"""One-off, no-training live RSI period using the native Usami open-world path."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import copy
import json
import sys
import traceback

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from rsi_core.budget import Ledger
from rsi_core.packages import PackageProvider, PackageRegistration, TaskProof
from rsi_core.programs import (DesignerSnapshot, ExperienceArtifact, ProgramArtifact,
                               ServiceSnapshot)
from rsi_core.protocol import Completion, FrozenModels, Limits, ModelSnapshot, digest
from integrations.rsi_usami.open_world import WorldPopulation, run_open_period
from usami.service.client import OpenAICompatibleClient
from usami_v2.scenarios.designer import OpenAIDesignerProvider
from usami_v2.scenarios.distribution import BusinessSource, BusinessStratum, DistributionSpec

OUTPUT = Path(__file__).resolve().parent


class JournalClient:
    """Native HTTP client with a local, credential-free transcript."""
    def __init__(self, inner, path):
        self.inner, self.settings, self.path = inner, inner.settings, Path(path)
        self.index = 0

    def _redact(self, value):
        return self.inner._redact(value)

    def close(self):
        self.inner.close()

    def _append(self, value):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()

    @staticmethod
    def _safe_response(raw):
        safe = copy.deepcopy(raw)
        for choice in safe.get("choices", []) if isinstance(safe, dict) else []:
            if isinstance(choice, dict) and isinstance(choice.get("message"), dict):
                choice["message"].pop("reasoning_content", None)
        return safe

    def complete(self, request):
        self.index += 1
        base = {"call_index": self.index, "request_hash": digest(request),
                "model": request.get("model", self.settings.model),
                "message_count": len(request.get("messages", [])),
                "message_chars": sum(len(str(row.get("content", ""))) for row in request.get("messages", [])),
                "tool_names": [row.get("function", {}).get("name", "")
                               for row in request.get("tools", []) if isinstance(row, dict)]}
        try:
            raw = self.inner.complete(request)
        except Exception as exc:
            base.update({"status": "error", "error_type": type(exc).__name__,
                         "error_code": getattr(exc, "code", ""), "error": str(exc),
                         "provider_response": getattr(exc, "response", None)})
            self._append(base)
            raise
        safe = self._safe_response(raw)
        choices = safe.get("choices", []) if isinstance(safe, dict) else []
        base.update({"status": "ok", "provider_response": safe})
        self._append(base)
        return safe


class LiveResearchModel:
    """Adapts Host JSON-schema requests and Service calls to the same live model."""
    def __init__(self, client):
        self.client = client

    def complete(self, snapshot, request, *, max_tokens, seed):
        if snapshot.model_id != self.client.settings.model:
            raise ValueError("frozen model snapshot differs from the configured live provider")
        if "response_schema" not in request:
            payload = dict(request)
            payload["max_tokens"] = max_tokens
            raw = self.client.complete(payload)
            output = raw
        else:
            schema = request["response_schema"]
            messages = [
                {"role": "system", "content": "Return one structured result using the registered function tool. Do not add prose."},
                {"role": "user", "content": json.dumps(request["request"], ensure_ascii=False, sort_keys=True)},
            ]
            tool = {"type": "function", "function": {"name": "submit_research_result",
                    "description": "Submit the structured result requested by the Host.",
                    "parameters": schema}}
            payload = self.client.settings.request(messages, [tool])
            payload["max_tokens"] = max_tokens
            payload["parallel_tool_calls"] = False
            if "qwen3" in self.client.settings.model.casefold():
                payload["tool_choice"] = "auto"
            else:
                payload["tool_choice"] = {"type": "function", "function": {"name": "submit_research_result"}}
            raw = self.client.complete(payload)
            choices = raw.get("choices", [])
            message = choices[0].get("message", {}) if len(choices) == 1 else {}
            calls = message.get("tool_calls", [])
            if len(calls) == 1:
                function = calls[0].get("function", {})
                if function.get("name") == "submit_research_result":
                    try:
                        output = json.loads(function.get("arguments", ""))
                    except (TypeError, ValueError):
                        output = function.get("arguments", "")
                else:
                    output = {"unexpected_function": function.get("name", ""),
                              "arguments": function.get("arguments", "")}
            elif not calls and isinstance(message.get("content"), str):
                try:
                    output = json.loads(message["content"])
                except ValueError:
                    output = message["content"]
            else:
                output = {"invalid_tool_call_count": len(calls)}
        choices = raw.get("choices", []) if isinstance(raw, dict) else []
        usage = raw.get("usage", {}) if isinstance(raw, dict) else {}
        return Completion(output, int(usage.get("prompt_tokens") or 0),
                          int(usage.get("completion_tokens") or 0))


def diagnostic_distribution():
    source = BusinessSource(source_id="synthetic-live-diagnostic", kind="synthetic_assumption",
        reference="One-off live RSI diagnostic; synthetic design strata, not an empirical population",
        version="2026-10-25", supported_claims=("live interface diagnostic only",))
    return DistributionSpec(distribution_id="usami-live-minimal-diagnostic", version=1,
        population_scope="synthetic multi-stratum commerce worlds",
        sources=(source,), strata=(
            BusinessStratum(stratum_id="multi-line-mixed-issues", weight=1,
                weight_basis_source_id=source.source_id,
                contexts=("One customer owns an order with multiple product families and distinct issues.",)),
            BusinessStratum(stratum_id="multiple-orders-one-customer", weight=1,
                weight_basis_source_id=source.source_id,
                contexts=("One customer owns multiple orders with distinct item conditions.",)),
            BusinessStratum(stratum_id="inventory-and-delivery-choice", weight=1,
                weight_basis_source_id=source.source_id,
                contexts=("A remedy decision has meaningful stock or delivery differences across warehouses.",)),
        ), split="train")


def build_context(output):
    import experiments.rsi.fixtures.open_world_validation as fixture
    from experiments.rsi.fixtures.open_world_validation import context as fixture_context
    from usami_v2.runtime.runner import EpisodeBudget

    # The fixture factory only supplies trusted registries, certificates and native helpers.
    # Give every registered task a bounded live-Service call allowance before certification.
    original_budget = fixture.EpisodeBudget
    def live_budget(**kwargs):
        kwargs["max_model_calls"] = 12
        return original_budget(**kwargs)
    fixture.EpisodeBudget = live_budget
    ctx = fixture_context(output)
    fixture.EpisodeBudget = original_budget

    raw_client = OpenAICompatibleClient.from_env()
    client = JournalClient(raw_client, output / "model-calls.jsonl")
    settings = client.settings
    model_snapshot = ModelSnapshot(settings.model,
        digest({"base_url": settings.base_url, "model": settings.model, "options": settings.options,
                "timeout_seconds": settings.timeout_seconds, "trust_env": settings.trust_env}))
    models = FrozenModels(model_snapshot, model_snapshot, model_snapshot)
    live_model = LiveResearchModel(client)

    host = ctx["host"]
    host.models = models
    host.model = live_model
    host.max_output_tokens = 4096
    limits = Limits(model_calls=512, model_tokens=2_000_000, episodes=256,
        tool_steps=20000, research_steps=20000, cpu_seconds=20000, wall_seconds=7200,
        memory_bytes=134217728, source_bytes=65536, response_bytes=1048576)
    host.ledger = Ledger(limits)

    adapter = ctx["service_evaluator"].adapter
    adapter.model = live_model

    # Keep the initial P generic: each Service decision is made by the frozen live B model.
    model_delegate = '''def step(view, state):\n    if "model_observation" in view:\n        return {"kind": "ACTION", "state": state, "action": view["model_observation"]}\n    return {"kind": "MODEL", "state": state, "request": view["baseline_request"]}\n'''
    service = ServiceSnapshot(model_snapshot.ref, ProgramArtifact("P", model_delegate), ExperienceArtifact())
    old_designer = ctx["designer"]
    ctx["designer"] = DesignerSnapshot(model_snapshot, old_designer.research_program)
    ctx["service"] = service

    ctx["population"] = WorldPopulation(output / "worlds", diagnostic_distribution(),
        OpenAIDesignerProvider(client), seed=84, max_attempts=1)
    ctx["episode_budget"] = EpisodeBudget(max_customer_turns=8, max_service_decisions=80,
        max_service_tool_calls=72, max_model_calls=12)

    # Re-register the existing, independently certified training packages against the live P0/B snapshot.
    old_sample = host.archive.load(ctx["self_edit_context"]["sampling_ref"])
    old_bank = host.archive.load(old_sample["manifest_ref"])
    registrations = []
    for row in old_bank["registrations"]:
        data = dict(row["package"])
        package = __import__("rsi_core.protocol", fromlist=["AdaptationPackage"]).AdaptationPackage(
            **{**data, "p0_ref": service.ref, "support": tuple(data["support"]),
              "probe_refs": tuple(data["probe_refs"]), "query_refs": tuple(data["query_refs"])})
        proofs = tuple(TaskProof(**proof) for proof in row["task_proofs"])
        registrations.append(PackageRegistration(package, tuple(row["support_origins"]), proofs))
    provider = PackageProvider(registrations, host.archive, ctx["verifier"])
    groups = provider.sample_training_context(27, counts={"C_probe": 1, "C_select": 1, "C_reward": 1})
    ctx["self_edit_context"] = {**ctx["self_edit_context"],
        "probe_packages": groups.probe, "select_packages": groups.selection,
        "reward_packages": groups.reward, "sampling_ref": groups.archive_ref}

    phase_budgets = {phase: {"model_calls": 32, "model_tokens": 100000, "episodes": 128,
                             "tool_steps": 3000, "research_steps": 3000, "cpu_seconds": 600}
                     for phase in ("root", "selection", "reward")}
    ctx["service_rounds"] = tuple({**row, "phase_budgets": phase_budgets} for row in ctx["service_rounds"])
    ctx["self_edit_context"] = {**ctx["self_edit_context"], "phase_budgets": phase_budgets}
    ctx["_live_client"] = client
    return ctx


def main():
    output = OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    summary = {"kind": "one-off-live-rsi-diagnostic-v1", "model": "dashscope/qwen3.7-plus",
               "training": "NOT_RUN", "automatic_provider_retries": 0,
               "output": str(output)}
    ctx = None
    try:
        ctx = build_context(output)
        summary["world_distribution"] = ctx["population"].distribution.model_dump(mode="json")
        run = run_open_period(world_count=3, **{k: v for k, v in ctx.items() if not k.startswith("_")})
        summary.update({"status": run["rsi_period"]["status"], "record": run,
                        "world_period_ref": run["world_period_ref"],
                        "challenge_attempt_refs": run["challenge_attempt_refs"],
                        "period_cost": run["rsi_period"].get("cost", {})})
    except BaseException as exc:
        summary.update({"status": "FAILED", "error_type": type(exc).__name__,
                        "error": str(exc), "traceback": traceback.format_exc()})
        if ctx is not None:
            population = ctx["population"]
            summary["world_period_refs"] = list(population.period_refs)
            summary["world_population_state"] = str(population.state_path)
            summary["ledger"] = ctx["host"].ledger.snapshot()
    finally:
        if ctx is not None:
            client = ctx.get("_live_client")
            if client is not None:
                client.close()
        transcript = output / "model-calls.jsonl"
        summary["model_call_count"] = sum(1 for _ in transcript.open(encoding="utf-8")) if transcript.exists() else 0
        (output / "diagnostic-summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: summary.get(key) for key in
            ("status", "training", "model_call_count", "world_period_ref", "challenge_attempt_refs", "error_type", "error")},
            ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
