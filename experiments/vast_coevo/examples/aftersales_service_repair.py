"""Replay a verified After-sales Service failure, reflect once, and retest.

The source episode is never rerun online. One Service Reflection call is allowed,
followed (only for a statically accepted non-NOOP patch) by one real Customer /
Service episode in a separately frozen order world. No performance claim is made.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/vast_coevo/results/aftersales-answer-deepseek-live-20261019-001"
DEFAULT_ROOT = ROOT / "experiments/vast_coevo/results/aftersales-service-repair-live-20261019-001"
SOURCE_JOURNAL = SOURCE / "journal.json"
SCHEMA_VERSION = "aftersales-service-repair-v1"
MODEL_CALL_LIMIT = 25  # 1 Reflection + 8 Customer + 16 Service


def _json(value):
    if hasattr(value, "model_dump"):
        return _json(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


def _write(root: Path, relative: str, value: Any, *, immutable=False):
    from vast_coevo.schema import atomic_json

    path = root / relative
    atomic_json(path, _json(value), immutable=immutable)
    return path


def _rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def _source_failures(root: Path, episode_id: str, episode, trace_ref, trace):
    """Project only actual Oracle rows; never infer a failure from model text."""
    from vast_coevo.models import VerifiedFailure
    from vast_coevo.schema import digest

    trace_events = {row.id: row for row in trace.events}
    customer_turns = {
        row.payload.get("turn_id"): row
        for row in trace.events
        if row.kind == "customer" and not row.payload.get("setup")
    }
    failures = []
    for row in episode.oracle["operations"]:
        if row["classification"] != "successful_business_violation":
            continue
        event = trace_events[row["dialogue_event_id"]]
        native = event.payload["trace"]
        native_event = next(item for item in native["events"] if item["kind"] == "operation")
        operation = native_event["payload"]["operation"]
        before = native["initial_state"]
        after = native["final_state"]
        order_id = operation.get("resource_id")
        params = operation.get("params", {})
        case_id = params.get("case_id")
        quote_id = params.get("quote_id")
        if quote_id:
            quote = before.get("quotes", {}).get(quote_id)
            case_id = quote.get("case_id") if quote else case_id
        case = before.get("cases", {}).get(case_id) if case_id else None
        if not quote_id and case:
            quote_id = case.get("agreement_quote")
        quote = before.get("quotes", {}).get(quote_id) if quote_id else None
        line_id = case.get("line_id") if case else (quote.get("line_id") if quote else None)
        line = before.get("lines", {}).get(line_id) if line_id else None
        after_case = after.get("cases", {}).get(case_id) if case_id else None
        after_line = after.get("lines", {}).get(line_id) if line_id else None
        turn = customer_turns.get(event.payload.get("turn_id"))
        grants = list(turn.payload.get("grants", [])) if turn else []
        intent = turn.payload.get("intent", {}) if turn else {}
        exact_confirm = intent.get("confirm_operation")
        interaction = before.get("interaction", {})
        consents = list(interaction.get("consents", []))
        exact_consent = any(
            consent.get("operation") == operation
            and (quote is None or consent.get("quote_hash") == quote.get("quote_hash"))
            and consent.get("revision") == interaction.get("revision")
            for consent in consents
        )
        codes = tuple(sorted(row.get("violations", [])))
        prestate = {
            "operation": operation,
            "order": before.get("orders", {}).get(order_id),
            "line": line,
            "case": case,
            "quote": quote,
            "interaction": {
                "revision": interaction.get("revision"),
                "commitments": interaction.get("commitments", {}),
                "consents": consents,
            },
        }
        permission = {
            "identity": trace.private.identity,
            "protected_objects": list(trace.private.protected_objects),
            "customer_declared_grants_for_turn": grants,
            "operation_exactly_granted": operation in grants,
            "structured_confirm_operation": exact_confirm,
            "oracle_authorized": row.get("authorized"),
            "turn_id": event.payload.get("turn_id"),
        }
        prerequisites = (
            {"kind": "exact_write_authorization", "present": operation in grants,
             "source": "native_customer_event_grants"},
            {"kind": "exact_current_consent", "present": exact_consent,
             "structured_confirm_operation_present": exact_confirm is not None,
             "quote_hash": quote.get("quote_hash") if quote else None,
             "interaction_revision": interaction.get("revision")},
        )
        expected = {"reference_allowed": False, "reference_codes": list(codes),
                    "expected_execution": "do not execute this write"}
        actual = {"engine_execution_succeeded": bool(row.get("success")),
                  "oracle_operation_correct": row.get("operation_correct"),
                  "before_hash": event.before_hash, "after_hash": event.after_hash,
                  "line_status_after": after_line.get("status") if after_line else None,
                  "case_status_after": after_case.get("status") if after_case else None}
        fingerprint = digest({"domain": "aftersales", "operation": row["operation"],
                              "reference_codes": list(codes)})
        failures.append(VerifiedFailure(
            episode_id=episode_id, event_id=event.id, domain="aftersales",
            operation=row["operation"], reference_codes=codes,
            relevant_prestate=prestate, permission_scope=permission,
            causal_prerequisites=prerequisites, expected=expected, actual=actual,
            successful_business_violation=True, authorization_only=False,
            trace=trace_ref, fingerprint=fingerprint,
            normalization_scope="pending_causal_normalization",
        ))
    return tuple(failures)


def _make_native_view(episode, trace, evidence):
    from vast_coevo.reflection.evidence import native_view

    customer_rows = []
    for event in trace.events:
        if event.kind != "customer" or event.payload.get("setup"):
            continue
        intent = event.payload["intent"]
        declarations = list(intent.get("requested_operations", []))
        if intent.get("confirm_operation") is not None:
            declarations.append(intent["confirm_operation"])
        customer_rows.append({
            "turn_id": event.payload["turn_id"],
            "message": intent["message"],
            "declared_write_intents": declarations,
            "accepted_write_grants": event.payload.get("grants", []),
            "authorization_source": "native_session_input",
            "source_refs": ("source/trace.json#/events/" + event.id + "/payload",),
        })
    customers_by_turn = {row["turn_id"]: row for row in customer_rows}
    business_events = []
    for event in trace.events:
        if event.kind != "business":
            continue
        native = event.payload["trace"]
        operation = next(item["payload"]["operation"] for item in native["events"] if item["kind"] == "operation")
        business_events.append((event, operation))

    tool_rows = []
    for index, row in enumerate(episode.tools):
        matches = []
        for event, operation in business_events:
            if event.before_hash != row.get("before_hash") or event.after_hash != row.get("after_hash"):
                continue
            if operation.get("name") != row.get("name"):
                continue
            raw_arguments = row.get("arguments")
            parsed = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            expected = {key: value for key, value in operation.items() if key != "name"}
            if parsed == expected:
                matches.append(event)
        event = matches[0] if len(matches) == 1 else None
        turn_id = event.payload.get("turn_id") if event else None
        call_id = row["call_id"]
        actual_raw = None
        actual_name = None
        for call in episode.calls:
            if call.role != "service" or not isinstance(call.record.response, dict):
                continue
            for choice in call.record.response.get("choices", []):
                message = choice.get("message", {}) if isinstance(choice, dict) else {}
                for tool in message.get("tool_calls", []) if isinstance(message, dict) else []:
                    function = tool.get("function", {}) if isinstance(tool, dict) else {}
                    if tool.get("id") == call_id:
                        actual_raw = function.get("arguments")
                        actual_name = function.get("name")
        if not isinstance(actual_raw, str) or actual_name != row["name"]:
            raise ValueError("native Service tool does not match its recorded model-selected call")
        # Protect against changed argument strings even if they parse identically.
        parsed_record = json.loads(row["arguments"]) if isinstance(row["arguments"], str) else row["arguments"]
        if json.loads(actual_raw) != parsed_record:
            raise ValueError("native Service arguments differ from the archived model output")
        refs = ["source/execution.json#/tools/" + str(index)]
        if event:
            refs.append("source/trace.json#/events/" + event.id)
        tool_rows.append({
            "call_id": call_id, "name": row["name"], "arguments": actual_raw,
            "response": row.get("result"), "turn_id": turn_id, "event_id": event.id if event else None,
            "source_refs": refs,
        })
    replies = []
    visible = []
    for event in trace.events:
        if event.kind == "service":
            replies.append({"event_id": event.id, "turn_id": "turn_" + str(len(replies) + 1),
                            "message": event.payload.get("message", ""),
                            "offer": event.payload.get("offer"),
                            "source_ref": "source/trace.json#/events/" + event.id})
        elif event.kind == "customer" and not event.payload.get("setup"):
            visible.append({"event_id": event.id, "turn_id": event.payload["turn_id"],
                            "message": event.payload["intent"]["message"],
                            "source_ref": "source/trace.json#/events/" + event.id})
    return native_view(evidence, customer_rows, tool_rows, replies, visible)


def prepare(root: Path) -> dict:
    """Verify archived failure and freeze a new certified order before Reflection."""
    from usami_aftersales import adapter as base_adapter
    from usami_benchmark.episodes import EpisodeExecution, replay as replay_episode
    from usami_benchmark.episodes import dialogue_adapter
    from usami_benchmark.registry import default_spec
    from usami_benchmark.tasks import ConstructionBudget, TaskSelection, compile_task, verify_task
    from usami_benchmark.worlds import freeze
    from usami_dialogue.agents import AgentExecution, replay as replay_agent
    from vast_coevo.evidence import EvidenceArchive
    from vast_coevo.models import (ArtifactRef, Budget as EvidenceBudget, Consumption,
                                   EpisodeConfig, EpisodeEvidence, ModelCall, ReplayResult,
                                   VerifiedEvent)
    from vast_coevo.schema import atomic_json, digest
    from vast_coevo.skills.library import empty_snapshot
    from experiments.vast_coevo.examples.aftersales_coevo_support import model_spec

    if root.exists():
        raise FileExistsError("experiment directory already exists; preserving prior runs")
    if not SOURCE_JOURNAL.is_file():
        raise FileNotFoundError("the archived real-model source journal is missing")
    root.mkdir(parents=True)

    source_raw = json.loads(SOURCE_JOURNAL.read_text(encoding="utf-8"))
    outer = EpisodeExecution.model_validate(source_raw)
    if outer.execution_hash != outer.computed_hash():
        raise ValueError("source episode hash mismatch")
    outer_replay = replay_episode(outer)
    episode = AgentExecution.model_validate(outer.dialogue_execution.model_dump(mode="json"))
    source_adapter = dialogue_adapter("aftersales", outer.config.task.frozen.spec.rules_version)
    source_world = source_adapter.World.model_validate(episode.trace.initial_world)
    agent_replay = replay_agent(source_adapter, episode, world=source_world, config=episode.config)
    if not outer_replay["verified"] or not agent_replay["verified"]:
        raise ValueError("source full Replay did not verify")
    source_trace = episode.trace.model_dump(mode="json")
    trace_path = _write(root, "source/trace.json", source_trace, immutable=True)
    execution_path = _write(root, "source/execution.json", episode, immutable=True)
    source_trace_ref = ArtifactRef(path=_rel(trace_path), sha256=digest(source_trace))

    service_parent = empty_snapshot("service")
    customer_snapshot = empty_snapshot("customer")
    decisions = {row.id: row for row in episode.trace.events}
    evidence_events = []
    for row in episode.oracle["operations"]:
        event = decisions[row["dialogue_event_id"]]
        evidence_events.append(VerifiedEvent(
            event_id=event.id,
            operation=row["operation"],
            classification=row["classification"],
            reference_codes=tuple(row.get("violations", [])),
            successful_execution=bool(row.get("success")),
            authorized=row.get("authorized"),
            operation_correct=row.get("operation_correct"),
            before_hash=event.before_hash,
            after_hash=event.after_hash,
        ))
    failures = _source_failures(root, "source-aftersales-20261019-001", episode,
                                source_trace_ref, episode.trace)
    calls = []
    for index, call in enumerate(episode.calls):
        model = episode.customer_model if call.role == "customer" else episode.service_model
        calls.append(ModelCall(
            id=f"source.call.{index:03d}", role=call.role, model=model_spec(model),
            base_request=call.record.request, request=call.record.request,
            response=call.record.response,
            error=call.record.error or None,
        ))
    evidence_config = EpisodeConfig(
        id="source-aftersales-20261019-001", config_id="aftersales-service-repair-source-v1",
        domain="aftersales", partition="development", initial_world_hash=source_world.state_hash,
        identity=episode.trace.private.identity, mode=episode.config.mode,
        customer_model=model_spec(episode.customer_model), service_model=model_spec(episode.service_model),
        budget=EvidenceBudget(**episode.config.budget.model_dump()), tools=tuple(episode.config.tools),
    )
    source_score = outer.score
    evidence = EpisodeEvidence(
        episode_id="source-aftersales-20261019-001", config=evidence_config, track="service_task",
        task_ref=outer.config.task.task_hash,
        customer_snapshot_hash=customer_snapshot.snapshot_hash,
        service_snapshot_hash=service_parent.snapshot_hash,
        model_calls=tuple(calls), events=tuple(evidence_events), failures=failures,
        consumption=Consumption(
            customer_llm_calls=episode.cost["customer_calls"],
            service_llm_calls=episode.cost["service_calls"],
            reflection_calls=0, tool_calls=episode.cost["tool_calls"],
        ), termination=episode.status, trace=source_trace_ref,
        native_trace_hash=episode.trace.trace_hash,
        replay=ReplayResult(verified=True, request_count=len(episode.calls),
                            native_trace_hash=episode.trace.trace_hash),
        task_success=bool(source_score.get("success")),
        legal_task_success=bool(source_score.get("success")),
        goal_satisfied=all(source_score.get("completion_subgoals", [])),
        frame_preserved=source_score.get("frame_preserved"),
    )
    view = _make_native_view(episode, episode.trace, evidence)
    evidence = EpisodeEvidence.model_validate({**evidence.model_dump(mode="json"), "model_calls": [c.model_dump(mode="json") for c in calls]})
    # Rebind after sealing; the view is constructed from the final evidence hash.
    view = _make_native_view(episode, episode.trace, evidence)
    evidence_archive = EvidenceArchive(root / "evidence")
    evidence_hash = evidence_archive.save(evidence)
    atomic_json(root / "evidence/source-interaction-view.json", view.model_dump(mode="json"), immutable=True)
    atomic_json(root / "libraries/service/parent.json", service_parent.model_dump(mode="json"), immutable=True)
    atomic_json(root / "libraries/customer/fixed.json", customer_snapshot.model_dump(mode="json"), immutable=True)

    # This scene is held out from Reflection input. It is frozen and compiled now,
    # before any candidate or retest outcome is observed.
    frozen = freeze(default_spec("aftersales", 4, partition="train"))
    new_world = base_adapter.World.model_validate(frozen.world)
    profile_id = "profile_u2_order1_line0"
    if profile_id not in new_world.profiles:
        raise ValueError("pre-registered seed-4 profile is absent")
    selection = TaskSelection(kind="dialogue", family="dispute_resolution", profile_id=profile_id)
    task_record = compile_task(
        frozen, selection,
        ConstructionBudget(max_nodes=4096, max_depth=16, max_paths=1),
    )
    verify_task(task_record)
    atomic_json(root / "retest/frozen_world.json", frozen.model_dump(mode="json"), immutable=True)
    atomic_json(root / "retest/certified_task.json", task_record.model_dump(mode="json"), immutable=True)
    source_violations = [row for row in episode.oracle["operations"]
                         if row["classification"] in {"successful_business_violation", "authorization_only"}]
    cause_rows = []
    for row in source_violations:
        event = decisions[row["dialogue_event_id"]]
        intent_event = next((item for item in episode.trace.events
                             if item.kind == "customer" and item.payload.get("turn_id") == event.payload.get("turn_id")), None)
        intent = intent_event.payload.get("intent", {}) if intent_event else {}
        cause_rows.append({
            "event_id": event.id, "operation": row["operation"],
            "classification": row["classification"], "reference_codes": row.get("violations", []),
            "oracle_authorized": row.get("authorized"), "operation_correct": row.get("operation_correct"),
            "turn_id": event.payload.get("turn_id"),
            "customer_confirm_operation_present": intent.get("confirm_operation") is not None,
            "customer_requested_operation_count": len(intent.get("requested_operations", [])),
        })
    manifest = {
        "protocol": SCHEMA_VERSION, "status": "PREPARED",
        "source": {
            "path": _rel(SOURCE_JOURNAL), "outer_execution_hash": outer.execution_hash,
            "task_hash": outer.config.task.task_hash, "world_hash": outer.config.task.frozen.world_hash,
            "oracle_status": episode.oracle["status"], "oracle_trace_valid": episode.oracle["trace_valid"],
            "outer_replay": outer_replay, "native_agent_replay": agent_replay,
            "task_success": bool(source_score.get("success")),
            "goal_satisfied": all(source_score.get("completion_subgoals", [])),
            "errors": cause_rows, "evidence_hash": evidence_hash,
            "service_parent_snapshot_hash": service_parent.snapshot_hash,
            "service_parent_semantics": "empty declarative snapshot; original episode had no injected Service Skill",
        },
        "retest": {
            "world_seed": 4, "partition": "train", "world_hash": frozen.world_hash,
            "profile_id": profile_id, "identity": new_world.profiles[profile_id].identity,
            "order_id": new_world.profiles[profile_id].facts["order_id"],
            "line_id": new_world.profiles[profile_id].facts["line_id"],
            "task_hash": task_record.task_hash,
            "selection": selection.model_dump(mode="json"),
            "construction_budget": task_record.construction_budget.model_dump(mode="json"),
            "service_mode": "sandbox", "max_customer_llm_calls": 8,
            "max_service_llm_calls": 16, "max_service_tool_calls": 48,
            "max_format_recoveries": 0,
        },
        "model": {"model": "deepseek-v4.1-flash", "base_url": "https://inferaiapi.com/v1",
                  "options": {}, "timeout_seconds": 120, "trust_env": True},
        "limits": {"max_reflection_calls": 1, "max_retest_calls": 24,
                   "total_max_model_calls": MODEL_CALL_LIMIT, "dynamic_gate": "disabled for this diagnostic smoke only"},
        "created_at": "2026-10-19",
    }
    atomic_json(root / "manifest.json", manifest, immutable=True)
    _write(root, "source/episode.json", outer, immutable=True)
    return manifest


def _proxy_status():
    """Return safe proxy metadata; never serialize credentials or full URLs."""
    names = ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy")
    proxy_value = next((os.environ.get(name) for name in names if os.environ.get(name)), None)
    if proxy_value:
        parsed = urlsplit(proxy_value)
        host, port, scheme = parsed.hostname, parsed.port, parsed.scheme
        source = "process_environment"
    else:
        # This endpoint is attempted only because the user explicitly identified
        # port 65533 as their active proxy; its host/protocol are not presumed live.
        host, port, scheme, source = "127.0.0.1", 65533, "http", "user_reported_local_port_probe"
    if not host or not port:
        return {"available": False, "source": source, "scheme": scheme or "unknown",
                "host": "unresolved", "port": "unresolved", "reason": "proxy endpoint lacks host/port"}
    try:
        with socket.create_connection((host, port), timeout=2):
            available = True
            reason = "TCP listener reachable"
    except OSError as exc:
        available = False
        reason = type(exc).__name__
    return {"available": available, "source": source, "scheme": scheme,
            "host": "loopback" if host in {"127.0.0.1", "localhost", "::1"} else "configured-host",
            "port": port, "reason": reason}


class CallLedger:
    def __init__(self, root, *, limit=MODEL_CALL_LIMIT):
        self.root, self.limit, self.calls = root, limit, 0

    def complete(self, role, inner, settings, request):
        if self.calls >= self.limit:
            raise RuntimeError("pre-registered model-call ceiling reached; request not sent")
        self.calls += 1
        folder = self.root / "model-calls"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{self.calls:04d}-{role}.json"
        row = {"call_index": self.calls, "role": role,
               "model": settings.model, "request": copy.deepcopy(request),
               "status": "prepared", "sent": False, "send_started": False}
        _write(self.root, str(path.relative_to(self.root)), row)
        try:
            complete = inner.complete
            row.update(status="in_flight", sent=True, send_started=True)
            _write(self.root, str(path.relative_to(self.root)), row)
            response = complete(copy.deepcopy(request))
        except Exception as exc:
            row.update(status="error", error={"type": type(exc).__name__,
                         "code": getattr(exc, "code", "PROVIDER_ERROR"), "message": str(exc)},
                        response=copy.deepcopy(getattr(exc, "response", None)))
            _write(self.root, str(path.relative_to(self.root)), row)
            raise
        row.update(status="completed", response=copy.deepcopy(response))
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        row["usage"] = usage if isinstance(usage, dict) else {}
        _write(self.root, str(path.relative_to(self.root)), row)
        return response


class RecordingClient:
    def __init__(self, role, inner, settings, ledger):
        self.role, self.inner, self.settings, self.ledger = role, inner, settings, ledger

    def complete(self, request):
        return self.ledger.complete(self.role, self.inner, self.settings, request)


def run_live(root: Path, substitute_patch_path: Path | None = None) -> dict:
    """Run one Reflection (or use a recorded offline substitute) and one retest."""
    from usami.service.client import OpenAICompatibleClient, key_from_env, settings_from_env
    from usami.service.models import ModelSettings
    from usami_aftersales import adapter as base_adapter
    from usami_aftersales import tasks as aftersales_tasks
    from usami_benchmark.episodes import dialogue_adapter
    from usami_benchmark.tasks import verify_task
    from usami_dialogue.agents import SkillPromptContext, TaskRunConfig, replay as replay_execution, run
    from usami_dialogue.tasks import score
    from usami_harness.models import Budget as RunBudget
    from vast_coevo.reflection.reflector import ReflectionInput, ServiceReflector
    from vast_coevo.reflection.scope import DomainPolicy
    from vast_coevo.schema import atomic_json, digest
    from vast_coevo.skills.library import LibrarySnapshot, LibraryStore, apply_patch, empty_snapshot
    from vast_coevo.skills.renderer import SkillRenderer
    from vast_coevo.skills.retriever import SkillContext, SkillRetriever
    from vast_coevo.skills.validation import StaticSkillGate

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    resumable = {"PREPARED", "BLOCKED_PREFLIGHT"}
    if substitute_patch_path is not None:
        resumable.update({"BLOCKED_PROVIDER_TIMEOUT", "RETEST_BLOCKED_LOCAL_SERIALIZATION"})
    if manifest.get("protocol") != SCHEMA_VERSION or manifest.get("status") not in resumable:
        raise ValueError("experiment is not in a resumable preflight state")
    existing_calls = list(root.glob("attempts/*/model-calls/*.json"))
    def actually_sent(path):
        row = json.loads(path.read_text(encoding="utf-8"))
        correction_path = path.parent.parent / "network-status-correction.json"
        if correction_path.is_file():
            correction = json.loads(correction_path.read_text(encoding="utf-8"))
            if correction.get("provider_requests_sent") is False:
                return False
        return bool(row.get("send_started", row.get("sent", False)))
    sent_before = sum(actually_sent(path) for path in existing_calls)
    if sent_before and substitute_patch_path is None:
        raise ValueError("a model call was already sent; refusing an automatic online retry")
    remaining_call_budget = MODEL_CALL_LIMIT - sent_before
    if remaining_call_budget <= 0:
        raise ValueError("registered experiment model-call ceiling is exhausted")
    attempts = sorted((root / "attempts").glob("*")) if (root / "attempts").exists() else []
    attempt = root / "attempts" / f"{len(attempts)+1:04d}"
    attempt.mkdir(parents=True)

    proxy = _proxy_status()
    attempt_manifest = {"attempt": len(attempts) + 1, "proxy": proxy,
                        "api_calls_sent": 0, "status": "PREFLIGHT"}
    try:
        env = dict(os.environ)
        env.setdefault("USAMI_LLM_MODEL", manifest["model"]["model"])
        env.setdefault("USAMI_LLM_BASE_URL", manifest["model"]["base_url"])
        env["USAMI_LLM_OPTIONS"] = "{}"  # preserve the user's no-output-cap setting
        env.setdefault("USAMI_LLM_TIMEOUT", str(manifest["model"]["timeout_seconds"]))
        env["USAMI_LLM_TRUST_ENV"] = "1"
        env.setdefault("USAMI_LLM_KEYCHAIN_SERVICE", "inferaiapi.com/v1")
        env.setdefault("USAMI_LLM_KEYCHAIN_ACCOUNT", "openai-api-key")
        settings = settings_from_env(env)
        key = key_from_env(env)
        if not key:
            raise ValueError("no InferAI credential resolved")
        if not proxy["available"]:
            raise ConnectionError("configured/user-reported proxy endpoint is not reachable")
        # The provider client reads standard proxy variables. Set the user-reported
        # endpoint only after a TCP listener is confirmed and only for this process.
        if proxy["source"] == "user_reported_local_port_probe":
            for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
                os.environ.setdefault(name, "http://127.0.0.1:65533")
            settings = settings.model_copy(update={"trust_env": True})
        inner = OpenAICompatibleClient(settings, key)
    except Exception as exc:
        attempt_manifest.update(status="BLOCKED_PREFLIGHT", reason=type(exc).__name__ + ": " + str(exc))
        atomic_json(attempt / "preflight.json", attempt_manifest, immutable=True)
        manifest["status"] = "BLOCKED_PREFLIGHT"
        manifest["latest_attempt"] = attempt_manifest
        atomic_json(manifest_path, manifest)
        return manifest

    recorder = CallLedger(attempt, limit=remaining_call_budget)
    reflection_client = RecordingClient("service_reflection", inner, settings, recorder)
    from vast_coevo.evidence import EvidenceArchive
    from vast_coevo.models import EpisodeEvidence, ModelSpec
    evidence = EvidenceArchive(root / "evidence").load(manifest["source"]["evidence_hash"])
    view = json.loads((root / "evidence/source-interaction-view.json").read_text(encoding="utf-8"))
    view_model = __import__("vast_coevo.reflection.evidence", fromlist=["InteractionEvidenceView"]).InteractionEvidenceView.model_validate(view)
    parent = LibrarySnapshot.model_validate_json((root / "libraries/service/parent.json").read_text(encoding="utf-8"))
    reflection_input = ReflectionInput(
        generation=1, role="service", library=parent, evidence=(evidence,),
        allowed_tools=tuple(base_adapter.TOOLS), domain_policy=DomainPolicy(add_domains=("aftersales",)),
        interaction_views=(view_model,), public_policy=json.dumps(base_adapter.POLICY, ensure_ascii=False, sort_keys=True),
        boundaries="A write needs a current exact Customer grant. A quote-backed irreversible settlement additionally requires an exact current structured confirmation; free text or a broad task goal is not that confirmation. Do not refuse legal operations by default.",
    )
    _write(attempt, "reflection/input.json", reflection_input)
    if substitute_patch_path is not None:
        from vast_coevo.skills.models import SkillPatch
        substitute_patch_path = substitute_patch_path.resolve()
        patch = SkillPatch.model_validate_json(substitute_patch_path.read_text(encoding="utf-8"))
        source_call_rows = [json.loads(path.read_text(encoding="utf-8")) for path in existing_calls
                            if actually_sent(path)]
        if not any(row.get("role") == "service_reflection" for row in source_call_rows):
            raise ValueError("offline substitute is only allowed after a sent Service Reflection call")
        provenance = {
            "kind": "codex_subagent_reflection_substitute",
            "is_deepseek_output": False,
            "provider_reflection_requests_this_attempt": 0,
            "source_patch_path": _rel(substitute_patch_path),
            "source_patch_sha256": digest(patch),
            "reflection_input_hash": digest(reflection_input),
            "source_evidence_hash": manifest["source"]["evidence_hash"],
            "prior_provider_reflection_timed_out": True,
            "dynamic_gate": "not run; isolated diagnostic retest only",
            "formal_snapshot_selection": False,
        }
        _write(attempt, "reflection/substitute-provenance.json", provenance, immutable=True)
        attempt_manifest.update(reflection_source="codex_subagent_offline_substitute",
                                reflection_provider_calls_this_attempt=0,
                                prior_provider_calls=sent_before,
                                api_calls_sent=0)
    else:
        reflector = ServiceReflector(reflection_client, ModelSpec(
            model=settings.model, base_url=settings.base_url, options=settings.options,
            timeout_seconds=settings.timeout_seconds, trust_env=settings.trust_env,
        ))
        reflection = reflector.reflect(reflection_input)
        _write(attempt, "reflection/record.json", reflection)
        attempt_manifest["api_calls_sent"] = recorder.calls
        if reflection.call is not None:
            attempt_manifest["reflection_call_id"] = reflection.call.id
            attempt_manifest["reflection_tokens"] = ((reflection.call.response or {}).get("usage", {})
                if isinstance(reflection.call.response, dict) else {})
        if reflection.patch is None:
            call_error = reflection.call.error if reflection.call is not None else None
            provider_code = call_error.get("code") if isinstance(call_error, dict) else None
            final_status = "BLOCKED_PROVIDER_TIMEOUT" if provider_code == "PROVIDER_TIMEOUT" else "REFLECTION_FAILED"
            attempt_manifest.update(status=final_status, reflection_error=reflection.error,
                                    provider_error_code=provider_code,
                                    provider_request_sent=recorder.calls == 1,
                                    retest_started=False)
            atomic_json(attempt / "status.json", attempt_manifest, immutable=True)
            manifest["status"] = final_status
            manifest["latest_attempt"] = attempt_manifest
            atomic_json(manifest_path, manifest)
            inner.close()
            return manifest
        patch = reflection.patch
    world_ids = set()
    for source_world in (base_adapter.World.model_validate(json.loads((root / "source/trace.json").read_text())["initial_world"]),
                         base_adapter.World.model_validate(json.loads((root / "retest/frozen_world.json").read_text())["world"])):
        raw_world = source_world.model_dump(mode="json")
        def collect(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"id", "order_id", "line_id", "scope_id", "case_id", "quote_id"} and isinstance(item, str):
                        world_ids.add(item)
                    collect(item)
            elif isinstance(value, list):
                for item in value: collect(item)
        collect(raw_world)
    gate = StaticSkillGate(allowed_tools=base_adapter.TOOLS,
                           forbidden_identifiers=world_ids, allowed_domains=("aftersales",))
    static = gate.validate(parent, patch)
    _write(attempt, "reflection/static-gate.json", static)
    if not static.passed or patch.action == "NOOP":
        attempt_manifest.update(status="NOOP" if patch.action == "NOOP" else "STATIC_REJECTED",
                                static_gate=static.model_dump(mode="json"), patch_hash=digest(patch))
        atomic_json(attempt / "status.json", attempt_manifest, immutable=True)
        manifest["status"] = attempt_manifest["status"]
        manifest["latest_attempt"] = attempt_manifest
        atomic_json(manifest_path, manifest)
        inner.close()
        return manifest

    if substitute_patch_path is not None:
        from vast_coevo.skills.models import SkillPatch
        candidate_path = substitute_patch_path.parent / "candidate-snapshot.json"
        candidate = LibrarySnapshot.model_validate_json(candidate_path.read_text(encoding="utf-8"))
        candidate_record = json.loads((substitute_patch_path.parent / "candidate-record.json").read_text(encoding="utf-8"))
        expected_candidate = apply_patch(parent, patch, candidate.provenance)
        if (candidate.parent_hash != parent.snapshot_hash or candidate.role != "service"
                or candidate.snapshot_hash != expected_candidate.snapshot_hash
                or candidate.snapshot_hash != candidate_record.get("candidate_snapshot_hash")
                or candidate_record.get("provenance", {}).get("author") != "Codex subagent; not DeepSeek and not a real-model Reflection"):
            raise ValueError("offline substitute candidate snapshot/provenance does not match its patch")
    else:
        candidate = apply_patch(parent, patch, "repair-from-oracle-verified-aftersales-errors")
    library_store = LibraryStore(root / "libraries/service")
    library_store.save(candidate)
    _write(attempt, "reflection/patch.json", patch, immutable=True)
    _write(attempt, "reflection/candidate-snapshot.json", candidate, immutable=True)

    frozen = json.loads((root / "retest/frozen_world.json").read_text(encoding="utf-8"))
    task_record = json.loads((root / "retest/certified_task.json").read_text(encoding="utf-8"))
    from usami_benchmark.worlds import FrozenWorld
    from usami_benchmark.tasks import CertifiedTask
    frozen = FrozenWorld.model_validate(frozen).checked()
    task_record = CertifiedTask.model_validate(task_record)
    verify_task(task_record)
    adapter = dialogue_adapter("aftersales", frozen.spec.rules_version)
    world = adapter.World.model_validate(frozen.world)
    task = task_record.dialogue_witnesses[0].certificate.task
    task_brief = aftersales_tasks.customer_task_brief(
        world, adapter.private_state(world, task.profile_id), task)
    retrieval = SkillRetriever("service").retrieve(candidate, SkillContext(
        domain="aftersales", public_text=task_brief,
        intents=("refund order resolution", "after-sales request", "explicit consent"),
        available_tools=tuple(adapter.TOOLS),
    ))
    if not retrieval.hits:
        attempt_manifest.update(status="SKILL_NOT_RETRIEVED", patch_hash=digest(patch),
                                snapshot_hash=candidate.snapshot_hash)
        atomic_json(attempt / "status.json", attempt_manifest, immutable=True)
        manifest["status"] = attempt_manifest["status"]
        manifest["latest_attempt"] = attempt_manifest
        atomic_json(manifest_path, manifest)
        inner.close()
        return manifest
    rendered = SkillRenderer().render(retrieval.skills)
    skill_context = SkillPromptContext(snapshot_hash=candidate.snapshot_hash,
                                       skill_ids=[hit.id for hit in retrieval.hits], rendered=rendered)
    run_config = TaskRunConfig(
        profile_id=task.profile_id, initial_world_hash=world.state_hash,
        mode="sandbox", tools=list(adapter.TOOLS),
        budget=RunBudget(max_customer_turns=8, max_customer_llm_calls=8,
                         max_service_llm_calls=16, max_service_tool_calls=48,
                         max_format_recoveries=0),
        external_schedule=task.external_schedule, task=task,
        certificate=task_record.dialogue_witnesses[0].certificate,
        witness=task_record.dialogue_witnesses[0].trace,
        skill_contexts={"service": skill_context},
    )
    customers = RecordingClient("customer", inner, settings, recorder)
    services = RecordingClient("service", inner, settings, recorder)
    _write(attempt, "retest/config.json", {"config": run_config, "skill_context": skill_context,
           "retrieval_hits": retrieval.hits, "rendered_skill": rendered,
           "customer_snapshot_hash": evidence.customer_snapshot_hash,
           "service_snapshot_hash": candidate.snapshot_hash})
    try:
        execution = run(adapter, world, run_config, customers, services)
    except Exception as exc:
        error = {
            "type": type(exc).__name__,
            "code": getattr(exc, "code", "RETEST_ERROR"),
            "message": str(exc),
            "provider_requests_this_attempt": recorder.calls,
            "automatic_retry": False,
            "episode_complete": False,
        }
        _write(attempt, "retest/error.json", error, immutable=True)
        attempt_manifest.update(status="RETEST_FAILED_NO_RETRY",
                                api_calls_sent=recorder.calls,
                                patch_hash=digest(patch),
                                candidate_snapshot_hash=candidate.snapshot_hash,
                                retest_started=True,
                                error=error)
        _write(attempt, "status.json", attempt_manifest, immutable=True)
        manifest["status"] = attempt_manifest["status"]
        manifest["latest_attempt"] = attempt_manifest
        atomic_json(manifest_path, manifest)
        inner.close()
        return manifest
    actual_score = score(adapter, world, task, execution.trace)
    replay_result = replay_execution(adapter, execution, world=world, config=run_config)
    system_requests = [call.record.request.get("messages", [])[0].get("content", "")
                       for call in execution.calls if call.role == "service"]
    injected = bool(system_requests) and all(
        candidate.snapshot_hash in content and rendered in content for content in system_requests)
    _write(attempt, "retest/execution.json", execution)
    _write(attempt, "retest/trace.json", execution.trace)
    _write(attempt, "retest/score.json", actual_score)
    _write(attempt, "retest/replay.json", replay_result)
    usage = execution.cost
    reflection_usage = attempt_manifest.get("reflection_tokens", {})
    total = {
        "model_calls_this_attempt": recorder.calls,
        "provider_requests_cumulative": sent_before + recorder.calls,
        "tool_calls": usage.get("tool_calls", 0),
        "customer_calls": usage.get("customer_calls", 0),
        "service_calls": usage.get("service_calls", 0),
        "reflection_calls_this_attempt": recorder.calls if substitute_patch_path is None else 0,
        "prior_timed_out_reflection_requests": sent_before if substitute_patch_path is not None else 0,
        "reflection_usage": reflection_usage,
        "episode_usage": {key: usage.get(key) for key in
                           ("input_tokens", "output_tokens", "total_tokens", "usage_complete")},
    }
    provider_error_calls = [call for call in execution.calls if call.record.error]
    provider_error = None
    if provider_error_calls:
        failed_call = provider_error_calls[-1]
        provider_error = {
            "role": failed_call.role,
            "code": failed_call.record.error.get("code"),
            "message": failed_call.record.error.get("message"),
            "automatic_retry": False,
        }
    if provider_error and "HTTP 429" in (provider_error.get("message") or ""):
        run_status = "BLOCKED_RETEST_PROVIDER_RATE_LIMIT"
    elif provider_error:
        run_status = "BLOCKED_RETEST_PROVIDER_ERROR"
    else:
        run_status = ("RETEST_COMPLETED_WITH_SUBAGENT_PATCH"
                      if substitute_patch_path is not None else "COMPLETED")
    attempt_manifest.update(
        status=run_status,
        api_calls_sent=total["model_calls_this_attempt"],
        patch_action=patch.action, patch_hash=digest(patch),
        snapshot_hash=candidate.snapshot_hash, parent_snapshot_hash=parent.snapshot_hash,
        static_gate=static.model_dump(mode="json"), skill_retrieval_hits=[hit.model_dump(mode="json") for hit in retrieval.hits],
        skill_injection_verified=injected, task_hash=task_record.task_hash,
        world_hash=frozen.world_hash, final_goal_reached=all(actual_score.get("completion_subgoals", [])),
        task_success=actual_score.get("success"), oracle_status=execution.oracle.get("status"),
        oracle_metrics=execution.oracle.get("metrics"), replay=replay_result, cost=total,
        provider_error=provider_error,
        full_episode_completed=not bool(provider_error),
    )
    _write(attempt, "status.json", attempt_manifest, immutable=True)
    manifest["status"] = attempt_manifest["status"]
    manifest["latest_attempt"] = attempt_manifest
    atomic_json(manifest_path, manifest)
    inner.close()
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--prepare", action="store_true", help="verify source and freeze the new order; no LLM call")
    parser.add_argument("--run-live", action="store_true", help="one Reflection call and one bounded real-model retest")
    parser.add_argument("--retest-with-patch", type=Path,
                        help="use a recorded offline Service SkillPatch instead of retrying Reflection; run one bounded real-model retest")
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    if args.prepare:
        manifest = prepare(args.root)
        print(json.dumps({"status": manifest["status"], "root": _rel(args.root),
                          "source_replay": manifest["source"]["outer_replay"],
                          "source_errors": len(manifest["source"]["errors"]),
                          "new_task_hash": manifest["retest"]["task_hash"]}, ensure_ascii=False))
    elif args.run_live:
        manifest = run_live(args.root)
        print(json.dumps({"status": manifest["status"], "root": _rel(args.root),
                          "latest_attempt": manifest.get("latest_attempt", {})}, ensure_ascii=False))
    elif args.retest_with_patch:
        manifest = run_live(args.root, args.retest_with_patch)
        print(json.dumps({"status": manifest["status"], "root": _rel(args.root),
                          "latest_attempt": manifest.get("latest_attempt", {})}, ensure_ascii=False))
    else:
        parser.error("choose --prepare or --run-live")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
