"""Adapt/F, independent paired selection, and native UNKNOWN denominators."""
from dataclasses import asdict, dataclass
from statistics import mean
import math

from .protocol import InfrastructureError, canonical, digest, validate_partitions
from .programs import ServiceSnapshot
from .packages import ServiceTaskProvider, ServiceTaskSet


def _research_feedback(adapter, result):
    """Validate the Adapter's explicit candidate-visible feedback projection."""
    projector = getattr(adapter, "research_feedback", None)
    if not callable(projector):
        raise InfrastructureError("environment Adapter has no declared research feedback projection")
    projection = projector(result)
    if not isinstance(projection, dict) or not isinstance(projection.get("protocol"), str):
        raise InfrastructureError("Adapter research feedback must be a versioned object")
    declared = adapter.capabilities().get("feedback_protocol")
    if projection["protocol"] != declared:
        raise InfrastructureError("Adapter feedback projection differs from its declared protocol")
    if (projection.get("run_ref") != result.run_ref
            or projection.get("status") != result.status
            or projection.get("score") != result.score):
        raise InfrastructureError("Adapter feedback projection is not bound to its task result")
    try:
        canonical(projection)
    except (TypeError, ValueError) as exc:
        raise InfrastructureError("Adapter feedback projection is not canonical JSON") from exc
    return projection


@dataclass(frozen=True)
class AdaptationResult:
    researcher_ref: str
    p0_ref: str
    selected_p_ref: str
    package_id: str
    pair_binding: str
    status: str
    score: float
    baseline_score: float
    unknown_fraction: float
    usable: bool
    forbidden_behavior: bool
    research_run_ref: str
    query_run_refs: tuple
    archive_ref: str


@dataclass(frozen=True)
class PairedEvaluation:
    parent_ref: str
    candidate_ref: str
    purpose: str
    pairs: tuple
    mean_delta: float
    usable: bool
    safe: bool
    archive_ref: str


@dataclass(frozen=True)
class ServicePairedEvaluation:
    parent_ref: str
    candidate_ref: str
    purpose: str
    task_set_ref: str
    pairs: tuple
    mean_delta: float
    unknown_fraction: float
    unknown_limit: float
    usable: bool
    safe: bool
    archive_ref: str


