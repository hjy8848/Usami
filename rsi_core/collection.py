"""Frozen SELF_EDIT sampling groups with private, independently sourced rewards."""
from dataclasses import asdict, dataclass
import math

from .evaluation import assert_context_partitions, select
from .protocol import BudgetExceeded, InfrastructureError, digest


@dataclass(frozen=True)
class CollectedGroup:
    context_ref: str
    archive_ref: str
    status: str
    selected_ref: str
    roots: tuple
    reward_refs: tuple


def collect_self_edit_group(host, evaluator, editor, target, probe_packages,
                            select_packages, reward_packages, *, seeds,
                            phase_budgets, public_view=None, margin=0.0,
                            max_regression=0.0, sampling_ref=None):
    """Collect all roots before selecting or revealing any terminal reward.

    Each root has independent state and a separate, identical allocation.
    Candidate deduplication affects external evaluation, never root retention.
    This produces executed reward receipts, not a parameter update.
    """
    seeds = tuple(seeds)
    if any(not math.isfinite(v) or v < 0 for v in (margin, max_regression)):
        raise ValueError("selection tolerances must be finite and nonnegative before sampling")
    if len(seeds) < 2 or len(set(seeds)) != len(seeds) or any(type(s) is not int for s in seeds):
        raise ValueError("a sampling group needs distinct integer root seeds")
    if editor.kind != "M" or target.kind != "M" or evaluator.host is not host:
        raise ValueError("SELF_EDIT collection needs the same trusted Host and M programs")
    if set(phase_budgets) != {"root", "selection", "reward"}:
        raise ValueError("register all three phase budgets before sampling")
    probe_packages, select_packages, reward_packages = (
        tuple(probe_packages), tuple(select_packages), tuple(reward_packages))
    if not all((probe_packages, select_packages, reward_packages)):
        raise ValueError("SELF_EDIT groups require probe, selection and reward packages")
    assert_context_partitions(probe_packages, select_packages, reward_packages)
    if sampling_ref is not None:
        sampled = host.archive.load(sampling_ref)
        if sampled["kind"] != "sampled_training_packages_v1":
            raise ValueError("sampling provenance is not a registered training context")
        for purpose, packages in (("C_probe", probe_packages), ("C_select", select_packages),
                                  ("C_reward", reward_packages)):
            draw = host.archive.load(sampled["draw_refs"][purpose])
            if (draw["manifest_ref"] != sampled["manifest_ref"] or draw["partition"] != "meta-train"
                    or draw["purpose"] != purpose or draw["package_ids"] != [p.package_id for p in packages]):
                raise ValueError("executed packages differ from their registered draw")
        bank = host.archive.load(sampled["manifest_ref"])
        registered = {row["package"]["package_id"]: row["package"] for row in bank["registrations"]}
        for p in probe_packages + select_packages + reward_packages:
            if digest(asdict(p)) != digest(registered[p.package_id]):
                raise ValueError("executed package contents differ from the frozen bank")
    package_index = {p.package_id: p for p in probe_packages}
    if len(package_index) != len(probe_packages):
        raise ValueError("duplicate public experiment handles")
    public = {} if public_view is None else public_view
    models = asdict(host.models)
    context = {"kind": "self_edit_sampling_context_v1", "editor_ref": editor.ref,
               "target_ref": target.ref, "models": models, "seeds": seeds,
               "limits": asdict(host.ledger.limits), "phase_budgets": phase_budgets,
               "public_view": public,
               "sampling_ref": sampling_ref,
               "packages": {"C_probe": [asdict(p) for p in probe_packages],
                            "C_select": [asdict(p) for p in select_packages],
                            "C_reward": [asdict(p) for p in reward_packages]},
               "margin": margin, "max_regression": max_regression}
    context_ref = host.archive.save(context)
    frozen = digest(models)
    roots, receipts, selections, rewards = [], [], {}, {}
    selected_ref, best_delta, error = target.ref, 0.0, ""
    usable = True

    def check_models():
        if digest(asdict(host.models)) != frozen:
            raise InfrastructureError("frozen model snapshots changed within a sampling group")

    def probe(candidate, package_ref):
        value = evaluator.value(candidate, package_index[package_ref])
        # Neither root nor nested M receives query membership or answers.
        return {"score": value.score, "baseline_score": value.baseline_score,
                "status": value.status, "usable": value.usable,
                "unknown_fraction": value.unknown_fraction}

    allocations = {phase + ":" + str(i): maximum
                   for phase, maximum in phase_budgets.items() for i in range(len(seeds))}
    try:
        with host.ledger.reserve_group(allocations) as reserved:
            for i, seed in enumerate(seeds):
                check_models()
                with reserved["root:" + str(i)].spend():
                    run = host.run(editor, target, "SELF_EDIT", public,
                                   tuple(package_index), probe, scope="root", seed=seed)
                host.verify(run)
                roots.append(run)
                check_models()

            # Selection never reads reward scores. Include the parent by
            # retaining it on ties, failed roots and rejected comparisons.
            for i, run in enumerate(roots):
                if run.status != "SUBMITTED" or run.submitted_ref in selections:
                    continue
                check_models()
                candidate = host.store.load(run.submitted_ref)
                with reserved["selection:" + str(i)].spend():
                    comparison = evaluator.paired(target, candidate, select_packages, purpose="C_select")
                decision = select(target, candidate, comparison, margin=margin,
                                  max_regression=max_regression)
                selections[candidate.ref] = decision
                if decision["decision"] == "ACCEPT" and comparison.mean_delta > best_delta:
                    selected_ref, best_delta = candidate.ref, comparison.mean_delta
                check_models()

            for i, run in enumerate(roots):
                check_models()
                comparison_ref = ""
                if run.status == "FAILED":
                    value, outcome = -1.0, "ROOT_FAILED"
                elif run.status == "NOOP":
                    value, outcome = 0.0, "NOOP"
                else:
                    if run.submitted_ref not in rewards:
                        candidate = host.store.load(run.submitted_ref)
                        with reserved["reward:" + str(i)].spend():
                            rewards[candidate.ref] = evaluator.paired(
                                target, candidate, reward_packages, purpose="C_reward")
                    comparison = rewards[run.submitted_ref]
                    comparison_ref = comparison.archive_ref
                    usable = usable and comparison.usable
                    value = comparison.mean_delta if comparison.safe else -1.0
                    outcome = "PAIRED_REWARD" if comparison.safe else "FORBIDDEN_CANDIDATE"
                receipts.append({"kind": "root_reward_v1", "context_ref": context_ref,
                                 "root_trace_ref": run.archive_ref, "models": models,
                                 "comparison_ref": comparison_ref, "reward": value,
                                 "outcome": outcome})
                check_models()
    except (InfrastructureError, BudgetExceeded) as exc:
        # An API/verifier failure invalidates the entire on-policy group.
        # Completed roots and comparisons remain in the audit record.
        usable, error = False, str(exc)

    # No partial group can be exported, even if some roots already have scores.
    reward_refs = tuple(host.archive.save(row) for row in receipts) if usable else ()
    record = {"kind": "self_edit_group_v1", "context_ref": context_ref,
              "status": "USABLE" if usable else "UNUSABLE",
              "root_refs": [r.archive_ref for r in roots], "reward_refs": reward_refs,
              "selected_ref": selected_ref if usable else target.ref, "selections": selections,
              "reward_comparisons": {ref: r.archive_ref for ref, r in rewards.items()},
              "error": error, "cost": host.ledger.snapshot(),
              "training_updates": 0}
    ref = host.archive.save(record)
    return CollectedGroup(context_ref, ref, record["status"], record["selected_ref"],
                          tuple(roots), reward_refs)


def collect_sampled_self_edit_group(host, evaluator, editor, target, provider, *,
                                    package_seed, package_counts, **options):
    """Sample private packages through the Host registry and archive the link."""
    sampled = provider.sample_training_context(package_seed, counts=package_counts)
    return collect_self_edit_group(host, evaluator, editor, target, sampled.probe,
                                   sampled.selection, sampled.reward,
                                   sampling_ref=sampled.archive_ref, **options)


def training_records(host, group):
    """Export every sampled root, independent of external selection outcome."""
    from .training import root_training_record

    saved = host.archive.load(group.archive_ref)
    if saved["status"] != "USABLE" or saved["context_ref"] != group.context_ref:
        raise ValueError("unusable or mismatched group cannot enter training")
    if saved["root_refs"] != [r.archive_ref for r in group.roots] or list(group.reward_refs) != saved["reward_refs"]:
        raise ValueError("sampling group roots/rewards differ from the archived group")
    if len(group.roots) != len(group.reward_refs):
        raise ValueError("incomplete group cannot enter training")
    return tuple(root_training_record(host, run, host.archive.load(ref)["reward"], ref,
                                     group.context_ref)
                 for run, ref in zip(group.roots, group.reward_refs))
