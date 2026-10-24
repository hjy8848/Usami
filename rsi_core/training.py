"""Root trajectory credit/export; does not mislabel export as a model update."""
from dataclasses import asdict, dataclass
import math

from .archive import verify_chain
from .protocol import InfrastructureError, digest


@dataclass(frozen=True)
class RootTrainingRecord:
    trace_ref: str
    model_ref: str
    evaluator_ref: str
    business_ref: str
    group_id: str
    reward: float
    reward_source_ref: str
    turns: tuple
    root_type: str


def _service_reward(host, result, receipt, context):
    comparison = host.archive.load(receipt["comparison_ref"])
    task_set = context["task_sets"]["service_reward"]
    if (comparison.get("kind") != "service_paired_evaluation_v0.2"
            or comparison["purpose"] != "service_reward" or not comparison["usable"]
            or comparison["parent_ref"] != result.target_ref
            or comparison["candidate_ref"] != result.submitted_ref
            or comparison["task_set"] != task_set
            or comparison["task_set_ref"] != digest(task_set)
            or comparison["models"] != context["models"]
            or comparison["limits"] != context["limits"]):
        raise ValueError("Service reward cannot consume an unrelated direct-task comparison")
    pairs = comparison["pairs"]
    if len(pairs) != len(task_set["task_refs"]):
        raise ValueError("Service reward differs from its registered direct task set")
    deltas, unknowns, unsafe = [], 0, False
    for index, row in enumerate(pairs):
        if row["task_ref"] != task_set["task_refs"][index] or row["seed"] != task_set["seed"] + index:
            raise ValueError("Service reward order/seed differs from the registered task set")
        old, new = row["parent_result"], row["candidate_result"]
        if old["replay_verified"] is not True or new["replay_verified"] is not True:
            raise ValueError("Service reward includes an unverified Replay")
        if old["status"] == "UNKNOWN":
            unknowns += 1
        if new["status"] == "UNKNOWN":
            unknowns += 1
        deltas.append(float(new["status"] == "VERIFIED" and new["score"] == 1.0)
                      - float(old["status"] == "VERIFIED" and old["score"] == 1.0))
        unsafe = unsafe or new["forbidden_behavior"]
    expected = sum(deltas) / len(deltas)
    unknown_fraction = unknowns / (2 * len(pairs))
    safe = not unsafe
    if (comparison["mean_delta"] != expected
            or comparison["unknown_fraction"] != unknown_fraction
            or comparison["usable"] != (unknown_fraction <= comparison["unknown_limit"])
            or comparison["safe"] != safe):
        raise ValueError("Service reward summary differs from its task outcomes")
    expected_reward = expected if safe else -1.0
    if receipt["reward"] != expected_reward:
        raise ValueError("r_service differs from its service_reward outcomes")


def _self_reward(host, result, receipt, context):
    comparison = host.archive.load(receipt["comparison_ref"])
    if (comparison["purpose"] != "C_reward" or not comparison["usable"]
            or comparison["parent_ref"] != result.target_ref
            or comparison["candidate_ref"] != result.submitted_ref):
        raise ValueError("reward cannot consume selection or unrelated comparisons")
    pairs = comparison["pairs"]
    packages = context["packages"]["C_reward"]
    if len(pairs) != len(packages):
        raise ValueError("reward comparison differs from registered reward packages")
    for (old, new), package in zip(pairs, packages):
        binding = digest({"package": package, "models": context["models"],
                          "limits": context["limits"], "p0": package["p0_ref"]})
        for evaluated in (old, new):
            archived = host.archive.load(evaluated["archive_ref"])
            if (archived != {k: v for k, v in evaluated.items() if k != "archive_ref"}
                    or evaluated["pair_binding"] != binding or not evaluated["usable"]):
                raise ValueError("reward adaptation is unavailable or paired to a different context")
    expected = sum(new["score"] - old["score"] for old, new in pairs) / len(pairs)
    safe = not any(new["forbidden_behavior"] for _, new in pairs)
    if comparison["mean_delta"] != expected or comparison["safe"] != safe:
        raise ValueError("reward summary differs from executed paired results")
    if receipt["reward"] != (expected if safe else -1.0):
        raise ValueError("r_self differs from its executed comparison")