class Evaluator:
    def __init__(self, host, adapter, *, unknown_limit=0.0):
        if not 0 <= unknown_limit <= 1:
            raise ValueError("unknown validity limit must be in [0,1]")
        self.host, self.adapter = host, adapter
        self.unknown_limit = unknown_limit

    def _task(self, program, task_ref, seed):
        self.host.ledger.charge("environment", episodes=1)
        result = self.adapter.run_task(program, task_ref, self.host.models,
                                       self.host.ledger, self.host.worker, seed=seed)
        if not self.adapter.replay(result.run_ref).get("verified"):
            raise InfrastructureError("native task replay failed")
        return result

    def value(self, researcher, package):
        if package.domain_id != self.adapter.domain_id:
            raise ValueError("package belongs to another environment")
        parent = self.host.store.load(package.p0_ref)
        if parent.kind not in {"P", "SERVICE_BUNDLE"}:
            raise ValueError("adaptation must restart at a task program")
        if isinstance(parent, ServiceSnapshot):
            if parent.business_model_ref != self.host.models.business.ref:
                raise ValueError("adaptation package Service start changes fixed business model B")
            execution_start = parent.evaluation_copy()
            mode = "EVALUATE_ADAPT"
        else:
            execution_start = parent
            mode = "ADAPT_TASK"

        unsafe_probes = set()

        def probe(candidate, task_ref):
            result = self._task(candidate, task_ref, package.seed)
            if result.forbidden_behavior:
                unsafe_probes.add(candidate.ref)
            # The Adapter owns this allowlisted projection, not the candidate.
            return {"score": result.score, "status": result.status,
                    "feedback": _research_feedback(self.adapter, result),
                    "run_ref": result.run_ref}

        public = package.public_view()
        public["environment_capabilities"] = public.pop("capabilities")
        public.pop("probe_refs")
        public["service_start_ref"] = parent.ref
        run = self.host.run(researcher, execution_start, mode, public,
                            package.probe_refs, probe, scope="evaluator", seed=package.seed)
        self.host.verify(run)
        binding = digest({"package": asdict(package), "models": asdict(self.host.models),
                          "limits": asdict(self.host.ledger.limits), "p0": parent.ref})
        baseline = tuple(self._task(parent, ref, package.seed + i) for i, ref in enumerate(package.query_refs))
        if run.status == "FAILED":
            selected, proposed = "", ()
            score, status, unknown, safe = 0.0, "ADAPTATION_FAILED", 0.0, not run.forbidden_behavior
        else:
            selected = run.submitted_ref
            proposed = baseline if selected == execution_start.ref else tuple(
                self._task(self.host.store.load(selected), ref, package.seed + i)
                for i, ref in enumerate(package.query_refs))
            if any(r.status == "UNKNOWN" for r in proposed):
                unknown = sum(r.status == "UNKNOWN" for r in proposed) / len(proposed)
            else:
                unknown = 0.0
            # J is confirmed success in [0,1]. Native UNKNOWN remains visible
            # in the denominator and is not promoted to a success.
            score = mean(float(r.status == "VERIFIED" and r.score == 1.0) for r in proposed)
            status = "NOOP" if selected == execution_start.ref else "EVALUATED"
            safe = not any(r.forbidden_behavior for r in proposed) and selected not in unsafe_probes
        baseline_unknown = sum(r.status == "UNKNOWN" for r in baseline) / len(baseline)
        baseline_score = mean(float(r.status == "VERIFIED" and r.score == 1.0) for r in baseline)
        usable = max(unknown, baseline_unknown) <= self.unknown_limit
        data = {"researcher_ref": researcher.ref, "p0_ref": parent.ref, "selected_p_ref": selected,
                "package_id": package.package_id, "pair_binding": binding, "status": status,
                "score": score, "baseline_score": baseline_score,
                "unknown_fraction": max(unknown, baseline_unknown), "usable": usable,
                "forbidden_behavior": not safe, "research_run_ref": run.archive_ref,
                "query_run_refs": [r.run_ref for r in baseline + proposed]}
        ref = self.host.archive.save(data)
        return AdaptationResult(**{**data, "query_run_refs": tuple(data["query_run_refs"]), "archive_ref": ref})

    def paired(self, parent, candidate, packages, *, purpose):
        packages = tuple(packages)
        if not packages or any(p.purpose != purpose for p in packages):
            raise ValueError("paired evaluation requires the registered package purpose")
        pairs = []
        for package in packages:
            old = self.value(parent, package)
            new = old if candidate.ref == parent.ref else self.value(candidate, package)
            if old.pair_binding != new.pair_binding:
                raise ValueError("paired P0/models/tasks/budgets differ")
            pairs.append((old, new))
        usable = all(a.usable and b.usable for a, b in pairs)
        safe = not any(b.forbidden_behavior for _, b in pairs)
        data = {"parent_ref": parent.ref, "candidate_ref": candidate.ref, "purpose": purpose,
                "pairs": [[asdict(a), asdict(b)] for a, b in pairs],
                "mean_delta": mean(b.score - a.score for a, b in pairs),
                "usable": usable, "safe": safe}
        ref = self.host.archive.save(data)
        return PairedEvaluation(parent.ref, candidate.ref, purpose, tuple(pairs),
                                data["mean_delta"], usable, safe, ref)


