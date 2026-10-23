"""Adapt/F, independent paired selection, and native UNKNOWN denominators."""
from dataclasses import asdict, dataclass
from statistics import mean
import math

from .protocol import CandidateError, InfrastructureError, digest, validate_partitions


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
        if parent.kind != "P":
            raise ValueError("adaptation must restart at a task program")

        unsafe_probes = set()

        def probe(candidate, task_ref):
            result = self._task(candidate, task_ref, package.seed)
            if result.forbidden_behavior:
                unsafe_probes.add(candidate.ref)
            # The Adapter owns this allowlisted projection, not the candidate.
            return {"score": result.score, "status": result.status,
                    "feedback": result.feedback, "run_ref": result.run_ref}

        public = package.public_view()
        public["environment_capabilities"] = public.pop("capabilities")
        public.pop("probe_refs")
        run = self.host.run(researcher, parent, "ADAPT_TASK", public,
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
            proposed = baseline if selected == parent.ref else tuple(
                self._task(self.host.store.load(selected), ref, package.seed + i)
                for i, ref in enumerate(package.query_refs))
            score = mean(r.score for r in proposed)
            status = "NOOP" if selected == parent.ref else "EVALUATED"
            unknown = sum(r.status == "UNKNOWN" for r in proposed) / len(proposed)
            safe = not any(r.forbidden_behavior for r in proposed) and selected not in unsafe_probes
        baseline_unknown = sum(r.status == "UNKNOWN" for r in baseline) / len(baseline)
        usable = max(unknown, baseline_unknown) <= self.unknown_limit
        data = {"researcher_ref": researcher.ref, "p0_ref": parent.ref, "selected_p_ref": selected,
                "package_id": package.package_id, "pair_binding": binding, "status": status,
                "score": score, "baseline_score": mean(r.score for r in baseline),
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


def assert_context_partitions(probe, selection, reward):
    validate_partitions({("meta-train", "C_probe"): tuple(probe),
                         ("meta-train", "C_select"): tuple(selection),
                         ("meta-train", "C_reward"): tuple(reward)})
