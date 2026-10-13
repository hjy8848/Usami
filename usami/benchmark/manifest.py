"""Two versioned tracks with frozen instances, budgets, authority and source provenance."""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import Field, model_validator

from usami.audit.runner import CORE_FILES
from usami.evaluation.splits import business_fingerprint
from usami.benchmark.goals import CLASSES, GOAL_VERSION, GoalTask, generate_goal_tasks, validate_task
from usami.interaction.models import CUSTOMER_VERSION, INTERACTION_VERSION
from usami.randomness import StableRandom
from usami.service.models import ModelSettings, SERVICE_VERSION, TOOL_NAMES
from usami.world.generator import GeneratorConfig, generate_world
from usami.world.models import GENERATOR_VERSION, RULES_VERSION, Model, digest

PROTOCOL_VERSION = "usami-benchmark-0.1.0"
SCORE_VERSION = "usami-benchmark-score-0.1.0"
ROOT = Path(__file__).resolve().parents[2]


def runtime_hashes():
    paths = list(CORE_FILES) + ["usami/audit/signatures.py"]
    for package in ("service", "customer", "interaction", "benchmark"):
        paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "usami" / package).glob("*.py"))]
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(paths)}


def versions():
    return dict(protocol=PROTOCOL_VERSION, score=SCORE_VERSION, goal=GOAL_VERSION,
                generator=GENERATOR_VERSION, rules=RULES_VERSION, service=SERVICE_VERSION,
                interaction=INTERACTION_VERSION, customer=CUSTOMER_VERSION)


class Budget(Model):
    max_customer_turns: int = Field(default=1, strict=True, ge=1, le=100)
    max_customer_llm_calls: int = Field(default=0, strict=True, ge=0, le=100)
    max_service_llm_calls: int = Field(default=8, strict=True, ge=1, le=100)
    max_service_tool_calls: int = Field(default=16, strict=True, ge=1, le=1000)


class Instance(Model):
    instance_id: str
    seed: int = Field(strict=True)
    initial_state_hash: str
    customer_identity: str
    task: Optional[GoalTask] = None
    exploration_strategy: Optional[str] = None


class BenchmarkManifest(Model):
    version: str = PROTOCOL_VERSION
    suite_id: str
    release: str = "0.1.0"
    track: Literal["service_task", "customer_discovery"]
    split: Literal["train", "validation", "test"]
    visibility: Literal["public", "private", "demo"]
    generator: GeneratorConfig
    mode: Literal["reference", "sandbox"] = "reference"
    tools: List[str] = Field(default_factory=lambda: list(TOOL_NAMES))
    budget: Budget = Field(default_factory=Budget)
    service_model: ModelSettings
    customer_model: Optional[ModelSettings] = None
    trials: List[str] = Field(default_factory=lambda: ["r0"])
    instances: List[Instance] = Field(min_length=1)
    sampling: Dict = Field(default_factory=dict)
    versions: Dict[str, str]
    source_hashes: Dict[str, str]
    dataset_hash: str = ""
    manifest_hash: str = ""

    @model_validator(mode="after")
    def shape(self):
        if not self.suite_id or not self.release:
            raise ValueError("suite/release must be named")
        if self.split == "test" and self.visibility == "public":
            raise ValueError("test is private or explicitly demo, never a published blind test")
        if len(self.tools) != len(set(self.tools)) or set(self.tools) - set(TOOL_NAMES):
            raise ValueError("fixed tools must be distinct supported tools")
        if not self.trials or any(not trial for trial in self.trials) or len(self.trials) != len(set(self.trials)):
            raise ValueError("trials must be nonempty and distinct")
        if self.track == "service_task":
            if self.customer_model is not None or self.budget.max_customer_llm_calls != 0 or self.budget.max_customer_turns != 1:
                raise ValueError("Service tasks use one trusted goal input and zero Customer LLM calls")
            if any(i.task is None or i.exploration_strategy is not None for i in self.instances):
                raise ValueError("every Service task instance needs a goal, not a discovery strategy")
        elif self.customer_model is None or self.budget.max_customer_llm_calls < 1 or any(i.task is not None for i in self.instances):
            raise ValueError("Discovery requires Customer model/budget and no fixed task or attack script")
        return self

    def computed_dataset_hash(self):
        # Compare Service methods on the same task set while pinning each method per run.
        return digest(self.model_dump(mode="json", exclude={"dataset_hash", "manifest_hash", "service_model", "customer_model"}))

    def computed_hash(self):
        return digest(self.model_dump(mode="json", exclude={"manifest_hash"}))

    def seal(self):
        self.dataset_hash = self.computed_dataset_hash()
        self.manifest_hash = self.computed_hash()
        return self

    def save(self, path):
        validate_manifest(self)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")