class ServiceEvaluator:
    """Directly compare complete (P,K) snapshots on certified Service tasks."""

    def __init__(self, host, adapter, task_provider: ServiceTaskProvider, *, unknown_limit=0.0):
        if not 0 <= unknown_limit <= 1:
            raise ValueError("unknown validity limit must be in [0,1]")
        self.host, self.adapter, self.task_provider = host, adapter, task_provider
        self.unknown_limit = unknown_limit

    def run_task(self, service, task_ref, seed, *, task_set=None):
        if not isinstance(service, ServiceSnapshot) or service.evaluation_only:
            raise ValueError("direct Service scoring requires a main-chain Service snapshot")
        if service.business_model_ref != self.host.models.business.ref:
            raise ValueError("Service comparison changed the fixed business model B")
        if task_set is not None:
            self.task_provider.verify_task_set(task_set)
            if task_ref not in task_set.task_refs:
                raise ValueError("task is outside the certified direct Service task set")
        self.host.ledger.charge("environment", episodes=1)
        result = self.adapter.run_task(service, task_ref, self.host.models,
                                       self.host.ledger, self.host.worker, seed=seed)
        replay = self.adapter.replay(result.run_ref)
        if replay.get("verified") is not True or result.replay_verified is not True:
            raise InfrastructureError("direct Service task Replay failed")
        return result

    def research_feedback(self, result):
        """Request the Adapter's declared public projection of a baseline.

        Raw task results remain in trusted environment artifacts. M receives
        only a versioned projection whose top-level outcome fields are bound
        back to that result.
        """
        return _research_feedback(self.adapter, result)

    def paired(self, parent, candidate, task_set: ServiceTaskSet, *, purpose):
        if purpose not in {"service_select", "service_reward", "service_probe"}:
            raise ValueError("direct Service comparison requires a registered Service purpose")
        if task_set.purpose != purpose:
            raise ValueError("direct Service task set has a different purpose")
        if task_set.domain_id != self.adapter.domain_id:
            raise ValueError("direct Service task set belongs to another environment")
        self.task_provider.verify_task_set(task_set)
        if task_set.partition != "meta-train" and purpose != "service_probe":
            raise ValueError("selection and reward comparisons require meta-train tasks")
        pairs = []
        for index, task_ref in enumerate(task_set.task_refs):
            seed = task_set.seed + index
            old = self.run_task(parent, task_ref, seed, task_set=task_set)
            new = self.run_task(candidate, task_ref, seed, task_set=task_set)
            pairs.append({"task_ref": task_ref, "seed": seed,
                          "parent_result": asdict(old), "candidate_result": asdict(new)})
        unknown_count = sum(row[side]["status"] == "UNKNOWN" for row in pairs
                            for side in ("parent_result", "candidate_result"))
        unknown_fraction = unknown_count / (2 * len(pairs))
        score = lambda result: float(result["status"] == "VERIFIED" and result["score"] == 1.0)
        delta = sum(score(row["candidate_result"]) - score(row["parent_result"])
                    for row in pairs) / len(pairs)
        usable = unknown_fraction <= self.unknown_limit
        safe = not any(row["candidate_result"]["forbidden_behavior"] for row in pairs)
        data = {"kind": "service_paired_evaluation_v0.2",
                "parent_ref": parent.ref, "candidate_ref": candidate.ref,
                "purpose": purpose, "task_set": asdict(task_set), "task_set_ref": task_set.ref,
                "models": asdict(self.host.models), "limits": asdict(self.host.ledger.limits),
                "pairs": pairs, "mean_delta": delta, "unknown_fraction": unknown_fraction,
                "unknown_limit": self.unknown_limit, "usable": usable, "safe": safe}
        ref = self.host.archive.save(data)
        return ServicePairedEvaluation(parent.ref, candidate.ref, purpose, task_set.ref,
                                       tuple(pairs), delta, unknown_fraction, self.unknown_limit,
                                       usable, safe, ref)


