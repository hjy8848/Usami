"""Frozen-model recursion; fixed editor continues editing the current target."""
from dataclasses import asdict

from .evaluation import assert_context_partitions, select
from .protocol import CandidateError, InfrastructureError, digest


def recursive_run(host, evaluator, initial, probe_packages, select_packages, *,
                  generations=3, fixed_editor=False, margin=0.0, max_regression=0.0):
    if initial.kind != "M" or type(generations) is not int or generations < 1:
        raise ValueError("recursive run requires M and a fixed positive generation count")
    probe_packages, select_packages = tuple(probe_packages), tuple(select_packages)
    assert_context_partitions(probe_packages, select_packages, ())
    if not probe_packages or not select_packages:
        raise ValueError("recursion needs public research probes and independent selection packages")
    package_index = {p.package_id: p for p in probe_packages}
    if len(package_index) != len(probe_packages):
        raise ValueError("duplicate research probe handles")
    parent, history = initial, []
    frozen_models = digest(asdict(host.models))
    host.store.save(initial)
    for generation in range(generations):
        if digest(asdict(host.models)) != frozen_models:
            raise ValueError("model parameters/sampling changed during frozen recursion")
        editor = initial if fixed_editor else parent

        def probe(candidate, package_ref):
            result = evaluator.value(candidate, package_index[package_ref])
            return {"score": result.score, "baseline_score": result.baseline_score,
                    "status": result.status, "unknown_fraction": result.unknown_fraction,
                    "usable": result.usable}

        # History deliberately includes only permitted generation summaries,
        # never C_select task membership, query contents or private artifacts.
        public_history = [{"generation": row["generation"], "decision": row["selection"]["decision"],
                           "parent_ref": row["target_ref"], "selected_ref": row["selected_ref"]}
                          for row in history]
        run = host.run(editor, parent, "SELF_EDIT", {"history": public_history},
                        tuple(package_index), probe, scope="root", seed=generation)
        host.verify(run)
        if run.status == "FAILED":
            chosen = {"decision": "KEEP_PARENT", "selected_ref": parent.ref,
                      "reasons": ["CANDIDATE_FAILED", run.error]}
            candidate_ref = ""
        elif run.status == "NOOP":
            candidate_ref = parent.ref
            chosen = {"decision": "KEEP_PARENT", "selected_ref": parent.ref, "reasons": ["NOOP"]}
        else:
            candidate_ref = run.submitted_ref
            candidate = host.store.load(candidate_ref)
            comparison = evaluator.paired(parent, candidate, select_packages, purpose="C_select")
            chosen = select(parent, candidate, comparison, margin=margin, max_regression=max_regression)
        row = {"generation": generation, "editor_ref": editor.ref, "target_ref": parent.ref,
               "candidate_ref": candidate_ref, "selected_ref": chosen["selected_ref"],
               "selection": chosen, "root_trace_ref": run.archive_ref,
               "frozen_models": frozen_models, "phi_changed": False,
               "fixed_editor": fixed_editor, "cumulative_cost": host.ledger.snapshot()}
        row["archive_ref"] = host.archive.save(row)
        history.append(row)
        parent = host.store.load(chosen["selected_ref"])
    return {"initial_ref": initial.ref, "final_ref": parent.ref, "history": history,
            "generations": generations, "fixed_editor": fixed_editor,
            "interpretation": "program execution evidence; no H1/H2/H3 effect claim"}
