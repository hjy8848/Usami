"""Procedural, deterministic integration data. No online learning/effect claim.

This provider samples World *structure*, then delegates construction/proof to
Usami. Its challenge proposals and Service policy are explicitly test fixtures.
The production integration accepts the native OpenAIDesignerProvider instead.
"""
from pathlib import Path
import random

from rsi_core.archive import Archive
from rsi_core.budget import Ledger
from rsi_core.evaluation import Evaluator, ServiceEvaluator
from rsi_core.isolation import DockerWorker
from rsi_core.packages import (PackageProvider, PackageRegistration, ServiceTaskProvider,
                              ServiceTaskRegistration, TaskProof)
from rsi_core.programs import (DesignerSnapshot, ExperienceArtifact, ProgramArtifact,
                               ProgramStore, ServiceSnapshot)
from rsi_core.protocol import AdaptationPackage, Completion, FrozenModels, Limits, ModelSnapshot
from rsi_core.runtime import ResearchHost
from integrations.rsi_usami.adapter import UsamiAdapter
from integrations.rsi_usami.packages import NativePackageVerifier
from integrations.rsi_usami.open_world import OpenChallengeBridge, WorldPopulation
from usami_v2.runtime.agents import AgentCall
from usami_v2.runtime.customer import CustomerDecision, CustomerProfile
from usami_v2.runtime.runner import EpisodeBudget
from usami_v2.scenarios.designer import ScenarioDraft
from usami_v2.scenarios.distribution import BusinessSource, BusinessStratum, DistributionSpec
from usami_v2.scenarios.schema import Attribute, IntegerRange, LineVariable, OrderVariable, SKUVariable, WarehouseVariable
from usami_v2.scenarios.task_certification import CustomerScenario

IMAGE = "sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf"
ROOT = Path(__file__).resolve().parents[1]


def distribution(name="open-integration", split="train"):
    source = BusinessSource(source_id="synthetic-composition", kind="synthetic_assumption",
        reference="procedural ScenarioDraft integration fixture", version="1",
        supported_claims=("integration only",))
    return DistributionSpec(distribution_id=name, version=1, population_scope="synthetic commerce structures",
        sources=(source,), strata=(BusinessStratum(stratum_id="composed-commerce", weight=1,
        weight_basis_source_id=source.source_id, contexts=("multiple orders, variants and warehouses",)),), split=split)


class ProceduralWorldProvider:
    def submit(self, phase, messages, model):
        import json
        assert phase == "world"
        seed = json.loads(messages[-1]["content"])["pre_registered_slot"]["seed"]
        rng = random.Random(seed)
        fixed = lambda n: IntegerRange(low=n, high=n)
        customers = tuple("buyer" + str(i) for i in range(rng.randint(1, 3)))
        families = ("device", "cable", "lamp")
        skus = []
        for family in families:
            for variant in range(rng.randint(1, 3)):
                skus.append(SKUVariable(alias=family + str(variant), family=family,
                    price_cents=fixed(rng.randint(10, 100) * 100),
                    attributes=(Attribute(name="variant", value=str(variant)),)))
        orders = []
        for customer in customers:
            lines = [LineVariable(alias=customer + "_item" + str(i), original_sku=family + "0",
                quantity=fixed(1), paid_cents=fixed(next(s.price_cents.low for s in skus if s.alias == family + "0")),
                issue=("damaged", "missing_parts", "wrong_item")[i]) for i, family in enumerate(families[:rng.randint(2, 3)])]
            count = rng.randint(1, len(lines))
            for i in range(count):
                group = tuple(lines[i::count])
                orders.append(OrderVariable(alias=customer + "_purchase" + str(i), customer_alias=customer,
                    delivered_days_ago=fixed(rng.randint(0, 5)), lines=group))
        draft = ScenarioDraft(scenario_id="procedural-" + str(seed), customer_aliases=customers,
            skus=tuple(skus), warehouses=tuple(WarehouseVariable(alias="depot" + str(i),
                delivery_days=fixed(rng.randint(1, 3)), delivery_fee_cents=fixed(rng.randint(0, 5) * 100))
                for i in range(rng.randint(1, 3))), orders=tuple(orders), default_stock=fixed(rng.randint(3, 9)))
        return draft, AgentCall(role="designer", request={"messages": messages},
            response={"fixture": "procedural ScenarioDraft", "output": draft.model_dump(mode="json")})


def proposal(multi=False, name="challenge"):
    goals = [{"goal_id": "device-remedy", "line_alias": "item", "quantity": 1,
              "allowed_remedies": ["refund"]}]
    selectors = [{"alias": "item", "family": "device", "issue": "damaged"}]
    if multi:
        goals.append({"goal_id": "cable-remedy", "line_alias": "other", "quantity": 1,
            "allowed_remedies": ["reship"], "latest_arrival_within_days": 3})
        selectors.append({"alias": "other", "family": "cable", "issue": "missing_parts"})
    return {"task_id": name, "customer_alias": "shopper",
            "remedy_goals": goals, "hypothesis": "Test independent remedies across customer-owned items.",
            "line_selectors": selectors}


class AcceptingCustomer:
    """Deterministic consent fixture; authority is enforced by native runtime."""
    uses_model = False
    last_call = None

    def decide(self, prompt, profile):
        if prompt.offer:
            return CustomerDecision(message="I accept this quote.", accept_quote_id=prompt.offer.quote_id,
                                    accept_operation=prompt.offer.operation)
        return CustomerDecision(message="Thank you.", finish=True)


def customer_binding(world, task):
    lines = tuple(goal.line_id for goal in task.remedy_goals)
    profile = CustomerProfile(customer_id=task.customer_id, delegated_line_ids=lines,
        maximum_extra_charge_cents=100000000)
    scenario = CustomerScenario(customer_id=task.customer_id, delegated_line_ids=lines)
    return profile, scenario, AcceptingCustomer


