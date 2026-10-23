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
