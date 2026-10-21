"""Open, multi-line business objectives; evaluation accepts any compliant SKU."""
from datetime import datetime
import re
from typing import Literal, Optional, Tuple

from pydantic import Field, field_validator, model_validator

from vast_coevo.schema import digest
from usami_v2.contracts import (
    CommunicationObligation, FactEvidence, FactKind, PublicRequest, Sealed,
    ServiceMessage, SourceRef, aware,
)
from usami_v2.commerce.invariants import invariants
from usami_v2.commerce.models import unit_credit
from usami_v2.evaluation.outcomes import GoalResult
from usami_v2.evaluation.communication import evaluate_communication
from .schema import Attribute


REMEDY_REQUEST_PATTERNS = {
    "refund": (
        r"\b(?:please\s+)?refund\s+(?:my|this|the|me|it)\b",
        r"\b(?:i\s+(?:want|need|request|would\s+like))\s+(?:a\s+)?(?:refund|reimbursement)\b",
        r"\b(?:give|send)\s+me\s+(?:a\s+)?refund\b",
        r"\b(?:i\s+(?:want|need))\s+my\s+money\s+back\b",
        r"(?:给我退款|请.{0,8}退款|我(?:要|想|需要|要求|希望).{0,4}退款|退钱给我)",
    ),
    "exchange": (
        r"\b(?:please\s+)?(?:exchange|replace|swap)\s+(?:my|this|the|it)\b",
        r"\b(?:i\s+(?:want|need|request|would\s+like))\s+(?:an?\s+)?(?:exchange|replacement)\b",
        r"(?:给我换货|请.{0,8}(?:换货|更换)|我(?:要|想|需要|要求|希望).{0,4}(?:换货|更换))",
    ),
    "reship": (
        r"\b(?:please\s+)?(?:reship|send|ship)\s+(?:it|this|the|my|another|a\s+replacement)\b",
        r"\b(?:i\s+(?:want|need|request|would\s+like))\s+(?:it\s+)?(?:resent|reshipped|sent\s+again)\b",
        r"(?:给我补发|请.{0,8}(?:补发|重寄)|我(?:要|想|需要|要求|希望).{0,4}(?:补发|重寄))",
    ),
}


def _positive_remedy_request(text, remedy):
    negative_prefix = re.compile(
        r"(?:\b(?:no|not|never|without|don't|do\s+not|didn't|cannot|can't|won't|wouldn't|shouldn't)\b)"
        r"(?:\s+[a-z]+){0,4}\s*$", re.I)
    negative_suffix = re.compile(r"^\s*(?:not|isn't|is\s+not|not\s+wanted|not\s+needed|not\s+accepted)\b", re.I)
    negative_cjk_prefix = re.compile(r"(?:不接受|不同意|不要|不想|不需要|无需|拒绝|不愿|不希望|别|禁止|请勿).{0,10}$")
    negative_cjk_suffix = re.compile(r"^.{0,8}(?:不接受|不同意|不要|不想|不需要|无需|拒绝|别|禁止|请勿)")
    text = " ".join(text.casefold().split())
    for pattern in REMEDY_REQUEST_PATTERNS[remedy]:
        for match in re.finditer(pattern, text, re.I):
            prefix = text[max(0, match.start() - 48):match.start()]
            suffix = text[match.end():match.end() + 18]
            if negative_prefix.search(prefix) or negative_suffix.search(suffix):
                continue
            if (negative_cjk_prefix.search(prefix) or negative_cjk_suffix.search(suffix)
                    or negative_cjk_prefix.search(match.group(0))
                    or negative_cjk_suffix.search(match.group(0))):
                continue
            return True
    return False


def request_names_remedy(text, remedies):
    return bool(remedies) and all(_positive_remedy_request(text, remedy) for remedy in remedies)


