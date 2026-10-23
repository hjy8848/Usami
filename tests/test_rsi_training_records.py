"""Token/mask contract fixtures; no parameter training is claimed here."""
from dataclasses import replace
from pathlib import Path

import pytest

from rsi_core.protocol import Completion, InfrastructureError
from rsi_core.programs import ProgramArtifact
from rsi_core.training import group_advantages, root_training_record
from test_rsi_core import host, task


class TokenContractModel:
    def complete(self, snapshot, request, *, max_tokens, seed):
        # Explicit fixture token IDs, never a real model's training receipt.
        return Completion({"sources": []}, 2, 3, (3, 4, 5), (-1.0, -2.0, -1.5), (1, 2))


def test_seed_model_turn_is_archived_and_only_its_generated_tokens_get_loss(host):
    host.model = TokenContractModel()
    seed = ProgramArtifact("M", (Path(__file__).parents[1] / "experiments/rsi/seeds/M0.py").read_text())
    run = host.run(seed, task(), "ADAPT_TASK", {"support": [{"text": "PRIVATE_REWARD_NOT_INCLUDED"}]},
                    (), None)
    assert run.status == "NOOP"
    reward_ref = host.archive.save({"kind": "noop_reward", "value": 0})
    row = root_training_record(host, run, 0, reward_ref, "fixed-context-group")
    assert len(row.turns) == 1
    assert row.turns[0]["input_ids"] == (1, 2, 3, 4, 5)
    assert row.turns[0]["loss_mask"] == (0, 0, 1, 1, 1)
    assert row.turns[0]["behavior_logprobs"] == (0, 0, -1, -2, -1.5)
    assert group_advantages((row, row, row, row)) == (0, 0, 0, 0)
    positive, negative = replace(row, reward=1), replace(row, reward=-1)
    assert group_advantages((positive, negative)) == (1, -1)
    with pytest.raises(ValueError, match="context"):
        group_advantages((positive, replace(negative, model_ref="changed-weights")))


def test_no_logprob_api_is_not_silently_exported_as_rl(host):
    class NoTokens:
        def complete(self, snapshot, request, *, max_tokens, seed):
            return Completion({"sources": []}, 2, 3)

    host.model = NoTokens()
    seed = ProgramArtifact("M", (Path(__file__).parents[1] / "experiments/rsi/seeds/M0.py").read_text())
    run = host.run(seed, task(), "ADAPT_TASK", {}, (), None)
    with pytest.raises(InfrastructureError, match="actual prompt"):
        root_training_record(host, run, 0, "source", "group")


def test_evaluator_model_calls_are_excluded_from_root_training(host):
    host.model = TokenContractModel()
    seed = ProgramArtifact("M", (Path(__file__).parents[1] / "experiments/rsi/seeds/M0.py").read_text())
    child = host.run(seed, task(), "ADAPT_TASK", {}, (), None, scope="evaluator")
    with pytest.raises(ValueError, match="only root"):
        root_training_record(host, child, 0, "source", "group")