class FixtureResearchModel:
    def __init__(self, policy_source):
        self.policy_source, self.proposals = policy_source, 0

    def complete(self, snapshot, request, *, max_tokens, seed):
        properties = set(request["response_schema"].get("properties", {}))
        if "line_selectors" in properties:
            self.proposals += 1
            output = proposal(self.proposals % 2 == 0, "proposal-" + str(self.proposals))
            for selector in output["line_selectors"]:
                selector["return_required"] = False
        elif {"policy_source", "experience"} <= properties:
            output = {"policy_source": self.policy_source,
                      "experience": {"fixture": "observed public training evidence", "proposal": self.proposals}}
        elif "sources" in properties:
            output = {"sources": []}
        else:
            raise ValueError("unexpected deterministic model schema: " + repr(sorted(properties)))
        return Completion(output, 1, 1)


def context(output):
    """CLI factory for deterministic end-to-end interface acceptance only."""
    output = Path(output)
    archive, store = Archive(output / "archive"), ProgramStore(output / "programs")
    limits = Limits(model_calls=128, model_tokens=1000000, episodes=128, tool_steps=10000,
                    research_steps=10000, cpu_seconds=10000, wall_seconds=7200)
    worker = DockerWorker(IMAGE, limits)
    fixture = ModelSnapshot("deterministic-open-interface-fixture", "scripted-v1")
    models = FrozenModels(fixture, fixture, fixture)
    policy_source = (ROOT / "fixtures/open_public_controller.py").read_text()
    host = ResearchHost(store, archive, worker, FixtureResearchModel(policy_source), models, Ledger(limits),
                        max_steps=24, max_output_tokens=4000)
    adapter = UsamiAdapter({}, output / "native-episodes")
    verifier = NativePackageVerifier({}, archive)
    episode_budget = EpisodeBudget(max_customer_turns=8, max_service_decisions=80,
                                   max_service_tool_calls=72, max_model_calls=0)
    service = ServiceSnapshot(fixture.ref, ProgramArtifact("P", policy_source), ExperienceArtifact())
    designer = DesignerSnapshot(fixture, ProgramArtifact("M", (ROOT / "seeds/M0.py").read_text()))
    population = WorldPopulation(output / "worlds", distribution(), ProceduralWorldProvider(), seed=84)
    direct, package_rows = [], []

    def independent_task(purpose, index):
        pool = WorldPopulation(output / ("independent-" + purpose), distribution("independent-" + purpose),
                               ProceduralWorldProvider(), seed=1000 + index)
        ref = pool.next_period(1)
        bridge = OpenChallengeBridge(pool, ref, adapter, verifier, customer_binding, episode_budget=episode_budget)
        receipt = bridge.certify(proposal(name=purpose))
        if receipt["status"] != "CERTIFIED":
            raise RuntimeError("independent fixture task did not certify")
        saved = archive.load(receipt["certificate_ref"])
        return TaskProof(receipt["task_ref"], saved["origin_ref"], receipt["certificate_ref"])

    for index, purpose in enumerate(("service_probe", "service_select", "service_reward")):
        proof = independent_task(purpose, index)
        direct.append(ServiceTaskRegistration(purpose, adapter.domain_id, purpose, purpose,
                                              "meta-train", purpose, (proof,), seed=10+index))
    provider = ServiceTaskProvider(direct, archive, verifier)
    sets = {purpose: provider.sets(purpose)[0] for purpose in ("service_probe", "service_select", "service_reward")}
    for index, purpose in enumerate(("C_probe", "C_select", "C_reward")):
        a = independent_task(purpose + "-support", 20+index)
        b = independent_task(purpose + "-query", 30+index)
        package = AdaptationPackage(purpose, adapter.domain_id, purpose, purpose, "meta-train", purpose,
            service.ref, (), (a.task_ref,), (b.task_ref,), {"task_interface": "native public tools"})
        package_rows.append(PackageRegistration(package, (), (a, b)))
    package_provider = PackageProvider(package_rows, archive, verifier)
    groups = package_provider.sample_training_context(27, counts={"C_probe": 1, "C_select": 1, "C_reward": 1})
    budgets = {phase: {"model_calls": 8, "model_tokens": 40000, "episodes": 4, "tool_steps": 200,
                       "research_steps": 300, "cpu_seconds": 600} for phase in ("root", "selection", "reward")}
    return {"population": population, "host": host, "service_evaluator": ServiceEvaluator(host, adapter, provider),
        "adaptation_evaluator": Evaluator(host, adapter), "designer": designer, "service": service,
        "service_rounds": ({"probe_tasks": sets["service_probe"], "select_tasks": sets["service_select"],
            "reward_tasks": sets["service_reward"], "seeds": (11, 22), "phase_budgets": budgets},),
        "self_edit_context": {"probe_packages": groups.probe, "select_packages": groups.selection,
            "reward_packages": groups.reward, "seeds": (33, 44), "phase_budgets": budgets,
            "sampling_ref": groups.archive_ref},
        "customer_binding": customer_binding, "verifier": verifier, "episode_budget": episode_budget}


def proposal_context(output):
    """Reuse frozen deterministic integration Worlds for a separate live Designer call."""
    output = Path(output)
    archive = Archive(output / "archive")
    return {"population": WorldPopulation(output / "worlds", distribution(), ProceduralWorldProvider(), seed=84),
            "service_evaluator": type("NativeContext", (), {"adapter": UsamiAdapter({}, output / "live-designer-native")})(),
            "verifier": NativePackageVerifier({}, archive), "customer_binding": customer_binding}