def public_line_match_ids(world, customer_id, mention):
    """Return owned lines whose frozen issue and SKU family are named publicly."""
    def normalized(value):
        return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.casefold()).strip()

    def contains(text, phrase):
        text, phrase = normalized(text), normalized(phrase)
        if not phrase:
            return False
        if re.search(r"[\u4e00-\u9fff]", phrase):
            return phrase in text
        return " " + phrase + " " in " " + text + " "

    normalized_mention = normalized(mention)
    owned_orders = {row.id for row in world.orders.values() if row.customer_id == customer_id}
    candidates = []
    for line in world.lines.values():
        if line.order_id not in owned_orders:
            continue
        sku = world.skus.get(line.sku_id)
        issues = {row.issue for row in world.evidence.values() if row.line_id == line.id}
        if (sku is not None
                and contains(normalized_mention, sku.product_family)
                and any(contains(normalized_mention, issue) for issue in issues)):
            candidates.append((line, sku))

    # A phrase such as "the damaged device" may match multiple lines. Publicly
    # named SKU attributes can disambiguate them without exposing internal IDs.
    attribute_names = {name for _, sku in candidates for name in sku.attributes}
    for name in sorted(attribute_names):
        values = {sku.attributes.get(name) for _, sku in candidates if sku.attributes.get(name)}
        named_values = {value for value in values if contains(normalized_mention, value)}
        if named_values:
            candidates = [(line, sku) for line, sku in candidates
                          if sku.attributes.get(name) in named_values]
    return tuple(sorted(line.id for line, _ in candidates))


class RemedyGoal(Sealed):
    goal_id: str
    line_id: str
    quantity: int = Field(ge=1, strict=True)
    allowed_remedies: Tuple[Literal["refund", "exchange", "reship"], ...] = Field(min_length=1)
    required_attributes: Tuple[Attribute, ...] = ()
    maximum_extra_charge_cents: Optional[int] = Field(default=None, ge=0, strict=True)
    latest_arrival: Optional[datetime] = None
    target_stage: Literal["settled", "delivered"] = "settled"

    @model_validator(mode="after")
    def coherent_goal(self):
        if len(set(self.allowed_remedies)) != len(self.allowed_remedies):
            raise ValueError("duplicate acceptable remedies")
        if self.latest_arrival is not None:
            aware(self.latest_arrival)
        if self.target_stage == "delivered" and "refund" in self.allowed_remedies:
            raise ValueError("a refund cannot satisfy a delivered-replacement goal")
        if len({row.name for row in self.required_attributes}) != len(self.required_attributes):
            raise ValueError("duplicate required attribute")
        return self


class GroundedRemedyGoal(RemedyGoal):
    """A new-protocol business goal linked to an exact public request span."""

    public_request_span: str = Field(min_length=1)
    subject_mention: str = Field(min_length=1)

    @field_validator("public_request_span")
    @classmethod
    def nonblank_request_span(cls, value):
        if not " ".join(value.casefold().split()):
            raise ValueError("remedy goal request span cannot be blank")
        return value


class InformationObjective(Sealed):
    goal_id: str
    subject_id: str
    subject_mention: str = Field(min_length=1)
    fact_kind: FactKind
    public_request: str = Field(min_length=1)

    @model_validator(mode="after")
    def mention_is_public(self):
        normalized = " ".join(self.public_request.casefold().split())
        mention = " ".join(self.subject_mention.casefold().split())
        if mention not in normalized:
            raise ValueError("information objective subject mention is absent from the public request")
        return self


class TaskSpec(Sealed):
    protocol: Literal["commerce-task-v1"] = "commerce-task-v1"
    task_id: str
    world_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    customer_id: str
    customer_request: str = Field(min_length=1)
    remedy_goals: Tuple[RemedyGoal, ...] = ()
    information_goals: Tuple[InformationObjective, ...] = ()
    partition: Literal["train", "validation", "heldout"]
    source_distribution_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    parent_training_evidence_hashes: Tuple[str, ...] = ()

    @field_validator("parent_training_evidence_hashes")
    @classmethod
    def valid_parent_hashes(cls, values):
        if any(len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value)
               for value in values):
            raise ValueError("training evidence references must be SHA-256 hashes")
        return values

    @model_validator(mode="after")
    def actual_goals(self):
        rows = self.remedy_goals + self.information_goals
        if not rows or len({row.goal_id for row in rows}) != len(rows):
            raise ValueError("task needs unique business/information objectives")
        normalized_request = " ".join(self.customer_request.casefold().split())
        for goal in self.information_goals:
            span = " ".join(goal.public_request.casefold().split())
            if span not in normalized_request:
                raise ValueError("information objective must be grounded in the public Customer request")
        if len({row.line_id for row in self.remedy_goals}) != len(self.remedy_goals):
            raise ValueError("combine acceptable remedies for one line rather than ambiguous duplicated goals")
        if self.partition == "heldout" and self.parent_training_evidence_hashes:
            raise ValueError("final evaluation tasks cannot be conditioned on training weakness evidence")
        return self


