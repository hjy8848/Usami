"""State completion, communication and full correctness are separate results."""
from typing import Literal, Optional, Tuple

from usami_v2.contracts import Sealed
from .communication import CommunicationResult
from usami_harness.models import digest


class GoalResult(Sealed):
    goal_id: str
    status: Literal["PASS", "FAIL", "UNRESOLVED", "NOT_APPLICABLE"]
    evidence_refs: Tuple[str, ...]


class Outcome(Sealed):
    protocol: Literal["commerce-outcome-v1"] = "commerce-outcome-v1"
    state_goals: Tuple[GoalResult, ...]
    compliance: Tuple[GoalResult, ...]
    communication_hash: str
    final_goal_reached: Optional[bool]
    state_goal_applicability: Literal["APPLICABLE", "NOT_APPLICABLE"]
    strict_task_success: Optional[bool]
    evaluation_status: Literal["VERIFIED", "UNRESOLVED", "INVALID_EVIDENCE"]
    valid_end: bool


def evaluate_execution_compliance(tool_executions):
    """Score Service operation decisions separately from final state goals.

    A correctly blocked invalid attempt is not a successful business
    violation, but it is still an incorrect Service action for strict task
    success. Oracle uncertainty remains unresolved rather than being treated
    as a pass.
    """
    rows, invalid_decisions, unresolved = [], [], False
    invalid_classes = {"successful_business_violation", "rejected_invalid_attempt",
                       "false_rejection", "authorization_only"}
    for execution in tool_executions:
        oracle = execution.oracle if hasattr(execution, "oracle") else execution.get("oracle", {})
        operations = oracle.get("operations", ()) if isinstance(oracle, dict) else ()
        if not operations or oracle.get("trace_valid") is not True:
            unresolved = True
        for operation in operations:
            classification = operation.get("classification")
            reference_allowed = operation.get("reference_allowed")
            if classification in invalid_classes or operation.get("operation_correct") is False or operation.get("violations"):
                invalid_decisions.append(digest(operation))
            elif classification == "unscored" or operation.get("operation_correct") is None:
                unresolved = True
            elif classification != "legal_execution":
                unresolved = True
            if reference_allowed is None:
                unresolved = True
        record_hash = getattr(execution, "record_hash", None)
        rows.append(record_hash or digest(execution))
    status = "FAIL" if invalid_decisions else "UNRESOLVED" if unresolved else "PASS"
    evidence = tuple(rows + invalid_decisions)
    return GoalResult(goal_id="service_operation_compliance", status=status, evidence_refs=evidence)


def evaluate_outcome(state_goals, compliance, communication: CommunicationResult, *,
                     replay_verified: bool, valid_end: bool):
    state_goals = tuple(row.checked() for row in state_goals)
    compliance = tuple(row.checked() for row in compliance)
    communication = communication.checked()
    applicable = [row.status for row in state_goals if row.status != "NOT_APPLICABLE"]
    final = None if not applicable or "UNRESOLVED" in applicable else all(
        status == "PASS" for status in applicable)
    if "FAIL" in applicable:
        final = False
    statuses = applicable + [row.status for row in compliance if row.status != "NOT_APPLICABLE"]
    if not replay_verified:
        success, evaluation = None, "INVALID_EVIDENCE"
    elif "FAIL" in statuses or communication.success is False or not valid_end:
        success, evaluation = False, "VERIFIED" if "UNRESOLVED" not in statuses and communication.success is not None else "UNRESOLVED"
    elif "UNRESOLVED" in statuses or communication.success is None:
        success, evaluation = None, "UNRESOLVED"
    else:
        success, evaluation = True, "VERIFIED"
    return Outcome(
        state_goals=state_goals, compliance=compliance, communication_hash=communication.record_hash,
        final_goal_reached=final, state_goal_applicability="APPLICABLE" if applicable else "NOT_APPLICABLE",
        strict_task_success=success, evaluation_status=evaluation, valid_end=valid_end)