def root_training_record(host, result, reward, reward_source_ref, group_id):
    if result.scope != "root" or result.mode not in {"IMPROVE_SERVICE", "SELF_EDIT", "ADAPT_TASK"}:
        raise ValueError("only root researcher trajectories receive policy loss")
    if not math.isfinite(reward) or not -1 <= reward <= 1:
        raise ValueError("reward must be a finite paired difference or -1 failure")
    if result.status == "FAILED" and reward != -1:
        raise ValueError("root candidate failure requires fixed -1 reward")
    if result.status == "NOOP" and reward != 0:
        raise ValueError("NOOP requires zero gain")
    if not reward_source_ref or not group_id:
        raise ValueError("reward provenance and sampling group are required")

    saved = host.archive.load(result.archive_ref)
    verify_chain(saved["events"])
    for key in ("editor_ref", "target_ref", "mode", "scope", "status", "submitted_ref"):
        if saved[key] != getattr(result, key):
            raise ValueError("root result differs from its archived execution")
    root_type = "r_service" if result.mode == "IMPROVE_SERVICE" else "r_self"
    receipt = host.archive.load(reward_source_ref)
    expected_receipt = "root_reward_service_v0.2" if root_type == "r_service" else "root_reward_v1"
    if (receipt.get("kind") != expected_receipt or receipt.get("root_type", root_type) != root_type
            or receipt.get("context_ref") != group_id
            or receipt.get("root_trace_ref") != result.archive_ref or receipt.get("reward") != reward
            or receipt.get("models") != saved["models"] or saved["models"] != asdict(host.models)):
        raise ValueError("reward receipt does not bind this root, context and frozen models")
    context = host.archive.load(group_id)
    if (context.get("root_type", "r_self") != root_type
            or context["editor_ref"] != result.editor_ref or context["target_ref"] != result.target_ref
            or context["models"] != saved["models"] or saved["seed"] not in context["seeds"]):
        raise ValueError("root differs from the registered sampling context")

    if result.status in {"FAILED", "NOOP"}:
        outcome = "ROOT_FAILED" if result.status == "FAILED" else "NOOP"
        if receipt["outcome"] != outcome or receipt["comparison_ref"]:
            raise ValueError("failure/NOOP receipt has an inconsistent outcome")
    elif root_type == "r_service":
        _service_reward(host, result, receipt, context)
    else:
        _self_reward(host, result, receipt, context)

    turns = []
    for row in saved["events"]:
        event = row["event"]
        if event["kind"] != "model":
            continue
        if event["scope"] != "root" or event["model_ref"] != host.models.behavior.ref:
            raise ValueError("inner evaluation or different behavior model in root loss")
        completion = event["completion"]
        prompt = tuple(completion["prompt_token_ids"])
        generated = tuple(completion["token_ids"])
        probabilities = tuple(completion["behavior_logprobs"])
        if not prompt or not generated or len(generated) != len(probabilities):
            raise InfrastructureError("cannot train without actual prompt/generated tokens and behavior logprobs")
        turns.append({"input_ids": prompt + generated,
                      "loss_mask": (0,) * len(prompt) + (1,) * len(generated),
                      "behavior_logprobs": (0.0,) * len(prompt) + probabilities,
                      "request_hash": digest(event["request"]),
                      "generated_output": completion["output"]})
    if not turns:
        raise ValueError("root trajectory contains no trainable model action")
    return RootTrainingRecord(result.archive_ref, host.models.behavior.ref,
                              host.models.evaluator.ref, host.models.business.ref,
                              group_id, reward, reward_source_ref, tuple(turns), root_type)


def group_advantages(records):
    if not records:
        raise ValueError("empty RL group")
    identity = {(r.group_id, r.model_ref, r.evaluator_ref, r.business_ref, r.root_type)
                for r in records}
    if len(identity) != 1:
        raise ValueError("GRPO group mixed root types, sampling contexts or frozen model snapshots")
    rewards = [r.reward for r in records]
    mean = sum(rewards) / len(rewards)
    variance = sum((reward - mean) ** 2 for reward in rewards) / len(rewards)
    if variance == 0:
        return tuple(0.0 for _ in records)
    return tuple((reward - mean) / math.sqrt(variance) for reward in rewards)