class TaskSpecV2(TaskSpec):
    """Versioned task with public-source binding for every remedy objective.

    The v1 TaskSpec remains readable for historical certificates and Episodes.
    New Designer output uses v2 so hidden transaction goals cannot be scored.
    """

    protocol: Literal["commerce-task-v2"] = "commerce-task-v2"
    remedy_goals: Tuple[GroundedRemedyGoal, ...] = ()

    @model_validator(mode="after")
    def remedy_goals_are_public(self):
        normalized_request = " ".join(self.customer_request.casefold().split())
        for goal in self.remedy_goals:
            span = " ".join(goal.public_request_span.casefold().split())
            mention = " ".join(goal.subject_mention.casefold().split())
            if (not span or span not in normalized_request or not mention or mention not in span
                    or not request_names_remedy(span, goal.allowed_remedies)):
                raise ValueError("remedy objective must quote the public request and name every accepted remedy")
        return self


def check_task_scope(world, task: TaskSpec):
    task = task.checked()
    if world.state_hash != task.world_hash or invariants(world):
        raise ValueError("task world binding or native invariants differ")
    if task.customer_id not in world.customers:
        raise ValueError("task Customer does not exist")

    owned_orders = {row.id for row in world.orders.values() if row.customer_id == task.customer_id}
    owned_lines = {row.id for row in world.lines.values() if row.order_id in owned_orders}

    for goal in task.remedy_goals:
        line = world.lines.get(goal.line_id)
        order = world.orders.get(line.order_id) if line else None
        if not order or order.customer_id != task.customer_id:
            raise ValueError("task crosses the frozen Customer identity")
        if isinstance(goal, GroundedRemedyGoal):
            if public_line_match_ids(world, task.customer_id, goal.subject_mention) != (line.id,):
                raise ValueError("public remedy mention must uniquely identify the frozen line issue and product family")
        occupied = {unit for row in world.cases.values()
                    if row.line_id == goal.line_id and row.status not in ("resolved", "cancelled")
                    for unit in row.unit_indices}
        settled = {unit for row in world.settlements.values() if row.line_id == goal.line_id
                   for unit in row.unit_indices}
        if goal.quantity > line.quantity - len(occupied | settled):
            raise ValueError("task exceeds the uncommitted purchased quantity")

    for goal in task.information_goals:
        if goal.subject_id not in owned_orders | owned_lines:
            raise ValueError("information objective is not about an owned order/line")
        if task.protocol == "commerce-task-v2":
            if goal.subject_id in owned_lines:
                if public_line_match_ids(world, task.customer_id, goal.subject_mention) != (goal.subject_id,):
                    raise ValueError("public information mention must uniquely identify the frozen line issue and product family")
            elif goal.subject_id in owned_orders and len(owned_orders) != 1:
                raise ValueError("order-level information target is ambiguous for this Customer")
    return task


def _validate_run_states(initial, final, task):
    task = check_task_scope(initial, task)
    if (final.seed != initial.seed or final.version != initial.version
            or final.domain != initial.domain):
        raise ValueError("final state belongs to a different business instance")
    if invariants(final):
        raise ValueError("final state violates native business invariants")
    immutable = ("customers", "merchants", "skus", "warehouses", "orders", "lines", "evidence")
    if any(getattr(initial, name) != getattr(final, name) for name in immutable):
        raise ValueError("final state changed frozen source business facts")
    if final.clock < initial.clock:
        raise ValueError("final business clock moved backwards")
    return task


