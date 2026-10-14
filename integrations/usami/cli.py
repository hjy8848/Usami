"""Concrete research CLI; all Usami imports remain outside VAST-CoEvo Core."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from typing import Literal, Optional, Tuple

from pydantic import Field, model_validator
from vast_coevo.models import Budget, EpisodeEvidence, ModelSpec
from vast_coevo.schema import FrozenModel, atomic_json, digest
from vast_coevo.skills.library import LibrarySnapshot, LibraryStore
from vast_coevo.evidence.archive import EvidenceArchive
from vast_coevo.evolution.models import GatePolicy, RunConfig, ValidationCase
from vast_coevo.evolution.controller import CoEvolutionController
from vast_coevo.storage.runs import RunStore
from vast_coevo.reflection.reflector import CustomerReflector, ServiceReflector, ReflectionInput
from vast_coevo.reflection.scope import DomainPolicy
from .adapter import UsamiAdapter
from .domains import UsamiProfile, ServiceTaskProfile, model_settings, native_task


class TaskCase(FrozenModel):
    task_ref: str
    purpose: Literal["legal_completion", "correct_refusal"]


class ExperimentPlan(FrozenModel):
    schema_version: Literal[1] = 1
    profiles: Tuple[UsamiProfile, ...] = Field(min_length=1)
    service_tasks: Tuple[ServiceTaskProfile, ...] = ()
    exploration: Tuple[str, ...] = Field(min_length=1)
    validation: Tuple[str, ...] = Field(min_length=1)
    regressions: Tuple[TaskCase, ...] = ()
    customer_library: str
    service_library: str
    customer_model: Optional[ModelSpec] = None
    service_model: Optional[ModelSpec] = None
    customer_reflector_model: Optional[ModelSpec] = None
    service_reflector_model: Optional[ModelSpec] = None
    budget: Budget = Field(default_factory=Budget)
    task_budget: Budget = Field(default_factory=lambda: Budget(max_customer_turns=1, max_customer_llm_calls=0,
                                                              max_service_llm_calls=14, max_service_tool_calls=24))
    generations: int = Field(default=1, ge=1, strict=True)
    max_llm_calls: int = Field(default=500, ge=2, strict=True)
    max_tool_calls: int = Field(default=1000, ge=0, strict=True)
    policy: GatePolicy = Field(default_factory=GatePolicy)

    @model_validator(mode="after")
    def registry(self):
        ids = {p.config_id for p in self.profiles}
        tasks = {t.task_ref for t in self.service_tasks}
        if set(self.exploration + self.validation) - ids or {r.task_ref for r in self.regressions} - tasks:
            raise ValueError("experiment plan references an unregistered case")
        if any(p.split == "heldout" for p in self.profiles if p.config_id in self.exploration + self.validation):
            raise ValueError("heldout profiles cannot be selected for development")
        return self


def model_from_env(role, fallback=None):
    """Pin actual configuration once; secret lookup remains in native transport."""
    from usami.service.client import settings_from_env
    env = dict(os.environ)
    prefix = "VAST_" + role.upper() + "_"
    configured = False
    for suffix in ("MODEL", "BASE_URL", "OPTIONS", "TIMEOUT", "TRUST_ENV"):
        if prefix + suffix in env:
            env["USAMI_LLM_" + suffix] = env[prefix + suffix]
            configured = True
    if fallback is not None and not configured:
        return fallback
    settings = settings_from_env(env)
    return ModelSpec(model=settings.model, base_url=settings.base_url, options=settings.options,
                     timeout_seconds=settings.timeout_seconds, trust_env=settings.trust_env)


def context(plan_path, root):
    plan_path, root = Path(plan_path).resolve(), Path(root).resolve()
    plan = ExperimentPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
    customer = LibrarySnapshot.model_validate_json((plan_path.parent / plan.customer_library).read_text())
    service = LibrarySnapshot.model_validate_json((plan_path.parent / plan.service_library).read_text())
    store = LibraryStore(root / "libraries")
    store.save(customer)
    store.save(service)
    adapter = UsamiAdapter(root / "native", plan.profiles, plan.service_tasks)
    archive = EvidenceArchive(root / "evidence")
    runs = RunStore(root / "runs")
    specs = {role: model_from_env(role, getattr(plan, role + "_model"))
             for role in ("customer", "service", "customer_reflector", "service_reflector")}
    return plan, adapter, store, archive, runs, customer, service, specs


def run_config(plan, adapter, customer, service, specs, run_id, generations=None):
    def case(config_id, task_ref=None, purpose=None):
        config = adapter.config_for(config_id, specs["customer"], specs["service"],
                                    plan.task_budget if task_ref else plan.budget, task_ref=task_ref)
        return ValidationCase(id=task_ref or config_id, config=config, task_ref=task_ref, purpose=purpose)
    profiles = {p.config_id: p for p in plan.profiles}
    tasks = {t.task_ref: t for t in plan.service_tasks}
    task_cases = []
    for regression in plan.regressions:
        task = tasks[regression.task_ref]
        _, actual, _ = native_task(profiles[task.config_id], task)
        expected = "correct_refusal" if actual.kind == "policy_refusal" else "legal_completion"
        if regression.purpose != expected:
            raise ValueError("declared regression purpose differs from native task kind")
        task_cases.append(case(task.config_id, task.task_ref, regression.purpose))
    return RunConfig(run_id=run_id, generations=generations or plan.generations,
                     exploration_cases=tuple(case(key) for key in plan.exploration),
                     validation_cases=tuple(case(key) for key in plan.validation), service_task_cases=tuple(task_cases),
                     customer_reflector_model=specs["customer_reflector"], service_reflector_model=specs["service_reflector"],
                     max_llm_calls=plan.max_llm_calls, max_tool_calls=plan.max_tool_calls, policy=plan.policy,
                     initial_customer_hash=customer.snapshot_hash, initial_service_hash=service.snapshot_hash)


def transport(spec):
    from usami.service.client import OpenAICompatibleClient, key_from_env
    return OpenAICompatibleClient(model_settings(spec), key_from_env())


def _evidence(value, archive):
    path = Path(value)
    if path.is_file():
        row = EpisodeEvidence.model_validate_json(path.read_text())
        EvidenceArchive.verify_artifact(row.trace)
        return row
    return archive.load(value)


def main(argv=None):
    parser = argparse.ArgumentParser(description="VAST-CoEvo on the unchanged Usami business worlds")
    parser.add_argument("--root", default="artifacts/vast-coevo", help="persistent run/evidence/library directory")
    parser.add_argument("--plan", help="versioned experiment plan (required for online execution and replay)")
    commands = parser.add_subparsers(dest="command", required=True)
    library = commands.add_parser("library", help="inspect immutable skill snapshots")
    library.add_argument("--hash")
    episode = commands.add_parser("episode", help="run one autonomous static Skill interaction")
    episode.add_argument("--profile", required=True)
    episode.add_argument("--id", required=True)
    reflect = commands.add_parser("reflect", help="one real Reflection, one patch; no automatic retry")
    reflect.add_argument("--role", choices=("customer", "service"), required=True)
    reflect.add_argument("--evidence", action="append", required=True)
    reflect.add_argument("--generation", type=int, default=0)
    reflect.add_argument("--output", required=True)
    run = commands.add_parser("run", help="run or resume one or multiple alternating generations")
    run.add_argument("--id", required=True)
    run.add_argument("--generations", type=int)
    history = commands.add_parser("history", help="inspect saved generation history")
    history.add_argument("--id", required=True)
    restore = commands.add_parser("restore", help="branch a historical snapshot into a new run")
    restore.add_argument("--source", required=True)
    restore.add_argument("--id", required=True)
    restore.add_argument("--generation", type=int)
    restore.add_argument("--generations", type=int)
    replay = commands.add_parser("replay", help="offline exact skill/wire/native/oracle replay")
    replay.add_argument("--evidence", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    store, archive, runs = LibraryStore(root / "libraries"), EvidenceArchive(root / "evidence"), RunStore(root / "runs")
    try:
        if args.command == "library":
            output = store.load(args.hash).model_dump(mode="json") if args.hash else {"hashes": store.hashes()}
        elif args.command == "history":
            output = {"generations": [g.model_dump(mode="json") for g in runs.history(args.id)],
                      "report": runs.load_report(args.id).model_dump(mode="json")}
        elif args.command == "restore":
            output = runs.branch_config(args.source, args.id, args.generation, args.generations).model_dump(mode="json")
        else:
            if not args.plan:
                raise ValueError("--plan is required")
            if args.command == "replay":
                # Offline replay does not need model environment or credentials.
                plan = ExperimentPlan.model_validate_json(Path(args.plan).read_text())
                adapter = UsamiAdapter(root / "native", plan.profiles, plan.service_tasks)
                evidence = _evidence(args.evidence, archive)
                output = adapter.replay(evidence, store.load(evidence.customer_snapshot_hash),
                                        store.load(evidence.service_snapshot_hash)).model_dump(mode="json")
                print(json.dumps(output, ensure_ascii=False, indent=2))
                return 0 if output["verified"] else 2
            if args.command == "reflect" and (Path(args.output).exists() or Path(args.output + ".started.json").exists()):
                raise ValueError("Reflection output or in-flight marker already exists; no duplicate call performed")
            plan, adapter, store, archive, runs, customer, service, specs = context(args.plan, root)
            if args.command == "episode":
                config = adapter.config_for(args.profile, specs["customer"], specs["service"], plan.budget)
                evidence = adapter.run_episode(config, customer, service, args.id)
                archive.save(evidence)
                output = evidence.model_dump(mode="json")
            elif args.command == "replay":
                evidence = _evidence(args.evidence, archive)
                customer = store.load(evidence.customer_snapshot_hash)
                service = store.load(evidence.service_snapshot_hash)
                output = adapter.replay(evidence, customer, service).model_dump(mode="json")
            elif args.command == "reflect":
                rows = tuple(_evidence(item, archive) for item in args.evidence)
                for row in rows:
                    checked = adapter.replay(row, store.load(row.customer_snapshot_hash), store.load(row.service_snapshot_hash))
                    if not checked.verified:
                        raise ValueError("Reflection evidence failed native verification: " + checked.reason)
                snapshot = customer if args.role == "customer" else service
                client = transport(specs[args.role + "_reflector"])
                try:
                    klass = CustomerReflector if args.role == "customer" else ServiceReflector
                    profiles = {profile.config_id: profile for profile in plan.profiles}
                    tasks = {task.task_ref: task for task in plan.service_tasks}
                    scope_profiles = set(plan.validation) | {tasks[row.task_ref].config_id for row in plan.regressions}
                    value = ReflectionInput(generation=args.generation, role=args.role, library=snapshot, evidence=rows,
                                            interaction_views=tuple(adapter.reflection_view(row) for row in rows) if args.role == "customer" else None,
                                            domain_policy=DomainPolicy(add_domains=tuple(sorted({profiles[key].domain for key in scope_profiles}))),
                                            allowed_tools=tuple(sorted({t for row in rows for t in row.config.tools})),
                                            public_policy=json.dumps([adapter.public_policy(row.config) for row in rows], sort_keys=True))
                    atomic_json(Path(args.output + ".started.json"), {"schema_version": 1,
                                "input_hash": digest(value), "model": specs[args.role + "_reflector"].model_dump(mode="json")}, immutable=True)
                    result = klass(client, specs[args.role + "_reflector"]).reflect(value)
                finally:
                    client.close()
                atomic_json(Path(args.output), result.model_dump(mode="json"), immutable=True)
                output = result.model_dump(mode="json")
            else:
                config = runs.load_config(args.id) if (root / "runs" / args.id / "config.json").exists() else run_config(
                    plan, adapter, customer, service, specs, args.id, args.generations)
                clients = [transport(config.customer_reflector_model), transport(config.service_reflector_model)]
                try:
                    output = CoEvolutionController(adapter, *clients, store, archive, runs).run(config).model_dump(mode="json")
                finally:
                    for client in clients:
                        client.close()
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if args.command == "replay" and not output["verified"]:
            return 2
        if args.command == "run" and output["status"] != "completed":
            return 2
        return 0
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, "VAST-CoEvo: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
