"""Run one RSI v0.2 period on certified Usami commerce episodes.

This is an integration smoke, not an LLM or learning experiment. The ResearchModel
returns fixed candidate artifacts and Service P programs execute through the native
Usami Customer, Engine, Oracle, and Replay. No API or verl training is started.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time

from integrations.rsi_usami.adapter import NativeTask, UsamiAdapter
from integrations.rsi_usami.packages import NativePackageVerifier
from rsi_core.archive import Archive
from rsi_core.budget import Ledger
from rsi_core.evaluation import Evaluator, ServiceEvaluator
from rsi_core.isolation import DockerWorker
from rsi_core.packages import (PackageProvider, PackageRegistration,
                               ServiceTaskProvider, ServiceTaskRegistration)
from rsi_core.period import run_period
from rsi_core.programs import (DesignerSnapshot, ExperienceArtifact, ProgramArtifact,
                               ProgramStore, ServiceSnapshot)
from rsi_core.protocol import (AdaptationPackage, Completion, FrozenModels, Limits,
                               ModelSnapshot, digest)
from rsi_core.runtime import ResearchHost
from usami_v2.runtime.customer import CustomerDecision, CustomerProfileV2
from usami_v2.runtime.runner import EpisodeBudget
from usami_v2.scenarios.builder import build_world
from usami_v2.scenarios.schema import (Attribute, IntegerRange, LineVariable,
                                       OrderVariable, ScenarioSpec, SKUVariable,
                                       WarehouseVariable)
from usami_v2.scenarios.task_certification import (CustomerScenario, certify_task,
                                                    verify_task_certificate)
from usami_v2.scenarios.tasks import GroundedRemedyGoal, TaskSpecV2


IMAGE = "sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf"
DOMAIN = UsamiAdapter.domain_id
DEVICE_REQUEST = "Please refund my damaged device."
CABLE_REQUEST = "Please refund my cable that arrived with missing parts."
DISTRIBUTION = digest("usami-rsi-native-period-smoke-v1")
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def _fixed(value):
    return IntegerRange(low=value, high=value)


def _scenario():
    return ScenarioSpec(
        scenario_id="usami-rsi-native-refund-smoke-v1",
        provenance_kind="offline_fixture",
        customer_aliases=("customer",),
        skus=(
            SKUVariable(alias="device", family="device",
                        attributes=(Attribute(name="model", value="Reference device"),),
                        price_cents=_fixed(20000)),
            SKUVariable(alias="cable", family="cable",
                        attributes=(Attribute(name="interface", value="USB-C"),),
                        price_cents=_fixed(2000)),
        ),
        warehouses=(WarehouseVariable(alias="fast", delivery_days=_fixed(2),
                                       delivery_fee_cents=_fixed(0)),),
        orders=(OrderVariable(
            alias="purchase", customer_alias="customer", delivered_days_ago=_fixed(1),
            lines=(
                LineVariable(alias="damaged_device", original_sku="device", quantity=_fixed(1),
                             paid_cents=_fixed(20000), issue="damaged", evidence_valid=True),
                LineVariable(alias="missing_parts_cable", original_sku="cable", quantity=_fixed(1),
                             paid_cents=_fixed(2000), issue="missing_parts", evidence_valid=True),
            ),
        ),),
        default_stock=_fixed(2),
    )


class SmokeCustomer:
    """Deterministic Customer policy; native CustomerRuntime enforces consent."""
    last_call = None
    uses_model = False

    def decide(self, prompt, profile):
        if prompt.offer:
            return CustomerDecision(message="I accept this refund quote.",
                                    accept_quote_id=prompt.offer.quote_id,
                                    accept_operation=prompt.offer.operation, finish=True)
        return CustomerDecision(message="Thank you.", finish=True)


def _native_task(seed, task_ref, request, product, issue):
    built = build_world(_scenario(), seed)
    if built.status != "SAT" or built.world is None:
        raise RuntimeError("native Usami world builder did not produce SAT: " + built.reason)
    aliases = dict(built.private_aliases)
    line_id = aliases[product]
    goal = GroundedRemedyGoal(
        goal_id="refund-requested-item", line_id=line_id, quantity=1,
        public_request_span=request,
        subject_mention="cable" if product == "missing_parts_cable" else "damaged device",
        allowed_remedies=("refund",), maximum_extra_charge_cents=0,
    )
    task = TaskSpecV2(
        task_id=task_ref, world_hash=built.world.state_hash,
        customer_id=aliases["customer"], customer_request=request,
        remedy_goals=(goal,), partition="train", source_distribution_hash=DISTRIBUTION,
    )
    profile = CustomerProfileV2(
        customer_id=aliases["customer"], delegated_line_ids=(line_id,),
        delegation_request_spans={line_id: request},
    )
    scenario = CustomerScenario(customer_id=aliases["customer"], delegated_line_ids=(line_id,))
    certificate = certify_task(built.world, task, scenario)
    if certificate.status != "CERTIFIED" or not certificate.business_reachability_certified:
        raise RuntimeError("native Usami Reference could not certify " + task_ref + ": "
                           + ",".join(certificate.blockers))
    if verify_task_certificate(built.world, task, scenario, certificate)["verified"] is not True:
        raise RuntimeError("native Usami task certificate did not independently replay")
    budget = EpisodeBudget(max_customer_turns=6, max_service_decisions=24,
                           max_service_tool_calls=20, max_model_calls=0)
    return NativeTask(built.world, task, profile, SmokeCustomer, budget), scenario, certificate


def _service_source():
    source = (SOURCE_ROOT / "refund_public_controller.py").read_text(encoding="utf-8")
    signature = "def step(view, state):"
    if source.count(signature) != 1:
        raise RuntimeError("public refund controller entrypoint changed")
    body = source.split(signature, 1)[1]
    limited = (
        "import json\n\n"
        "def _device_refund(view, state):" + body + "\n\n"
        "def step(view, state):\n"
        "    if 'cable' in view['customer_request'].casefold():\n"
        "        return {'kind':'ACTION','state':state,'action':{"
        "'kind':'reply','message':'I cannot process this cable refund yet.'}}\n"
        "    return _device_refund(view, state)\n"
    )
    old_line = (
        'state["line"] = next(line["id"] for line, sku in zip(state["lines"], state["skus"])\n'
        '                             if sku["product_family"] == "device")'
    )
    new_line = (
        'request = view["customer_request"].casefold()\n'
        '        family = "cable" if "cable" in request else "device"\n'
        '        state["issue"] = "missing_parts" if "missing parts" in request else "damaged"\n'
        '        state["line"] = next(line["id"] for line, sku in zip(state["lines"], state["skus"])\n'
        '                             if sku["product_family"] == family)'
    )
    if source.count(old_line) != 1:
        raise RuntimeError("public refund controller product-selection contract changed")
    general = source.replace(old_line, new_line)
    if general.count('"issue": "damaged"') != 1:
        raise RuntimeError("public refund controller issue-selection contract changed")
    general = general.replace('"issue": "damaged"', '"issue": state["issue"]')
    if general.count('if row["issue"] == "damaged"') != 1:
        raise RuntimeError("public refund controller evidence-selection contract changed")
    general = general.replace('if row["issue"] == "damaged"', 'if row["issue"] == state["issue"]')
    return limited, general


class ScriptedResearchModel:
    """Fixed response fixture for protocol execution; token data is synthetic."""

    def __init__(self, baseline_source, candidate_source, m_candidate_source):
        self.baseline_source = baseline_source
        self.candidate_source = candidate_source
        self.m_candidate_source = m_candidate_source
        self.calls = []

    def complete(self, snapshot, request, *, max_tokens, seed):
        request_body = request["request"]
        instruction = request_body.get("instruction", "")
        if "propose one frozen-world Service challenge" in instruction:
            output = {"proposal": {"customer_request": DEVICE_REQUEST, "remedy": "refund"}}
            purpose = "challenge_proposal"
        elif "complete (P,K) improvement" in instruction:
            output = {"policy_source": self.candidate_source,
                      "experience": {"source": "fixed native-period smoke candidate"}}
            purpose = "service_candidate"
        elif "Propose up to two executable candidates" in instruction:
            output = {"sources": [self.m_candidate_source]}
            purpose = "designer_program_candidate"
        elif "Adapt the complete Service copy" in instruction:
            output = {"policy_source": self.baseline_source,
                      "experience": {"source": "fixed M0 adaptation response"}}
            purpose = "M0_adaptation"
        else:
            raise ValueError("unregistered smoke ResearchModel request: " + instruction[:100])
        self.calls.append({"snapshot_ref": snapshot.ref, "purpose": purpose, "seed": seed})
        # One-token metadata satisfies protocol shape only; it is not tokenizer output.
        return Completion(output, 1, 1, (seed,), (-0.01,), (seed,))


def _m1_source(candidate_service_source):
    return """def next_step(view, state):
    if view["mode"] != "EVALUATE_ADAPT":
        return {"action":"SUBMIT","state":{},"candidate_ref":view["target"]["ref"]}
    phase = state.get("phase", 0)
    target = view["target"]["ref"]
    if phase == 0:
        return {"action":"STAGE","state":{"phase":1},"kind":"SERVICE_BUNDLE",
                "policy_source": """ + repr(candidate_service_source) + """,
                "experience":{"source":"M1 fixed domain adaptation"},"parent_ref":target}
    if phase == 1:
        previous = view["observations"][-1]
        if previous.get("kind") != "STAGE" or previous.get("status") != "VALID":
            return {"action":"SUBMIT","state":{},"candidate_ref":target}
        candidate = previous["candidate_ref"]
        return {"action":"PROBE","state":{"phase":2,"candidate":candidate},
                "candidate_ref":target,"probe_ref":view["capabilities"]["probe_refs"][0]}
    if phase == 2:
        previous = view["observations"][-1]
        base_score = previous["result"]["score"]
        return {"action":"PROBE","state":{"phase":3,"candidate":state["candidate"],
                "base_score":base_score},"candidate_ref":state["candidate"],
                "probe_ref":view["capabilities"]["probe_refs"][0]}
    previous = view["observations"][-1]
    winner = state["candidate"] if previous["result"]["score"] > state["base_score"] else target
    return {"action":"SUBMIT","state":{},"candidate_ref":winner}
