"""Research Studio records native evidence and isolates candidate Skills."""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from usami.service.models import ModelSettings, ServiceError
from usami_v2.runtime.agents import OpenAIServiceAgent, ServicePrompt
from usami_v2.scenarios.distribution import sample_schedule
from usami_v2.scenarios.designer import OpenAIDesignerProvider, ScenarioDraft
from vast_coevo.schema import digest
from vast_coevo.skills.library import LibrarySnapshot, empty_snapshot
from vast_coevo.skills.models import DecisionSkill, Scope, Trigger
from web.backend.human_customer import HumanSessionManager
from web.backend.research_studio import (
    ResearchRunManager, _distribution, install_research_studio_routes,
)


class TextReplyClient:
    def __init__(self):
        self.settings = ModelSettings(model="fixed-test-model", base_url="http://127.0.0.1/v1",
                                      options={"max_tokens": 64})
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return {"choices": [{"message": {"role": "assistant", "content": "I can help."},
                              "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 3}}


def test_research_distribution_reseals_difficulty_strata_and_samples():
    for name in ("mixed_after_sales", "multi_line", "inventory_and_deadline"):
        spec = _distribution(name, "train", "basic")
        checked = spec.checked()
        assert checked.record_hash == spec.record_hash
        assert all("small number of prerequisites" in row.contexts[-1] for row in spec.strata)
        assert len(sample_schedule(spec, seed=42, count=1)) == 1


def test_designer_failure_record_keeps_only_redacted_provider_diagnostics():
    class FailingClient(TextReplyClient):
        def complete(self, request):
            raise ServiceError("PROVIDER_HTTP_ERROR", "HTTP 400", {
                "status_code": 400, "body": "bad request sk-secret-value"})

        def _redact(self, value):
            return json.loads(json.dumps(value).replace("sk-secret-value", "[REDACTED]"))

    provider = OpenAIDesignerProvider(FailingClient())
    with pytest.raises(ServiceError):
        provider.submit("world", [{"role": "user", "content": "test"}], ScenarioDraft)
    assert provider.last_call is not None
    error = provider.last_call.response["error"]
    assert error["code"] == "PROVIDER_HTTP_ERROR"
    assert error["provider_response"]["status_code"] == 400
    assert "sk-secret-value" not in json.dumps(provider.last_call.model_dump())


def test_candidate_skill_enters_only_the_s1_real_model_request():
    skill = DecisionSkill(
        id="transaction-consent-check", version=1,
        scope=Scope(domains=("aftersales",)),
        trigger=Trigger(keywords=("refund",)),
        description="Check transaction preconditions from observed case state.",
        preconditions=("Use the current tool results for the case.",),
        procedure=("Check prerequisites before committing a quote.",),
        postconditions=("Confirm the operation result before reporting completion.",),
        recovery=("If a prerequisite is absent, explain what remains needed.",),
    )
    candidate = LibrarySnapshot(role="service", skills=(skill,), provenance="test candidate")
    prompt = ServicePrompt(customer_id="customer-1", customer_request="Please refund these headphones.")
    s0_client, s1_client = TextReplyClient(), TextReplyClient()

    assert OpenAIServiceAgent(s0_client).decide(prompt).kind == "reply"
    s1 = OpenAIServiceAgent(s1_client, skill_snapshot=candidate)
    assert s1.decide(prompt).kind == "reply"

    s0_request, s1_request = s0_client.requests[0], s1_client.requests[0]
    assert s0_request["model"] == s1_request["model"]
    assert s0_request["tools"] == s1_request["tools"]
    assert s0_request["messages"][:2] == s1_request["messages"][:2]
    assert len(s0_request["messages"]) == 2
    assert len(s1_request["messages"]) == 3
    rendered = s1_request["messages"][-1]["content"]
    assert skill.id in rendered and skill.content_hash in rendered
    assert s1.last_skill_injection["snapshot_hash"] == candidate.snapshot_hash
    assert s1.last_skill_injection["rendered_hash"] == digest(rendered)
    assert s1.last_skill_injection["request_hash"] == digest(s1_request)
    assert len(s1.last_skill_injection["hits"]) == 1


def test_research_archive_hash_chain_detects_row_and_journal_tampering(tmp_path):
    manager = ResearchRunManager(object(), output_dir=tmp_path / "research")
    row = {"run_id": "rs-integrity-test", "status": "READY", "phases": {}, "journal": []}
    manager._persist(row, "created")
    folder = tmp_path / "research" / row["run_id"]
    saved = json.loads((folder / "current.json").read_text(encoding="utf-8"))

    assert ResearchRunManager._verify_persisted_row(saved, folder / "journal.jsonl")
    changed = dict(saved)
    changed["status"] = "FAILED"
    assert not ResearchRunManager._verify_persisted_row(changed, folder / "journal.jsonl")

    journal = folder / "journal.jsonl"
    journal.write_text(journal.read_text(encoding="utf-8").replace("created", "changed"), encoding="utf-8")
    assert not ResearchRunManager._verify_persisted_row(saved, journal)


def test_research_routes_bootstrap_shared_local_owner_cookie(tmp_path):
    app = FastAPI()
    human = HumanSessionManager(output_dir=tmp_path / "human")
    install_research_studio_routes(app, human, output_dir=tmp_path / "research")
    with TestClient(app) as client:
        history = client.get("/api/research/runs")
        assert history.status_code == 200
        cookie = history.headers.get("set-cookie", "").lower()
        assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
        config = client.get("/api/research/config")
        assert config.status_code == 200
        assert "credential" not in json.dumps(config.json()).lower()
