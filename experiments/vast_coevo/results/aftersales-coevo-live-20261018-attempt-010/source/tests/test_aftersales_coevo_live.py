import json

import pytest

from experiments.vast_coevo.examples.aftersales_coevo_live import (
    BudgetedClient, CallLedger, _designer_context,
)
from experiments.vast_coevo.examples.aftersales_coevo_support import initial_skill_libraries
from usami.service.models import ModelSettings, ServiceError


class _Endpoint:
    def __init__(self):
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 2, "total_tokens": 13}}


def test_live_call_ledger_records_exact_wire_exchange_and_stops_at_budget(tmp_path):
    settings = ModelSettings(model="fixture", base_url="https://fixture.invalid/v1",
                             options={"temperature": 0})
    endpoint = _Endpoint()
    ledger = CallLedger(tmp_path, limit=1)
    client = BudgetedClient("service", endpoint, settings, ledger)
    request = settings.request([{"role": "user", "content": "hello"}], [])

    result = client.complete(request)
    assert result["usage"]["total_tokens"] == 13
    record = json.loads((tmp_path / "model-calls/0001-service.json").read_text())
    assert record["request"] == request
    assert record["response"] == result
    assert ledger.usage()["by_role"]["service"]["total_tokens"] == 13

    with pytest.raises(ServiceError, match="budget exhausted"):
        client.complete(request)
    assert len(endpoint.requests) == 1
    assert ledger.actual_calls == 1
    assert ledger.denied == 1


def test_live_designer_context_does_not_preselect_a_task_or_expected_result():
    designer, _, _ = initial_skill_libraries()
    prior = [{"episode_id": "task-1", "trace_hash": "a" * 64,
              "process_errors": [{"classification": "false_rejection"}]}]
    context = _designer_context(designer, prior, "task-2")

    assert context["skill_snapshot_hash"] == designer.snapshot_hash
    assert "skill_rendered" in context and context["skill_rendered"]
    assert context["verified_prior_trials"] == prior
    assert "selection" not in context
    assert "expected_outcome" not in context
    from usami_aftersales import adapter
    from typing import get_args
    expected = list(get_args(adapter.World.model_fields["lines"].annotation.__args__[1].model_fields["status"].annotation))
    assert context["native_field_enums"]["lines"]["status"] == expected
    assert "resolved" not in context["native_field_enums"]["lines"]["status"]


def test_live_initial_snapshots_are_distinct_from_the_offline_smoke_provenance():
    designer, service, customer = initial_skill_libraries()
    assert designer.provenance == "aftersales-initial-designer-v1"
    assert service.provenance == "aftersales-initial-service-v1"
    assert customer.role == "customer"


def test_live_execution_returns_saved_replayable_artifacts(tmp_path):
    from pathlib import Path
    from experiments.vast_coevo.examples.aftersales_coevo_live import (
        _execute_task, _initial_world,
    )
    from experiments.vast_coevo.examples.aftersales_coevo_smoke import (
        _single_task, _task_customer_client, ServiceScriptClient,
    )
    from usami_aftersales import adapter

    frozen = _initial_world(1)
    task = _single_task(frozen)
    _, service, _ = initial_skill_libraries()
    customer = _task_customer_client(1, adapter.World.model_validate(frozen.world), "refund")
    result = _execute_task(tmp_path, 1, frozen, task, service, customer,
                           ServiceScriptClient(task_number=1), turns=4)

    assert result["evaluation_error"] is None
    assert result["agent_replay"]["verified"] is True
    for key in ("trace_path", "execution_path", "task_path"):
        assert Path(result[key]).is_file()
    status = json.loads((tmp_path / "tasks/task-1/status.json").read_text())
    assert status["status"] == "COMPLETED"