def validate_manifest(manifest):
    # Revalidate shape even after mutable fields were modified.
    BenchmarkManifest.model_validate(manifest.model_dump())
    if (manifest.version != PROTOCOL_VERSION or manifest.versions != versions()
            or manifest.generator.rules.version != RULES_VERSION
            or manifest.source_hashes != runtime_hashes()
            or manifest.dataset_hash != manifest.computed_dataset_hash()
            or manifest.manifest_hash != manifest.computed_hash()):
        raise ValueError("manifest version, source provenance or hash mismatch")
    identifiers = set()
    for instance in manifest.instances:
        if instance.instance_id in identifiers:
            raise ValueError("duplicate benchmark instance")
        identifiers.add(instance.instance_id)
        world = generate_world(instance.seed, manifest.generator)
        expected_id = (instance.task.task_id if instance.task else "discovery_" + digest(
            {"state": world.state_hash, "identity": instance.customer_identity, "strategy": instance.exploration_strategy})[:24])
        if instance.initial_state_hash != world.state_hash or instance.customer_identity not in world.users or instance.instance_id != expected_id:
            raise ValueError("fixed world/identity/instance cannot be reproduced")
        if instance.task:
            if instance.task.identity != instance.customer_identity:
                raise ValueError("task cannot change the fixed Customer identity")
            validate_task(world, instance.task)
            if set(o.name for o in instance.task.capabilities) - set(manifest.tools):
                raise ValueError("task requires unavailable tools")
            if not any(len(w.operations) <= manifest.budget.max_service_tool_calls for w in instance.task.witnesses):
                raise ValueError("tool budget cannot cover any certified route")
    if manifest.track == "service_task" and "quotas" in manifest.sampling:
        actual = Counter(i.task.structural_class for i in manifest.instances)
        if dict(actual) != {k: v for k, v in manifest.sampling["quotas"].items() if v}:
            raise ValueError("structural sampling quotas do not match actual instances")


def load_manifest(path, expected_hash=None):
    manifest = BenchmarkManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))
    validate_manifest(manifest)
    if expected_hash is not None and manifest.manifest_hash != expected_hash:
        raise ValueError("manifest differs from external trusted commitment")
    return manifest


def create_service_manifest(seeds, quotas, service_model, *, generator=None, split="validation", visibility="public",
                            suite_id="usami-goals-v0.1", budget=None, sampling_seed=0, trials=None):
    seeds = list(seeds)
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("candidate world seeds must be nonempty and unique")
    if not quotas or set(quotas) - set(CLASSES) or any(type(n) is not int or n < 0 for n in quotas.values()) or not sum(quotas.values()):
        raise ValueError("quotas must name supported structural classes with nonnegative integer counts")
    cfg = generator or GeneratorConfig()
    pools = {key: [] for key in CLASSES}
    for seed in seeds:
        world = generate_world(seed, cfg)
        for task in generate_goal_tasks(world):
            pools[task.structural_class].append((seed, task))
    rng, chosen = StableRandom(sampling_seed), []
    for key, count in sorted(quotas.items()):
        candidates = sorted(pools[key], key=lambda item: item[1].task_id)
        rng.shuffle(candidates)
        if len(candidates) < count:
            raise ValueError(f"insufficient {key}: requested {count}, found {len(candidates)}; expand seed pool")
        for seed, task in candidates[:count]:
            chosen.append(Instance(instance_id=task.task_id, seed=seed, initial_state_hash=task.initial_state_hash,
                                   customer_identity=task.identity, task=task))
    manifest = BenchmarkManifest(suite_id=suite_id, track="service_task", split=split, visibility=visibility,
        generator=cfg, budget=budget or Budget(), service_model=service_model, trials=trials or ["r0"],
        instances=chosen, sampling={"candidate_seeds": seeds, "quotas": quotas, "sampling_seed": sampling_seed,
                                    "candidate_counts": {k: len(v) for k, v in pools.items()},
                                    "search": {"max_depth": 4, "max_nodes": 512, "max_solutions": 4}},
        versions=versions(), source_hashes=runtime_hashes()).seal()
    validate_manifest(manifest)
    return manifest


