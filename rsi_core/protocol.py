"""Public contracts; no environment or model-framework imports."""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from typing import Any, Dict, Optional, Protocol, Tuple


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class CandidateError(ValueError):
    """Candidate-owned syntax, capability, contract or execution failure."""


class InfrastructureError(RuntimeError):
    """Unusable execution/comparison; never a candidate's zero score."""


class BudgetExceeded(CandidateError):
    pass


class CapabilityViolation(CandidateError):
    """Known attempt to access capabilities outside this research mode."""


@dataclass(frozen=True)
class Limits:
    model_calls: int = 64
    model_tokens: int = 200000
    episodes: int = 128
    tool_steps: int = 2048
    research_steps: int = 512
    cpu_seconds: int = 120
    wall_seconds: int = 300
    memory_bytes: int = 134217728
    source_bytes: int = 65536
    response_bytes: int = 1048576

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in asdict(self).values()):
            raise ValueError("limits must be positive integers")


@dataclass(frozen=True)
class ModelSnapshot:
    model_id: str
    parameter_hash: str
    sampling: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.model_id or not self.parameter_hash:
            raise ValueError("models require an exact identity and parameter hash")
        blocked = {"model", "messages", "tools", "api_key", "authorization", "headers", "base_url"}
        if any(key.casefold() in blocked for key in self.sampling):
            raise ValueError("sampling cannot override model/capabilities or contain credentials")
        canonical(self.sampling)

    @property
    def ref(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class FrozenModels:
    behavior: ModelSnapshot
    evaluator: ModelSnapshot
    business: ModelSnapshot


@dataclass(frozen=True)
class Completion:
    output: Any
    prompt_tokens: int
    completion_tokens: int
    token_ids: Tuple[int, ...] = ()
    behavior_logprobs: Tuple[float, ...] = ()
    prompt_token_ids: Tuple[int, ...] = ()

    def __post_init__(self):
        canonical(self.output)
        if any(type(n) is not int or n < 0 for n in (self.prompt_tokens, self.completion_tokens)):
            raise InfrastructureError("model usage is missing or invalid")
        if len(self.token_ids) != len(self.behavior_logprobs):
            raise InfrastructureError("generated token/logprob alignment differs")
        if any(type(n) is not int or n < 0 for n in self.token_ids + self.prompt_token_ids):
            raise InfrastructureError("invalid model token IDs")
        if any(not math.isfinite(p) or p > 0 for p in self.behavior_logprobs):
            raise InfrastructureError("invalid behavior log probabilities")
        if self.token_ids and (len(self.token_ids) != self.completion_tokens
                               or len(self.prompt_token_ids) != self.prompt_tokens):
            raise InfrastructureError("token arrays do not match reported model usage")


class ResearchModel(Protocol):
    def complete(self, snapshot: ModelSnapshot, request: Dict[str, Any], *,
                 max_tokens: int, seed: int) -> Completion: ...


@dataclass(frozen=True)
class TaskResult:
    run_ref: str
    score: float
    status: str
    replay_verified: bool
    tool_steps: int = 0
    model_calls: int = 0
    model_tokens: int = 0
    feedback: Dict[str, Any] = field(default_factory=dict)
    forbidden_behavior: bool = False

    def __post_init__(self):
        if self.status not in {"VERIFIED", "UNKNOWN", "CANDIDATE_FAILED"}:
            raise ValueError("unknown native task status")
        if not math.isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("task score must be in [0,1]")
        if self.status == "VERIFIED" and not self.replay_verified:
            raise InfrastructureError("verified task result requires native Replay")
        if self.status != "VERIFIED" and self.score != 0:
            raise ValueError("unverified task cannot claim confirmed success")
        if any(type(v) is not int or v < 0 for v in (self.tool_steps, self.model_calls, self.model_tokens)):
            raise ValueError("invalid task consumption")
        canonical(self.feedback)


class EnvironmentAdapter(Protocol):
    domain_id: str

    def capabilities(self) -> Dict[str, Any]: ...

    def run_task(self, program, task_ref: str, models: FrozenModels, ledger,
                 worker, *, seed: int) -> TaskResult: ...

    def replay(self, run_ref: str) -> Dict[str, Any]: ...


@dataclass(frozen=True)
class AdaptationPackage:
    package_id: str
    domain_id: str
    family_id: str
    source_lineage: str
    partition: str
    purpose: str
    p0_ref: str
    support: Tuple[Dict[str, Any], ...]
    probe_refs: Tuple[str, ...]
    query_refs: Tuple[str, ...]
    capabilities: Dict[str, Any]
    seed: int = 0

    def __post_init__(self):
        if self.partition not in {"meta-train", "meta-validation", "meta-test"}:
            raise ValueError("invalid package partition")
        if self.purpose not in {"C_probe", "C_select", "C_reward", "audit"}:
            raise ValueError("invalid package purpose")
        if not all((self.package_id, self.domain_id, self.family_id, self.source_lineage, self.p0_ref)):
            raise ValueError("package provenance is required")
        if not self.query_refs or set(self.probe_refs) & set(self.query_refs):
            raise ValueError("private query must exist and be disjoint from public probes")
        if len(set(self.probe_refs)) != len(self.probe_refs) or len(set(self.query_refs)) != len(self.query_refs):
            raise ValueError("duplicate package task references")
        canonical(asdict(self))

    def public_view(self):
        # Explicit allowlist: purpose, query membership and source metadata do
        # not leak through dataclass serialization to a candidate process.
        return {"package_id": self.package_id, "domain_id": self.domain_id,
                "support": list(self.support), "probe_refs": list(self.probe_refs),
                "capabilities": self.capabilities}


def validate_partitions(groups):
    """Prove separation using families AND source lineages, not seed/ID changes."""
    seen_ids, seen_families, seen_lineages, seen_tasks = {}, {}, {}, {}
    for label, packages in groups.items():
        for package in packages:
            if (package.partition, package.purpose) != label:
                raise ValueError("package registered under a different partition/purpose")
            entries = ((seen_ids, (package.package_id,)),
                       (seen_families, ((package.domain_id, package.family_id),)),
                       (seen_lineages, ((package.domain_id, package.source_lineage),)),
                       (seen_tasks, tuple((package.domain_id, ref) for ref in package.probe_refs + package.query_refs)))
            for index, keys in entries:
                for key in keys:
                    if key in index and index[key] != label:
                        raise ValueError("package/family/lineage/task crosses an evaluation boundary")
                    index[key] = label