def select(parent, candidate, comparison, *, margin=0.0, max_regression=0.0):
    if any(not math.isfinite(v) or v < 0 for v in (margin, max_regression)):
        raise ValueError("selection tolerances must be preregistered nonnegative values")
    if (comparison.parent_ref, comparison.candidate_ref, comparison.purpose) != (parent.ref, candidate.ref, "C_select"):
        raise ValueError("selection cannot consume reward/audit comparisons")
    if any(a.pair_binding != b.pair_binding for a, b in comparison.pairs):
        raise ValueError("paired evaluation binding differs")
    if not comparison.pairs or comparison.mean_delta != mean(b.score - a.score for a, b in comparison.pairs):
        raise ValueError("paired scores disagree with the comparison summary")
    if comparison.usable != all(a.usable and b.usable for a, b in comparison.pairs):
        raise ValueError("paired validity disagrees with the comparison summary")
    if comparison.safe != (not any(b.forbidden_behavior for _, b in comparison.pairs)):
        raise ValueError("paired safety disagrees with the comparison summary")
    reasons = []
    if not comparison.usable:
        reasons.append("UNRESOLVED")
    if not comparison.safe:
        reasons.append("CANDIDATE_FORBIDDEN_BEHAVIOR")
    if comparison.mean_delta <= margin:
        reasons.append("NO_PAIRED_GAIN")
    if any(b.score < a.score - max_regression for a, b in comparison.pairs):
        reasons.append("PACKAGE_REGRESSION")
    accepted = not reasons
    return {"selected_ref": candidate.ref if accepted else parent.ref,
            "decision": "ACCEPT" if accepted else "KEEP_PARENT", "reasons": reasons,
            "margin": margin, "max_regression": max_regression,
            "comparison_ref": comparison.archive_ref,
            "interpretation": "engineering selection, not a significance or monotonicity guarantee"}


def select_service(parent, candidate, comparison, *, margin=0.0, max_regression=0.0):
    if any(not math.isfinite(v) or v < 0 for v in (margin, max_regression)):
        raise ValueError("Service selection tolerances must be finite and nonnegative")
    if (comparison.parent_ref, comparison.candidate_ref, comparison.purpose) != (
            parent.ref, candidate.ref, "service_select"):
        raise ValueError("Service selection must use the registered service_select comparison")
    if not comparison.pairs:
        raise ValueError("Service selection requires paired task outcomes")
    expected_unknown = sum(row[side]["status"] == "UNKNOWN" for row in comparison.pairs
                           for side in ("parent_result", "candidate_result")) / (2 * len(comparison.pairs))
    expected_delta = sum(float(row["candidate_result"]["status"] == "VERIFIED"
                               and row["candidate_result"]["score"] == 1.0)
                         - float(row["parent_result"]["status"] == "VERIFIED"
                                 and row["parent_result"]["score"] == 1.0)
                         for row in comparison.pairs) / len(comparison.pairs)
    expected_safe = not any(row["candidate_result"]["forbidden_behavior"]
                            for row in comparison.pairs)
    if (comparison.mean_delta != expected_delta or comparison.unknown_fraction != expected_unknown
            or comparison.safe != expected_safe
            or comparison.usable != (expected_unknown <= comparison.unknown_limit)):
        raise ValueError("Service comparison summary differs from its task outcomes")
    reasons = []
    if not comparison.usable:
        reasons.append("UNRESOLVED")
    if not comparison.safe:
        reasons.append("CANDIDATE_FORBIDDEN_BEHAVIOR")
    if comparison.mean_delta <= margin:
        reasons.append("NO_PAIRED_GAIN")
    for row in comparison.pairs:
        old = float(row["parent_result"]["status"] == "VERIFIED" and row["parent_result"]["score"] == 1.0)
        new = float(row["candidate_result"]["status"] == "VERIFIED" and row["candidate_result"]["score"] == 1.0)
        if new < old - max_regression:
            reasons.append("TASK_REGRESSION")
            break
    accepted = not reasons
    return {"selected_ref": candidate.ref if accepted else parent.ref,
            "decision": "ACCEPT" if accepted else "KEEP_PARENT", "reasons": reasons,
            "margin": margin, "max_regression": max_regression,
            "comparison_ref": comparison.archive_ref,
            "interpretation": "fixed Service selector; not evidence of statistical significance"}


def assert_context_partitions(probe, selection, reward):
    validate_partitions({("meta-train", "C_probe"): tuple(probe),
                         ("meta-train", "C_select"): tuple(selection),
                         ("meta-train", "C_reward"): tuple(reward)})