"""


def _register_native(task_ref, seed, request, product, issue, tasks, verifier, origin, adapter=None):
    native, scenario, certificate = _native_task(seed, task_ref, request, product, issue)
    if adapter is not None:
        adapter.register_task(task_ref, native)
    try:
        proof = verifier.register(task_ref, native, origin, scenario, certificate)
    except Exception:
        if adapter is not None:
            del adapter.tasks[task_ref]
        raise
    tasks[task_ref] = native
    if verifier(DOMAIN, proof) is not True:
        raise RuntimeError("native task certificate registry failed verification")
    return proof


def _service_registry(tasks, verifier, archive):
    rows, task_sets = [], {}
    for index, purpose in enumerate(("service_probe", "service_select", "service_reward")):
        task_ref = purpose + "-device-refund"
        proof = _register_native(task_ref, 10 + index, DEVICE_REQUEST, "damaged_device",
                                 "damaged", tasks, verifier, "native-smoke/" + purpose + "/device")
        rows.append(ServiceTaskRegistration(
            purpose + "-set", DOMAIN, "native-smoke-family-" + purpose,
            "native-smoke-lineage-" + purpose, "meta-train", purpose, (proof,), seed=31 + index))
    provider = ServiceTaskProvider(rows, archive, verifier)
    for purpose in ("service_probe", "service_select", "service_reward"):
        task_sets[purpose] = provider.sets(purpose)[0]
    return provider, task_sets


def _self_edit_context(host, service, tasks, verifier, archive, adapter):
    registrations = []
    for index, purpose in enumerate(("C_probe", "C_select", "C_reward")):
        probe_ref, query_ref = purpose + "-cable-probe", purpose + "-cable-query"
        probe_proof = _register_native(probe_ref, 30 + index, CABLE_REQUEST,
                                      "missing_parts_cable", "missing_parts", tasks,
                                      verifier, "native-smoke/" + purpose + "/probe", adapter)
        query_proof = _register_native(query_ref, 40 + index, CABLE_REQUEST,
                                       "missing_parts_cable", "missing_parts", tasks,
                                       verifier, "native-smoke/" + purpose + "/query", adapter)
        package = AdaptationPackage(
            "native-smoke-" + purpose, DOMAIN, "native-smoke-family-" + purpose,
            "native-smoke-lineage-" + purpose, "meta-train", purpose, service.ref,
            (), (probe_ref,), (query_ref,),
            {"task_interface": "public Usami tools; settle an explicitly requested refund"},
            seed=51 + index)
        registrations.append(PackageRegistration(package, (), (probe_proof, query_proof)))
    provider = PackageProvider(registrations, archive, verifier)
    sampled = provider.sample_training_context(20261024, counts={
        "C_probe": 1, "C_select": 1, "C_reward": 1})
    return {"probe_packages": sampled.probe, "select_packages": sampled.selection,
            "reward_packages": sampled.reward, "seeds": (101, 202),
            "phase_budgets": _self_budgets(), "sampling_ref": sampled.archive_ref,
            "public_view": {"domain": DOMAIN, "integration": "native_usami_commerce"}}


def _service_budgets():
    return {
        "root": {"model_calls": 2, "model_tokens": 1000, "episodes": 2,
                 "tool_steps": 40, "research_steps": 64, "cpu_seconds": 300},
        "selection": {"episodes": 2, "tool_steps": 40,
                      "research_steps": 64, "cpu_seconds": 300},
        "reward": {"episodes": 2, "tool_steps": 40,
                   "research_steps": 64, "cpu_seconds": 300},
    }


def _self_budgets():
    return {
        "root": {"model_calls": 8, "model_tokens": 4000, "episodes": 8,
                 "tool_steps": 160, "research_steps": 240, "cpu_seconds": 600},
        "selection": {"model_calls": 4, "model_tokens": 2000, "episodes": 8,
                      "tool_steps": 160, "research_steps": 240, "cpu_seconds": 600},
        "reward": {"model_calls": 4, "model_tokens": 2000, "episodes": 8,
                   "tool_steps": 160, "research_steps": 240, "cpu_seconds": 600},
    }


def _episode_summary(adapter):
    rows = []
    for run_ref, path in adapter.runs.items():
        from usami_v2.runtime.runner import EpisodeRecord
        record = EpisodeRecord.model_validate_json(path.read_text(encoding="utf-8"))
        rows.append({"run_ref": run_ref, "task_id": record.task.task_id,
                     "status": record.status,
                     "strict_task_success": record.outcome.strict_task_success,
                     "process_errors": record.outcome.process_errors.status,
                     "safety": record.outcome.safety_violations.status,
                     "service_tool_calls": len(record.tool_executions),
                     "replay_verified": adapter.replay(run_ref)["verified"]})
    return rows


def run(output, *, image=IMAGE):
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    limits = Limits(model_calls=64, model_tokens=20000, episodes=64, tool_steps=1200,
                    research_steps=2048, cpu_seconds=7200, wall_seconds=1800)
    behavior = ModelSnapshot("scripted-research-fixture", "fixed-responses-v1")
    evaluator_model = ModelSnapshot("scripted-evaluator-fixture", "fixed-responses-v1")
    business = ModelSnapshot("native-service-program-fixture", "no-online-model-v1")
    models = FrozenModels(behavior, evaluator_model, business)
    archive, store = Archive(root / "archive"), ProgramStore(root / "programs")
    worker = DockerWorker(image, limits)
    tasks = {}
    verifier = NativePackageVerifier(tasks, archive)
    probe_provider, task_sets = _service_registry(tasks, verifier, archive)
    baseline_source, candidate_source = _service_source()
    m0_source = (Path(__file__).resolve().parents[1] / "seeds" / "M0.py").read_text(encoding="utf-8")
    m1_source = _m1_source(candidate_source)
    model = ScriptedResearchModel(baseline_source, candidate_source, m1_source)
    host = ResearchHost(store, archive, worker, model, models, Ledger(limits),
                        max_steps=24, max_output_tokens=4000)
    adapter = UsamiAdapter(tasks, root / "native-episodes")
    service_evaluator = ServiceEvaluator(host, adapter, probe_provider)
    adaptation_evaluator = Evaluator(host, adapter)

    service0 = ServiceSnapshot(business.ref, ProgramArtifact("P", baseline_source),
                               ExperienceArtifact())
    designer0 = DesignerSnapshot(behavior, ProgramArtifact("M", m0_source))
    store.publish_service(service0)
    store.publish_designer(designer0)

    # The Designer proposes intent against this already-built frozen world. The
    # callback compiles the public request into a native TaskSpecV2 and refuses
    # all task types outside this smoke's explicit task contract.
    challenge_world, challenge_aliases = None, None
    world_build = build_world(_scenario(), 99)
    if world_build.status != "SAT":
        raise RuntimeError("frozen native challenge world is not SAT")
    challenge_world, challenge_aliases = world_build.world, dict(world_build.private_aliases)

    # Keep the challenge proof lookup explicit and deterministic across the two
    # independent roots that propose the same certified intent.
    _challenge_proofs = []
    register_challenge = _compile_challenge_factory(tasks, verifier, _challenge_proofs, adapter)

    def certify_challenge(proposal):
        if (set(proposal) != {"customer_request", "remedy"}
                or proposal.get("customer_request") != DEVICE_REQUEST
                or proposal.get("remedy") != "refund"):
            return {"status": "INVALID", "reason_code": "unsupported_or_ungrounded_native_task"}
        task_ref = "designer-challenge-device-refund"
        if task_ref not in tasks:
            proof = register_challenge(challenge_world, challenge_aliases,
                                       task_ref, DEVICE_REQUEST)
        else:
            proof = next(row for row in _challenge_proofs if row.task_ref == task_ref)
        if verifier(DOMAIN, proof) is not True:
            raise RuntimeError("challenge certificate did not independently verify")
        return {"status": "CERTIFIED", "task_ref": task_ref,
                "certificate_ref": proof.certificate_ref,
                "certification_scope": "usami_v2.native_reference_task_certification",
                "frozen": True}

    def self_context(final_service):
        return _self_edit_context(host, final_service, tasks, verifier, archive, adapter)

    result = run_period(
        host, service_evaluator, adaptation_evaluator, designer0, service0,
        service_rounds=({
            "probe_tasks": task_sets["service_probe"],
            "select_tasks": task_sets["service_select"],
            "reward_tasks": task_sets["service_reward"],
            "seeds": (11, 22), "phase_budgets": _service_budgets(),
            "certify_challenge": certify_challenge,
            "public_view": {"domain": DOMAIN,
                            "challenge_space": [{"request": DEVICE_REQUEST,
                                                 "remedy": "refund",
                                                 "world": "frozen seed 99"}]},
        },),
        self_edit_context=self_context,
    )

    episodes = _episode_summary(adapter)
    if not episodes or any(row["replay_verified"] is not True for row in episodes):
        raise RuntimeError("native period produced no episodes or a failed Usami Replay")
    report = {"kind": "rsi_v02_usami_native_period_smoke_v1",
              "native_domain": DOMAIN,
              "period": result, "service_task_sets": {key: asdict(value)
                                                         for key, value in task_sets.items()},
              "native_task_refs": sorted(tasks), "native_episodes": episodes,
              "native_episode_count": len(episodes),
              "native_replays_verified": sum(row["replay_verified"] is True for row in episodes),
              "scripted_research_calls": model.calls,
              "scripted_research_call_count": len(model.calls),
              "online_model_calls": 0, "verl_training_runs": 0,
              "parameter_updates": 0,
              "interpretation": "Usami Engine/Oracle/Replay and RSI period wiring executed; "
                                "candidate generation is scripted and no model learning was tested."}
    report_path = root / "summary.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "training_status": result["training_status"],
                      "service_round_status": result["service_rounds"][0]["group_status"],
                      "designer_group_status": archive.load(result["self_edit_group_ref"])["status"],
                      "native_episodes": len(episodes),
                      "native_replays_verified": report["native_replays_verified"],
                      "online_model_calls": 0, "parameter_updates": 0,
                      "summary": str(report_path)}, ensure_ascii=False, indent=2))
    return report


def _profile(aliases, product, request):
    line = aliases[product]
    return CustomerProfileV2(customer_id=aliases["customer"], delegated_line_ids=(line,),
                             delegation_request_spans={line: request})


def _compile_challenge(world, aliases, task_ref, request):
    line_id = aliases["damaged_device"]
    from usami_v2.scenarios.tasks import GroundedRemedyGoal, TaskSpecV2
    from usami_v2.scenarios.task_certification import CustomerScenario, certify_task
    task = TaskSpecV2(
        task_id=task_ref, world_hash=world.state_hash, customer_id=aliases["customer"],
        customer_request=request,
        remedy_goals=(GroundedRemedyGoal(
            goal_id="refund-requested-device", line_id=line_id, quantity=1,
            public_request_span=request, subject_mention="damaged device",
            allowed_remedies=("refund",), maximum_extra_charge_cents=0),),
        partition="train", source_distribution_hash=DISTRIBUTION)
    scenario = CustomerScenario(customer_id=aliases["customer"], delegated_line_ids=(line_id,))
    certificate = certify_task(world, task, scenario)
    if certificate.status != "CERTIFIED":
        raise RuntimeError("native challenge task did not certify: " + ",".join(certificate.blockers))
    if verify_task_certificate(world, task, scenario, certificate)["verified"] is not True:
        raise RuntimeError("native challenge certificate did not replay")
    return task, scenario, certificate


def _compile_challenge_factory(tasks, verifier, proofs, adapter):
    def compile_one(world, aliases, task_ref, request):
        task, scenario, certificate = _compile_challenge(world, aliases, task_ref, request)
        native = NativeTask(
            world, task, _profile(aliases, "damaged_device", request), SmokeCustomer,
            EpisodeBudget(max_customer_turns=6, max_service_decisions=24,
                          max_service_tool_calls=20, max_model_calls=0))
        adapter.register_task(task_ref, native)
        try:
            proof = verifier.register(task_ref, native,
                                      "native-smoke/challenge/frozen-world-99",
                                      scenario, certificate)
        except Exception:
            del adapter.tasks[task_ref]
            raise
        tasks[task_ref] = native
        proofs.append(proof)
        return proof
    return compile_one


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=None,
                        help="new output directory (default: outputs/rsi-v02-usami-period-TIMESTAMP)")
    parser.add_argument("--image", default=IMAGE, help="locally cached pinned Docker image digest")
    args = parser.parse_args()
    output = args.output or "outputs/rsi-v02-usami-period-" + time.strftime("%Y%m%d-%H%M%S")
    run(output, image=args.image)


if __name__ == "__main__":
    main()
