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


def root_training_record(host, result, reward, reward_source_ref, group_id):
    if result.scope != "root" or result.mode not in {"SELF_EDIT", "ADAPT_TASK"}:
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
    receipt = host.archive.load(reward_source_ref)
    if (receipt.get("kind") != "root_reward_v1" or receipt.get("context_ref") != group_id
            or receipt.get("root_trace_ref") != result.archive_ref or receipt.get("reward") != reward
            or receipt.get("models") != saved["models"] or saved["models"] != asdict(host.models)):
        raise ValueError("reward receipt does not bind this root, context and frozen models")
    context = host.archive.load(group_id)
    if (context["editor_ref"] != result.editor_ref or context["target_ref"] != result.target_ref
            or context["models"] != saved["models"] or saved["seed"] not in context["seeds"]):
        raise ValueError("root differs from the registered sampling context")
    if result.status in {"FAILED", "NOOP"}:
        outcome = "ROOT_FAILED" if result.status == "FAILED" else "NOOP"
        if receipt["outcome"] != outcome or receipt["comparison_ref"]:
            raise ValueError("failure/NOOP receipt has an inconsistent outcome")
    else:
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
        if reward != (expected if safe else -1.0):
            raise ValueError("root reward differs from its executed comparison")
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
                              group_id, reward, reward_source_ref, tuple(turns))


def group_advantages(records):
    if not records:
        raise ValueError("empty RL group")
    identity = {(r.group_id, r.model_ref, r.evaluator_ref, r.business_ref) for r in records}
    if len(identity) != 1:
        raise ValueError("RL group changed context or frozen model snapshots")
    rewards = [r.reward for r in records]
    mean = sum(rewards) / len(rewards)
    variance = sum((r - mean) ** 2 for r in rewards) / len(rewards)
    if variance == 0:
        return tuple(0.0 for _ in records)
    return tuple((r - mean) / math.sqrt(variance) for r in rewards)
