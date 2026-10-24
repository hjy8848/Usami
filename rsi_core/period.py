"""One v0.2 cycle: Service roots, M self-edit roots, then one φ update hook."""
from collections import Counter
from dataclasses import asdict, replace

from .collection import (collect_self_edit_group, collect_service_improvement_group,
                         training_records)
from .programs import DesignerSnapshot, ServiceSnapshot
from .protocol import FrozenModels, ModelSnapshot, digest
from .training import group_advantages


def _public_service_research_history(groups):
    """Summarize only root-visible Service research feedback for M self-editing."""
    def summarize_feedback(feedback):
        outcomes = []
        for row in feedback.get("operations", []):
            result = row["result"]
            outcome = result.get("error_code") or ("SUCCESS" if result.get("success") is True else "FAILED")
            outcomes.append((row["operation"], outcome))
        counts = Counter(outcomes)
        return {"status": feedback.get("status", ""),
                "terminal_status": feedback.get("terminal_status", ""),
                "safety_violation": feedback.get("safety_violation", False),
                "operation_results": [{"operation": operation, "result": result, "count": count}
                                      for (operation, result), count in sorted(counts.items())]}

    history = []
    for group in groups:
        group_row = {"status": group.status, "roots": []}
        for root in group.roots:
            root_row = {"status": root.status, "error": root.error,
                        "challenge_attempts": [], "baseline_runs": [], "candidate_feedback": []}
            for wrapped in root.events:
                event = wrapped.get("event", wrapped)
                if event.get("kind") == "challenge_certification":
                    receipt = event["receipt"]
                    root_row["challenge_attempts"].append({
                        "proposal": event["proposal"], "status": receipt["status"],
                        "reason_code": receipt.get("reason_code", ""),
                    })
                elif event.get("kind") == "baseline_execution":
                    result = event["result"]
                    root_row["baseline_runs"].append({
                        "task_ref": event["task_ref"], "status": result["status"],
                        "score": result["score"], "replay_verified": result["replay_verified"],
                        "feedback": summarize_feedback(result["feedback"]),
                    })
                elif event.get("kind") == "observation":
                    value = event["value"]
                    if value.get("kind") == "STAGE":
                        root_row["candidate_feedback"].append({key: value[key] for key in (
                            "kind", "status", "reason", "candidate_ref") if key in value})
                    elif value.get("kind") == "PROBE":
                        result = value["result"]
                        summary = {key: result[key] for key in (
                            "score", "status", "usable", "unknown_fraction", "run_ref") if key in result}
                        if isinstance(result.get("feedback"), dict):
                            summary["feedback"] = summarize_feedback(result["feedback"])
                        root_row["candidate_feedback"].append({
                            "kind": "PROBE", "candidate_ref": value["candidate_ref"],
                            "probe_ref": value["probe_ref"], "result": summary})
            group_row["roots"].append(root_row)
        history.append(group_row)
    return history


