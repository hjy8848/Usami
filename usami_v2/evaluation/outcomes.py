"""State completion, communication and full correctness are separate results."""
from typing import Literal, Optional, Tuple

from usami_v2.contracts import Sealed
from .communication import CommunicationResult


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
