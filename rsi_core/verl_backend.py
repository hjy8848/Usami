"""Optional verl integration for on-policy RSI root updates.

This module is deliberately not imported by ``rsi_core`` itself.  Install the
optional ``verl`` extra and import this module only in a verl training process.
It adapts complete, archived root groups to verl's AgentLoop/GRPO contracts; it
does not run training as an import or export side effect.
"""

import asyncio
from concurrent.futures import TimeoutError as FutureTimeout
import json
import math
from pathlib import Path
import uuid

from .archive import Archive
from .collection import training_records
from .protocol import InfrastructureError, canonical, digest


VERL_VERSION = "0.9.1"
VERL_AGENT_LOOP_NAME = "rsi_archived_root"


def _turn_parts(turn):
    tokens = tuple(turn["input_ids"])
    mask = tuple(turn["loss_mask"])
    logprobs = tuple(turn["behavior_logprobs"])
    if not tokens or len(tokens) != len(mask) or len(tokens) != len(logprobs):
        raise InfrastructureError("verl export found inconsistent token/mask/logprob lengths")
    if any(type(token) is not int or token < 0 for token in tokens):
        raise InfrastructureError("verl export found an invalid token id")
    if any(value not in (0, 1) for value in mask) or 1 not in mask:
        raise InfrastructureError("verl export needs an actual generated-token span")
    start = mask.index(1)
    if start == 0 or any(value != 1 for value in mask[start:]):
        raise InfrastructureError("verl export requires prompt tokens followed by one generated span")
    if any(value != 0.0 for value in logprobs[:start]):
        raise InfrastructureError("prompt positions must not carry behavior log probabilities")
    generated_logprobs = logprobs[start:]
    if any(not math.isfinite(value) or value > 0 for value in generated_logprobs):
        raise InfrastructureError("verl export found invalid behavior log probabilities")
    return tokens[:start], tokens[start:], generated_logprobs


def root_to_verl_rollout(record):
    """Encode a root as one continuous-token verl response without inventing context.

    A later MODEL prompt must extend the exact prior prompt + generated stream.
    New context is appended with response_mask=0; generated model tokens keep
    response_mask=1 and their recorded behavior log probabilities. Independent
    prompts are rejected because concatenating them would change the policy
    conditioning distribution.
    """
    if not record.turns:
        raise InfrastructureError("verl export needs at least one root model action")
    if not math.isfinite(record.reward) or not -1 <= record.reward <= 1:
        raise InfrastructureError("verl export found an invalid root reward")

    first_prompt, first_generated, first_logprobs = _turn_parts(record.turns[0])
    prompt_ids = list(first_prompt)
    response_ids = list(first_generated)
    response_mask = [1] * len(first_generated)
    response_logprobs = list(first_logprobs)
    stream = prompt_ids + response_ids

    for turn in record.turns[1:]:
        prompt, generated, logprobs = _turn_parts(turn)
        if len(prompt) < len(stream) or prompt[:len(stream)] != tuple(stream):
            raise InfrastructureError(
                "multi-turn root prompts are not continuous-token prefixes; "
                "verl export will not flatten independently conditioned turns"
            )
        appended_context = list(prompt[len(stream):])
        response_ids.extend(appended_context)
        response_mask.extend([0] * len(appended_context))
        response_logprobs.extend([0.0] * len(appended_context))
        response_ids.extend(generated)
        response_mask.extend([1] * len(generated))
        response_logprobs.extend(logprobs)
        stream = list(prompt) + list(generated)

    if len(response_ids) != len(response_mask) or len(response_ids) != len(response_logprobs):
        raise InfrastructureError("verl continuous-token response metadata lost alignment")
    if not any(response_mask):
        raise InfrastructureError("verl rollout contains no policy-generated token")

    return {
        "trace_ref": record.trace_ref,
        "reward_source_ref": record.reward_source_ref,
        "group_id": record.group_id,
        "model_ref": record.model_ref,
        "evaluator_ref": record.evaluator_ref,
        "business_ref": record.business_ref,
        "reward": float(record.reward),
        "prompt_ids": prompt_ids,
        "response_ids": response_ids,
        "response_mask": response_mask,
        "response_logprobs": response_logprobs,
        "turn_count": len(record.turns),
        "turn_request_hashes": [turn["request_hash"] for turn in record.turns],
    }