def evaluate_state_goals(initial, final, task: TaskSpec):
    """Return only registered business-state objectives.

    Communication and out-of-scope settlement checks are separate so a
    read-only task can correctly have no state goal while still succeeding.
    """
    task = _validate_run_states(initial, final, task)
    rows = []
    for goal in task.remedy_goals:
        settlements = [row for key, row in final.settlements.items()
                       if row.line_id == goal.line_id and key not in initial.settlements]
        quantity = sum(len(row.unit_indices) for row in settlements)
        ok = quantity == goal.quantity and all(row.remedy in goal.allowed_remedies for row in settlements)
        requested_units = set()
        for settlement in settlements:
            if requested_units.intersection(settlement.unit_indices):
                ok = False
            requested_units.update(settlement.unit_indices)
            line = initial.lines[goal.line_id]
            previously_used = {unit for row in initial.settlements.values() if row.line_id == goal.line_id
                               for unit in row.unit_indices}
            previously_used.update(unit for row in initial.cases.values()
                                   if row.line_id == goal.line_id and row.status not in ("resolved", "cancelled")
                                   for unit in row.unit_indices)
            if any(unit in previously_used for unit in settlement.unit_indices):
                ok = False
            if any(type(unit) is not int or unit < 0 or unit >= line.quantity
                   for unit in settlement.unit_indices):
                ok = False
        refs = []
        extra = 0
        for settlement in settlements:
            refs.append(digest(settlement))
            quote = final.quotes.get(settlement.quote_id)
            if quote is None:
                ok = False
                continue
            ledger = [entry for entry in final.ledger.values() if entry.quote_id == quote.id]
            extra += sum(entry.amount_cents for entry in ledger if entry.kind == "extra_charge")
            if settlement.remedy == "refund":
                paid = unit_credit(initial.lines[goal.line_id], settlement.unit_indices)
                if sum(entry.amount_cents for entry in ledger if entry.kind == "refund") != paid:
                    ok = False
                if goal.required_attributes or goal.latest_arrival is not None:
                    ok = False
                order = initial.orders[initial.lines[goal.line_id].order_id]
                if any(entry.channel != order.payment_channel for entry in ledger):
                    ok = False
            else:
                deliveries = [row for row in final.fulfillments.values() if row.quote_id == quote.id]
                if len(deliveries) != 1:
                    ok = False
                    continue
                delivery = deliveries[0]
                sku = final.skus.get(delivery.sku_id)
                if not sku or any(sku.attributes.get(row.name) != row.value for row in goal.required_attributes):
                    ok = False
                if goal.target_stage == "delivered" and delivery.actual_arrival is None:
                    ok = False
                arrival = delivery.actual_arrival or delivery.promised_arrival
                if goal.latest_arrival is not None and arrival > goal.latest_arrival:
                    ok = False
                refs.append(digest(delivery))
        if goal.maximum_extra_charge_cents is not None and extra > goal.maximum_extra_charge_cents:
            ok = False
        rows.append(GoalResult(goal_id=goal.goal_id, status="PASS" if ok else "FAIL", evidence_refs=tuple(refs)))

    return tuple(rows)


def evaluate_task_compliance(initial, final, task: TaskSpec):
    """Report unrequested settlements as a compliance result, not goal progress."""
    task = _validate_run_states(initial, final, task)
    allowed_lines = {row.line_id for row in task.remedy_goals}
    unexpected = [row for key, row in final.settlements.items()
                  if key not in initial.settlements and row.line_id not in allowed_lines]
    return (GoalResult(goal_id="unrequested_settlements", status="FAIL" if unexpected else "PASS",
                       evidence_refs=tuple(digest(row) for row in unexpected)),)


def evaluate_task_communication(initial, task: TaskSpec, *, facts=(), messages=(), end_event_index=None):
    """Evaluate requests grounded in the frozen Customer text against delivered claims."""
    task = check_task_scope(initial, task)
    if task.information_goals:
        messages = tuple(messages)
        if end_event_index is None:
            end_event_index = max((row.event_index for row in messages), default=0)
        obligations = []
        for goal in task.information_goals:
            source = SourceRef(
                source_id="customer-request-" + goal.goal_id,
                source_kind="customer_message",
                source_hash=digest({"customer_request": task.customer_request,
                                   "request_span": goal.public_request}),
                event_index=0)
            request = PublicRequest(
                request_id=goal.goal_id, subject_id=goal.subject_id, fact_kind=goal.fact_kind,
                source=source, public_text=goal.public_request)
            obligations.append(CommunicationObligation(
                obligation_id="information-" + goal.goal_id, request=request,
                due_event_index=end_event_index, required=True))
        return evaluate_communication(facts, messages, obligations,
                                      end_event_index=end_event_index, terminal=True)
    messages = tuple(messages)
    if end_event_index is None:
        end_event_index = max((row.event_index for row in messages), default=0)
    return evaluate_communication(facts, messages, (), end_event_index=end_event_index, terminal=True)