def create_discovery_manifest(seeds, identity, service_model, customer_model, *, generator=None, split="validation",
                              visibility="public", budget=None, mode="sandbox", trials=None, strategy=None):
    seeds = list(seeds)
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("discovery seeds must be nonempty and unique")
    cfg, instances = generator or GeneratorConfig(profile="test_composed"), []
    for seed in seeds:
        world = generate_world(seed, cfg)
        instances.append(Instance(instance_id="discovery_" + digest({"state": world.state_hash, "identity": identity, "strategy": strategy})[:24],
                                  seed=seed, initial_state_hash=world.state_hash, customer_identity=identity,
                                  exploration_strategy=strategy))
    manifest = BenchmarkManifest(suite_id="usami-discovery-v0.1", track="customer_discovery", split=split, visibility=visibility,
        generator=cfg, mode=mode, budget=budget or Budget(max_customer_turns=6, max_customer_llm_calls=8,
                                                         max_service_llm_calls=24, max_service_tool_calls=48),
        service_model=service_model, customer_model=customer_model, trials=trials or ["r0"], instances=instances,
        sampling={"world_seeds": seeds, "fixed_attack_script": False}, versions=versions(), source_hashes=runtime_hashes()).seal()
    validate_manifest(manifest)
    return manifest


def split_overlap(left, right, *, require_holdout=False):
    validate_manifest(left)
    validate_manifest(right)
    if left.track != "service_task" or right.track != "service_task":
        raise ValueError("goal structural overlap applies to Service Task manifests")
    a = {i.task.structure_signature for i in left.instances}
    b = {i.task.structure_signature for i in right.instances}
    sa = {i.task.semantic_signature for i in left.instances}
    sb = {i.task.semantic_signature for i in right.instances}
    worlds = {business_fingerprint(generate_world(i.seed, left.generator)) for i in left.instances} & {
        business_fingerprint(generate_world(i.seed, right.generator)) for i in right.instances}
    train_atoms = {o.name for i in left.instances for w in i.task.witnesses for o in w.operations}
    test_atoms = {o.name for i in right.instances for w in i.task.witnesses for o in w.operations}
    result = {"shared_world_instances": len(worlds), "common_structures": len(a & b), "common_semantics": len(sa & sb),
              "left_only_structures": sorted(a - b), "right_only_structures": sorted(b - a),
              "right_sample_structure_overlap": sum(i.task.structure_signature in a for i in right.instances) / len(right.instances),
              "right_only_atomic_operations": sorted(test_atoms - train_atoms)}
    if require_holdout and (worlds or a & b or test_atoms - train_atoms):
        raise ValueError("compositional split needs distinct worlds/structures and train-visible atomic operations")
    return result


def assert_comparable(left, right):
    validate_manifest(left)
    validate_manifest(right)
    if left.dataset_hash != right.dataset_hash:
        raise ValueError("methods must share frozen instances, budgets, tools, trials and protocol")
    if left.track == "customer_discovery" and left.service_model != right.service_model:
        raise ValueError("Customer discovery comparisons must fix the target Service model/settings")