def _json_line(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def export_verl_group(host, group, output_dir):
    """Export one already-validated complete sampling group for one GRPO update.

    The output contains a JSONL replay dataset, a custom AgentLoop config, and
    a JSON-formatted YAML overlay for verl v0.9.1. One bundle contains exactly
    one full group, so verl cannot shuffle roots across advantage batches.
    """
    records = training_records(host, group)
    context = host.archive.load(group.context_ref)
    expected_model = context["models"]["behavior"]
    expected_model_ref = digest(expected_model)
    root_count = len(context["seeds"])
    if len(records) != root_count or len(group.roots) != root_count:
        raise ValueError("verl export requires every registered root from the complete group")
    if len({row.trace_ref for row in records}) != root_count:
        raise ValueError("verl export found duplicate root traces")
    if any(row.model_ref != expected_model_ref or row.group_id != group.context_ref for row in records):
        raise ValueError("verl export roots do not share the registered behavior snapshot and group")

    rollouts = [root_to_verl_rollout(row) for row in records]
    if any(row["group_id"] != group.context_ref for row in rollouts):
        raise ValueError("verl rollout group identity changed during conversion")
    max_prompt = max(len(row["prompt_ids"]) for row in rollouts)
    max_response = max(len(row["response_ids"]) for row in rollouts)
    group_ref = group.archive_ref
    manifest = {
        "kind": "verl_rsi_root_group_v1",
        "verl_version": VERL_VERSION,
        "group_ref": group_ref,
        "context_ref": group.context_ref,
        "group_id": group.context_ref,
        "behavior_model": expected_model,
        "behavior_model_ref": expected_model_ref,
        "evaluator_model_ref": digest(context["models"]["evaluator"]),
        "business_model_ref": digest(context["models"]["business"]),
        "root_refs": [row.trace_ref for row in records],
        "reward_refs": [row.reward_source_ref for row in records],
        "group_size": root_count,
        "max_prompt_tokens": max_prompt,
        "max_response_tokens": max_response,
        "loss_aggregation": "seq-mean-token-mean",
        "advantage_estimator": "grpo",
        "rollouts": rollouts,
        "training_updates_before_export": 0,
    }

    destination = Path(output_dir).resolve()
    if destination.exists():
        raise FileExistsError("verl export destination must be new: " + str(destination))
    destination.mkdir(parents=True)
    manifest_ref = host.archive.save(manifest)
    archive_root = str(host.archive.root.resolve())

    rows = []
    for index, rollout in enumerate(rollouts):
        rows.append({
            "data_source": "usami_rsi_archived_root",
            "prompt": [{"role": "user", "content": "Archived RSI root rollout. Tokens are loaded by the replay AgentLoop."}],
            "uid": group.context_ref,
            "trace_ref": rollout["trace_ref"],
            "group_ref": group_ref,
            "manifest_ref": manifest_ref,
            "extra_info": {"index": index},
        })

    loop_config = [{
        "name": VERL_AGENT_LOOP_NAME,
        "_target_": "rsi_core.verl_backend.ArchiveReplayAgentLoop",
        "archive_root": archive_root,
        "manifest_ref": manifest_ref,
    }]

    # JSON is valid YAML; using it avoids adding a YAML dependency to rsi_core.
    overlay = {
        "actor_rollout_ref": {
            "model": {"path": expected_model["model_id"]},
            "rollout": {
                "name": "vllm",
                "n": 1,
                "prompt_length": max_prompt,
                "response_length": max_response,
                "calculate_log_probs": True,
                "agent": {
                    "default_agent_loop": VERL_AGENT_LOOP_NAME,
                    "agent_loop_config_path": str(destination / "agent_loop.yaml"),
                },
            },
            "actor": {
                "ppo_epochs": 1,
                "ppo_mini_batch_size": root_count,
                "loss_agg_mode": "seq-mean-token-mean",
                "use_kl_loss": False,
            },
        },
        "algorithm": {
            "adv_estimator": "grpo",
            "norm_adv_by_std_in_grpo": True,
            "use_kl_in_reward": False,
        },
        "data": {
            "train_files": [str(destination / "train.jsonl")],
            # verl requires a validation dataset object; validation is explicitly disabled below.
            "val_files": [str(destination / "train.jsonl")],
            "prompt_key": "prompt",
            "train_batch_size": root_count,
            "gen_batch_size": root_count,
            "max_prompt_length": max_prompt,
            "max_response_length": max_response,
            "train_max_samples": root_count,
            "val_max_samples": root_count,
            "dataloader_num_workers": 0,
        },
        "trainer": {
            "use_v1": True,
            "total_epochs": 1,
            "total_training_steps": 1,
            "val_before_train": False,
            "test_freq": -1,
            "save_freq": 1,
            "resume_mode": "disable",
            "project_name": "usami-rsi",
            "experiment_name": "group-" + group_ref[:12],
            "default_local_dir": str(destination / "checkpoints"),
            "logger": ["console"],
        },
    }

    files = {
        "train.jsonl": "".join(_json_line(row) for row in rows),
        "agent_loop.yaml": json.dumps(loop_config, ensure_ascii=False, indent=2) + "\n",
        "verl_overlay.yaml": json.dumps(overlay, ensure_ascii=False, indent=2) + "\n",
        "manifest-ref.json": json.dumps({"manifest_ref": manifest_ref,
                                         "archive_root": archive_root,
                                         "group_ref": group_ref,
                                         "behavior_model_ref": expected_model_ref},
                                        ensure_ascii=False, indent=2) + "\n",
    }
    for name, contents in files.items():
        with (destination / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(contents)
    return {"manifest_ref": manifest_ref, "group_ref": group_ref,
            "output_dir": str(destination), "group_size": root_count,
            "max_prompt_tokens": max_prompt, "max_response_tokens": max_response,
            "verl_version": VERL_VERSION, "training_started": False}


def _verl_agent_loop_types():
    try:
        from verl.experimental.agent_loop.agent_loop import (
            AgentLoopBase, AgentLoopMetrics, AgentLoopOutput, register,
        )
    except ImportError as exc:
        return None, None, None, None, exc
    return AgentLoopBase, AgentLoopMetrics, AgentLoopOutput, register, None


_AgentLoopBase, _AgentLoopMetrics, _AgentLoopOutput, _register, _VERL_IMPORT_ERROR = _verl_agent_loop_types()
if _AgentLoopBase is None:
    _AgentLoopBase = object
    _AgentLoopMetrics = None
    _AgentLoopOutput = None
    _register = lambda _name: lambda cls: cls


@_register(VERL_AGENT_LOOP_NAME)
class ArchiveReplayAgentLoop(_AgentLoopBase):
    """Replay one root record into verl's GRPO batch; never calls the model."""

    def __init__(self, *args, archive_root, manifest_ref, **kwargs):
        if _VERL_IMPORT_ERROR is not None:
            raise ImportError("verl==0.9.1 is required to instantiate ArchiveReplayAgentLoop") from _VERL_IMPORT_ERROR
        super().__init__(*args, **kwargs)
        if not Path(archive_root).is_dir():
            raise FileNotFoundError("registered RSI archive is unavailable")
        self.archive = Archive(archive_root)
        self.manifest_ref = manifest_ref
        self.manifest = self.archive.load(manifest_ref)
        if (self.manifest.get("kind") != "verl_rsi_root_group_v1"
                or self.manifest.get("verl_version") != VERL_VERSION):
            raise ValueError("verl replay manifest has an unsupported schema/version")
        self.rollouts = {row["trace_ref"]: row for row in self.manifest["rollouts"]}
        if len(self.rollouts) != self.manifest["group_size"]:
            raise ValueError("verl replay manifest has duplicate or missing roots")

    async def run(self, sampling_params, **kwargs):
        del sampling_params  # This replay path deliberately performs no generation.
        if kwargs.get("manifest_ref") != self.manifest_ref:
            raise ValueError("dataset row references a different archived group")
        if kwargs.get("group_ref") != self.manifest["group_ref"]:
            raise ValueError("dataset row is not bound to this complete root group")
        if kwargs.get("uid") != self.manifest["group_id"]:
            raise ValueError("verl GRPO uid must be the registered sampling group")
        trace_ref = kwargs.get("trace_ref")
        if trace_ref not in self.rollouts:
            raise ValueError("dataset row references a root outside the archived group")
        row = self.rollouts[trace_ref]
        if row["group_id"] != kwargs["uid"] or row["model_ref"] != self.manifest["behavior_model_ref"]:
            raise ValueError("archived root differs from its frozen group/model reference")
        return _AgentLoopOutput(
            prompt_ids=row["prompt_ids"],
            response_ids=row["response_ids"],
            response_mask=row["response_mask"],
            response_logprobs=row["response_logprobs"],
            reward_score=row["reward"],
            num_turns=row["turn_count"],
            metrics=_AgentLoopMetrics(),
            extra_fields={"rsi_trace_ref": row["trace_ref"],
                          "rsi_reward_source_ref": row["reward_source_ref"],
                          "rsi_group_ref": self.manifest["group_ref"],
                          "rsi_behavior_model_ref": row["model_ref"]},
        )


class VerlResearchModel:
    """Synchronous Host adapter for verl's asynchronous token generation client.

    Run Host collection inside ``asyncio.to_thread`` using
    ``collect_self_edit_group_with_verl``. Each frozen ResearchModel snapshot
    must be explicitly mapped to its own verl client/tokenizer pair.
    """

    _SAMPLING_KEYS = {"temperature", "top_p", "top_k", "repetition_penalty"}

    def __init__(self, endpoints, *, event_loop, timeout_seconds=120):
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("verl request timeout must be positive and finite")
        self.endpoints = dict(endpoints)
        self.event_loop = event_loop
        self.timeout_seconds = timeout_seconds
        if not self.endpoints:
            raise ValueError("at least one frozen verl model endpoint is required")

    def complete(self, snapshot, request, *, max_tokens, seed):
        endpoint = self.endpoints.get(snapshot.ref)
        if endpoint is None:
            raise InfrastructureError("verl has no endpoint for the requested frozen model snapshot")
        client, tokenizer, registered_snapshot = endpoint
        if registered_snapshot.ref != snapshot.ref:
            raise InfrastructureError("verl endpoint snapshot does not match the Host model snapshot")
        if set(snapshot.sampling) - self._SAMPLING_KEYS:
            raise ValueError("ResearchModel sampling contains options not mapped by the verl adapter")
        if type(max_tokens) is not int or max_tokens < 1 or type(seed) is not int:
            raise ValueError("verl sampling requires a positive token budget and integer seed")
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is self.event_loop:
            raise InfrastructureError("run synchronous Host collection in a worker thread, not on the verl event loop")

        prompt_text = canonical(request)
        prompt_ids = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt_text}],
            tokenize=True, add_generation_prompt=True,
        )
        if hasattr(prompt_ids, "tolist"):
            prompt_ids = prompt_ids.tolist()
        if prompt_ids and isinstance(prompt_ids[0], list):
            prompt_ids = prompt_ids[0]
        prompt_ids = [int(token) for token in prompt_ids]
        sampling = {
            "temperature": snapshot.sampling.get("temperature", 1.0),
            "top_p": snapshot.sampling.get("top_p", 1.0),
            "top_k": snapshot.sampling.get("top_k", -1),
            "repetition_penalty": snapshot.sampling.get("repetition_penalty", 1.0),
            "max_tokens": max_tokens,
            "seed": seed,
            "logprobs": True,
        }
        future = asyncio.run_coroutine_threadsafe(
            client.generate(uuid.uuid4().hex, prompt_ids=prompt_ids, sampling_params=sampling),
            self.event_loop,
        )
        try:
            completion = future.result(timeout=self.timeout_seconds)
        except FutureTimeout as exc:
            future.cancel()
            raise InfrastructureError("verl rollout request timed out; no retry performed") from exc
        except Exception as exc:
            raise InfrastructureError("verl rollout request failed: " + str(exc)) from exc

        token_ids = tuple(completion.token_ids)
        logprobs = completion.log_probs
        if not token_ids or logprobs is None or len(token_ids) != len(logprobs):
            raise InfrastructureError("verl rollout did not return aligned tokens and behavior logprobs")
        text = tokenizer.decode(token_ids, skip_special_tokens=True)
        try:
            output = json.loads(text)
        except json.JSONDecodeError:
            output = text

        from .protocol import Completion
        return Completion(output, len(prompt_ids), len(token_ids), token_ids,
                          tuple(float(value) for value in logprobs), tuple(prompt_ids))


async def collect_self_edit_group_with_verl(host, endpoints, *args, timeout_seconds=120, **kwargs):
    """Run the existing group collector using explicit verl inference endpoints.

    No endpoint is inferred from an alias and no failed group is retried. Host
    collection runs off the event loop because its container/protocol API is
    synchronous; the adapter schedules each inference request back onto verl's
    async event loop.
    """
    from .collection import collect_self_edit_group

    if host.model is not None:
        raise ValueError("verl collection requires an otherwise unbound ResearchHost")
    loop = asyncio.get_running_loop()
    host.model = VerlResearchModel(endpoints, event_loop=loop,
                                   timeout_seconds=timeout_seconds)
    try:
        return await asyncio.to_thread(collect_self_edit_group, host, *args, **kwargs)
    finally:
        host.model = None