def run_period(host, service_evaluator, adaptation_evaluator, designer, service,
               service_rounds, self_edit_context, *, fixed_self_editor=None,
               phi_update=None):
    """Execute a configured v0.2 period without starting training implicitly.

    ``service_rounds`` is the preregistered ordered list of K collection
    contexts. ``self_edit_context`` is created against the final accepted
    Service snapshot (or a callable that receives that snapshot). If
    ``phi_update`` is omitted, the period records training as not run and keeps
    φ unchanged. A supplied hook receives the archived collection groups and
    their separately grouped roots with within-group GRPO advantages, and is
    called exactly once after both root types. It must return the next
    immutable φ snapshot; it must not mutate the Host's frozen snapshots as a
    side effect.
    """
    if not isinstance(designer, DesignerSnapshot) or not isinstance(service, ServiceSnapshot):
        raise ValueError("v0.2 period requires atomic Designer and Service snapshots")
    rounds = tuple(service_rounds)
    if not rounds:
        raise ValueError("a period requires at least one preregistered Service round")
    if service_evaluator.host is not host or adaptation_evaluator.host is not host:
        raise ValueError("period evaluators must share the fixed Host")
    if designer.research_model.ref != host.models.behavior.ref:
        raise ValueError("Designer φ snapshot differs from the frozen behavior model")
    if service.business_model_ref != host.models.business.ref:
        raise ValueError("Service snapshot differs from fixed business model B")

    store, archive = host.store, host.archive
    store.save(designer)
    store.save(service)
    initial_models = asdict(host.models)
    current_designer, current_service = designer, service
    round_records = []
    service_groups = []

    for index, config in enumerate(rounds):
        if digest(asdict(host.models)) != digest(initial_models):
            raise ValueError("φ or evaluator/B snapshot changed before the period-end update")
        required = {"probe_tasks", "select_tasks", "reward_tasks", "seeds", "phase_budgets",
                    "certify_challenge"}
        if not required <= set(config):
            raise ValueError("Service round is missing a preregistered task set or runner")
        group = collect_service_improvement_group(
            host, service_evaluator, current_designer.research_program, current_service,
            config["probe_tasks"], config["select_tasks"], config["reward_tasks"],
            seeds=config["seeds"], phase_budgets=config["phase_budgets"],
            certify_challenge=config["certify_challenge"],
            public_view=config.get("public_view"), margin=config.get("margin", 0.0),
            max_regression=config.get("max_regression", 0.0))
        service_groups.append(group)
        previous = current_service
        if group.status == "USABLE" and group.selected_ref != current_service.ref:
            candidate = store.load(group.selected_ref)
            store.publish_service(candidate, parent_ref=current_service.ref)
            current_service = candidate
        round_records.append({"round": index, "parent_service_ref": previous.ref,
                              "group_ref": group.archive_ref, "group_status": group.status,
                              "candidate_selected_ref": group.selected_ref,
                              "service_after_ref": current_service.ref})
        if group.status != "USABLE":
            record = {"kind": "rsi_period_v0.2", "status": "ABORTED_SERVICE_GROUP",
                      "input_designer_ref": designer.ref, "input_service_ref": service.ref,
                      "frozen_models": initial_models, "service_rounds": round_records,
                      "self_edit_group_ref": "", "output_designer_ref": designer.ref,
                      "output_service_ref": current_service.ref, "training_status": "NOT_RUN",
                      "training_updates": 0, "training_hook_calls": 0,
                      "training_input_group_refs": [], "cost": host.ledger.snapshot()}
            return {**record, "archive_ref": archive.save(record)}

    if digest(asdict(host.models)) != digest(initial_models):
        raise ValueError("φ or evaluator/B snapshot changed before Designer self-edit")
    context = self_edit_context(current_service) if callable(self_edit_context) else self_edit_context
    required = {"probe_packages", "select_packages", "reward_packages", "seeds", "phase_budgets"}
    if not required <= set(context):
        raise ValueError("Designer self-edit context is missing a registered package group")
    packages = tuple(context["probe_packages"]) + tuple(context["select_packages"]) + tuple(context["reward_packages"])
    if any(package.p0_ref != current_service.ref for package in packages):
        raise ValueError("SELF_EDIT packages must all start from the same final S_ref")
    editor = fixed_self_editor or current_designer.research_program
    store.save(editor)
    public = dict(context.get("public_view", {}))
    if "service_start_ref" in public:
        raise ValueError("self-edit public view cannot override the frozen S_ref")
    public["service_start_ref"] = current_service.ref
    public["prior_service_research"] = _public_service_research_history(service_groups)
    self_group = collect_self_edit_group(
        host, adaptation_evaluator, editor, current_designer.research_program,
        context["probe_packages"], context["select_packages"], context["reward_packages"],
        seeds=context["seeds"], phase_budgets=context["phase_budgets"], public_view=public,
        margin=context.get("margin", 0.0), max_regression=context.get("max_regression", 0.0),
        sampling_ref=context.get("sampling_ref"))

    if self_group.status != "USABLE":
        record = {"kind": "rsi_period_v0.2", "status": "ABORTED_SELF_EDIT_GROUP",
                  "input_designer_ref": designer.ref, "input_service_ref": service.ref,
                  "frozen_models": initial_models, "service_rounds": round_records,
                  "self_edit_group_ref": self_group.archive_ref,
                  "output_designer_ref": designer.ref, "output_service_ref": current_service.ref,
                  "training_status": "NOT_RUN", "training_updates": 0,
                  "training_hook_calls": 0, "training_input_group_refs": [],
                  "cost": host.ledger.snapshot()}
        return {**record, "archive_ref": archive.save(record)}

    selected_program = store.load(self_group.selected_ref)
    if selected_program.kind != "M":
        raise ValueError("SELF_EDIT selection did not return a research program M")
    phi_next = current_designer.research_model
    training_status, training_count, training_hook_calls = "NOT_RUN", 0, 0
    training_input_refs = []
    groups = service_groups + [self_group]
    if phi_update is not None:
        training_groups = []
        for group in groups:
            records = training_records(host, group)
            advantages = group_advantages(records)
            training_groups.append({"group_ref": group.archive_ref,
                                   "context_ref": group.context_ref,
                                   "root_type": group.root_type,
                                   "records": records,
                                   "advantages": advantages})
            training_input_refs.append(group.archive_ref)
        if {row["root_type"] for row in training_groups} != {"r_service", "r_self"}:
            raise ValueError("period-end update requires both separately collected root types")
        if any((record.model_ref, record.evaluator_ref, record.business_ref) != (
                host.models.behavior.ref, host.models.evaluator.ref, host.models.business.ref)
               for group in training_groups for record in group["records"]):
            raise ValueError("period training records disagree on frozen model snapshots")
        training_hook_calls = 1
        try:
            result = phi_update(tuple(groups), tuple(training_groups))
            if not isinstance(result, ModelSnapshot):
                raise TypeError("φ update hook must return the new immutable ModelSnapshot")
            if digest(asdict(host.models)) != digest(initial_models):
                raise ValueError("φ update hook mutated frozen Host snapshots during the period")
            if (result.model_id != phi_next.model_id or result.sampling != phi_next.sampling):
                raise ValueError("period-end update may change φ weights only")
        except Exception as exc:
            # Trainer failure is an explicit terminal record. Restore the
            # Host's immutable snapshots so a partial hook cannot move φ/B.
            host.models = FrozenModels(**{
                key: ModelSnapshot(**value) for key, value in initial_models.items()})
            failed = {"kind": "rsi_period_v0.2", "status": "TRAINING_FAILED",
                      "input_designer_ref": designer.ref, "input_service_ref": service.ref,
                      "frozen_models": initial_models, "service_rounds": round_records,
                      "self_edit_group_ref": self_group.archive_ref,
                      "selected_m_ref": selected_program.ref,
                      "output_designer_ref": designer.ref,
                      "output_service_ref": current_service.ref,
                      "training_status": "FAILED", "training_updates": 0,
                      "training_hook_calls": 1,
                      "training_input_group_refs": training_input_refs,
                      "error": type(exc).__name__ + ": " + str(exc),
                      "root_group_refs": [group.archive_ref for group in groups],
                      "cost": host.ledger.snapshot()}
            ref = archive.save(failed)
            raise RuntimeError("period-end φ update failed; archived period " + ref) from exc
        phi_next = result
        training_status = "UPDATED" if phi_next.ref != current_designer.research_model.ref else "UNCHANGED"
        training_count = int(training_status == "UPDATED")

    designer_next = DesignerSnapshot(phi_next, selected_program, current_designer.ref)
    store.publish_designer(designer_next, parent_ref=current_designer.ref)
    host.models = replace(host.models, behavior=phi_next)
    record = {"kind": "rsi_period_v0.2",
              "status": "COMPLETED" if phi_update is not None else "READY_FOR_TRAINING",
              "input_designer_ref": designer.ref, "input_service_ref": service.ref,
              "frozen_models": initial_models, "service_rounds": round_records,
              "self_edit_group_ref": self_group.archive_ref,
              "selected_m_ref": selected_program.ref,
              "output_designer_ref": designer_next.ref,
              "output_service_ref": current_service.ref,
              "training_status": training_status, "training_updates": training_count,
              "training_hook_calls": training_hook_calls,
              "training_input_group_refs": training_input_refs,
              "root_group_refs": [group.archive_ref for group in groups],
              "cost": host.ledger.snapshot()}
    ref = archive.save(record)
    return {**record, "archive_ref": ref}
