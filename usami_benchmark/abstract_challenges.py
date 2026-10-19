"""Strict, ID-free challenge language for the world-grounded batch Designer.

The grammar is deliberately smaller than the native task language. A Designer
can choose predicates and goals; it cannot provide entity IDs, frames, native
operations, Reference outcomes, or executable code.
"""
from __future__ import annotations

import re

from typing import Any, Literal, Optional
from pydantic import Field, model_validator

from usami_harness.models import Model, digest


PROTOCOL = "world-grounded-batch-designer-v1"
BATCH_REVISION_PROTOCOL = "world-grounded-batch-designer-one-revision-v1"

EntityType = Literal["profile", "customer", "order", "line", "product", "evidence", "external_event"]
Operator = Literal["eq", "neq", "in", "lt", "lte", "gt", "gte"]
Predicate = Literal["within_case_window", "eligible_for_case", "has_valid_evidence", "requires_approval", "registered_event_exists"]
Relation = Literal["distinct", "same_identity", "same_owner", "references", "profile_for_line", "event_for_line"]


class EntityVariable(Model):
    alias: str = Field(min_length=1, max_length=48, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    type: EntityType


class EntityConstraint(Model):
    alias: str = Field(min_length=1, max_length=48)
    field: Optional[str] = None
    op: Optional[Operator] = None
    value: Any = None
    predicate: Optional[Predicate] = None

    @model_validator(mode="after")
    def exactly_field_or_predicate(self):
        field_form = self.field is not None or self.op is not None
        predicate_form = self.predicate is not None
        if field_form == predicate_form:
            raise ValueError("constraint must define exactly one field comparison or registered predicate")
        if field_form and (self.field is None or self.op is None):
            raise ValueError("field comparisons need both field and operator")
        if predicate_form and self.op is not None:
            raise ValueError("registered predicates do not accept an operator")
        return self


class RelationshipConstraint(Model):
    type: Relation
    left: str = Field(min_length=1, max_length=48)
    right: str = Field(min_length=1, max_length=48)


class ChallengeObjective(Model):
    kind: Literal["existing_object_completion", "created_object_completion", "correct_refusal"]
    target: str = Field(min_length=1, max_length=48)
    collection: Optional[Literal["lines", "cases"]] = None
    field: Optional[Literal["status"]] = None
    accepted_values: list[str] = Field(default_factory=list, max_length=8)
    operation: Optional[Literal["open_case"]] = None

    @model_validator(mode="after")
    def validate_objective_shape(self):
        if self.kind == "existing_object_completion":
            if self.collection != "lines" or self.field != "status" or not self.accepted_values or self.operation:
                raise ValueError("existing completion currently targets a line status with accepted values")
            if set(self.accepted_values) - {"return_pending", "refunded", "exchanged", "reshipped"}:
                raise ValueError("unregistered After-sales line completion value")
        elif self.kind == "created_object_completion":
            if self.collection != "cases" or self.field != "status" or not self.accepted_values or self.operation:
                raise ValueError("created completion currently targets a Case status")
            if set(self.accepted_values) - {"open", "evidence_verified"}:
                raise ValueError("unregistered Case completion value")
        elif self.operation != "open_case" or any((self.collection, self.field, self.accepted_values)):
            raise ValueError("correct refusal currently targets the native open_case operation only")
        if len(self.accepted_values) != len(set(self.accepted_values)):
            raise ValueError("objective values must not repeat")
        return self


class CustomerInformationRequirement(Model):
    profile_alias: str = Field(min_length=1, max_length=48)
    fact_keys: list[Literal["order_id", "line_id", "issue", "evidence_id", "deadline", "pickup_slot"]] = Field(min_length=1, max_length=6)


class CustomerPreferenceRequirement(Model):
    profile_alias: str = Field(min_length=1, max_length=48)
    preference: Literal["resolution"] = "resolution"
    accepted_values: list[Literal["refund", "exchange", "reship"]] = Field(min_length=1, max_length=3)


class ExternalEventConstraint(Model):
    target_alias: str = Field(min_length=1, max_length=48)
    kind: Literal["manager_review", "return_received"]
    outcome: Literal["approved", "denied", "received", "missing"]
    required: bool = True


class AbstractChallenge(Model):
    challenge_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    hypothesis: str = Field(min_length=8, max_length=1200)
    domain: Literal["aftersales", "airline", "property", "education", "saas", "cloudops", "fulfillment", "stayops"]
    customer_request: str = Field(min_length=8, max_length=1200)
    entity_variables: list[EntityVariable] = Field(min_length=1, max_length=10)
    entity_constraints: list[EntityConstraint] = Field(default_factory=list, max_length=32)
    relationship_constraints: list[RelationshipConstraint] = Field(default_factory=list, max_length=24)
    objectives: list[ChallengeObjective] = Field(min_length=1, max_length=8)
    required_customer_information: list[CustomerInformationRequirement] = Field(default_factory=list, max_length=10)
    required_customer_preferences: list[CustomerPreferenceRequirement] = Field(default_factory=list, max_length=10)
    external_event_constraints: list[ExternalEventConstraint] = Field(default_factory=list, max_length=12)
    difficulty_hypothesis: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def unique_variables_and_objectives(self):
        aliases = [v.alias for v in self.entity_variables]
        if len(aliases) != len(set(aliases)):
            raise ValueError("entity aliases must be unique")
        if len({r.profile_alias for r in self.required_customer_information}) != len(self.required_customer_information):
            raise ValueError("at most one information declaration is allowed per profile alias")
        if len({r.profile_alias for r in self.required_customer_preferences}) != len(self.required_customer_preferences):
            raise ValueError("at most one preference declaration is allowed per profile alias")
        return self

    @property
    def challenge_hash(self) -> str:
        return digest(self)


class ChallengeBatch(Model):
    protocol: Literal[PROTOCOL] = PROTOCOL
    challenges: list[AbstractChallenge] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def unique_challenge_ids(self):
        ids = [c.challenge_id for c in self.challenges]
        if len(ids) != len(set(ids)):
            raise ValueError("challenge_id values must be unique in a batch")
        return self


FIELD_ALLOWLIST: dict[str, dict[str, set[str]]] = {
    "aftersales": {
        "profile": {"issue"},
        "customer": set(),
        "order": {"status", "paid_cents", "payment_channel", "delivered_at"},
        "line": {"status", "quantity", "unit_price_cents"},
        "product": {"stock", "returnable", "return_days", "return_required", "replacement_days"},
        "evidence": {"issue", "simulated_valid"},
        "external_event": {"kind", "outcome", "at"},
    }
}

PREDICATE_TYPES: dict[str, set[str]] = {
    "within_case_window": {"line"}, "eligible_for_case": {"line"},
    "has_valid_evidence": {"line"}, "requires_approval": {"line"},
    "registered_event_exists": {"line"},
}


def validate_challenge(challenge: AbstractChallenge | dict) -> AbstractChallenge:
    """Validate typed references and fixed grammar before any world lookup."""
    row = challenge if isinstance(challenge, AbstractChallenge) else AbstractChallenge.model_validate(challenge)
    if row.domain != "aftersales":
        raise ValueError("grounder supports the registered aftersales grammar only")
    variables = {v.alias: v.type for v in row.entity_variables}
    if len({v.type for v in row.entity_variables}) > 7:
        raise ValueError("unsupported entity type combination")
    fields = FIELD_ALLOWLIST[row.domain]
    for constraint in row.entity_constraints:
        kind = variables.get(constraint.alias)
        if kind is None:
            raise ValueError("entity constraint references an unknown alias")
        if constraint.predicate:
            if kind not in PREDICATE_TYPES.get(constraint.predicate, set()):
                raise ValueError("registered predicate is unsupported for this entity type")
            if type(constraint.value) is not bool:
                raise ValueError("registered predicate value must be boolean")
        else:
            if constraint.field not in fields[kind]:
                raise ValueError("unknown field for declared entity type")
            if constraint.op == "in" and (not isinstance(constraint.value, list) or not constraint.value):
                raise ValueError("in predicate needs a nonempty value list")
            if constraint.op != "in" and isinstance(constraint.value, (dict, list)):
                raise ValueError("field comparison values must be scalar")
    for relation in row.relationship_constraints:
        left, right = variables.get(relation.left), variables.get(relation.right)
        if left is None or right is None:
            raise ValueError("relationship references an unknown alias")
        allowed = {
            "distinct": left == right,
            "same_identity": left in {"profile", "customer"} and right in {"profile", "customer"},
            "same_owner": left in {"profile", "line", "order"} and right in {"profile", "line", "order"},
            "references": (left, right) in {("line", "order"), ("line", "product"), ("evidence", "line"),
                           ("external_event", "line"), ("profile", "line"), ("profile", "order"),
                           ("profile", "evidence"), ("order", "customer")},
            "profile_for_line": (left, right) in {("profile", "line"), ("line", "profile")},
            "event_for_line": (left, right) in {("external_event", "line"), ("line", "external_event")},
        }[relation.type]
        if not allowed:
            raise ValueError("relationship type is not registered for these entity types")
    for objective in row.objectives:
        expected = "line" if objective.kind in {"existing_object_completion", "correct_refusal"} else "line"
        if variables.get(objective.target) != expected:
            raise ValueError("objective target must reference a declared line variable")
        related = any(r.type == "profile_for_line" and
                      ((variables.get(r.left) == "profile" and r.right == objective.target) or
                       (variables.get(r.right) == "profile" and r.left == objective.target))
                      for r in row.relationship_constraints)
        if not related:
            raise ValueError("each objective line needs an explicit profile_for_line relationship")
    for requirement in row.required_customer_information:
        if variables.get(requirement.profile_alias) != "profile":
            raise ValueError("information requirement must reference a profile alias")
        if not any(r.type == "profile_for_line" and
                   ((r.left == requirement.profile_alias and variables.get(r.right) == "line") or
                    (r.right == requirement.profile_alias and variables.get(r.left) == "line"))
                   for r in row.relationship_constraints):
            raise ValueError("information profile must be explicitly related to an objective line")
    for requirement in row.required_customer_preferences:
        if variables.get(requirement.profile_alias) != "profile":
            raise ValueError("preference requirement must reference a profile alias")
        if not any(r.type == "profile_for_line" and
                   ((r.left == requirement.profile_alias and variables.get(r.right) == "line") or
                    (r.right == requirement.profile_alias and variables.get(r.left) == "line"))
                   for r in row.relationship_constraints):
            raise ValueError("preference profile must be explicitly related to an objective line")
    for event in row.external_event_constraints:
        if variables.get(event.target_alias) != "line":
            raise ValueError("external event constraint must reference a line alias")
        if event.kind == "manager_review" and event.outcome not in {"approved", "denied"}:
            raise ValueError("manager_review events must have approved or denied outcomes")
        if event.kind == "return_received" and event.outcome not in {"received", "missing"}:
            raise ValueError("return_received events must have received or missing outcomes")
    forbidden = re.compile(r"\b(?:profile_u\d+_order\d+_line\d+|u\d+_order\d+(?:_line\d+)?|photo_u\d+_order\d+_line\d+|(?:manager_review|return_received)_u\d+_order\d+_line\d+|case_[0-9a-f]{8,}|quote_[0-9a-f]{8,})\b")
    text = " ".join((row.customer_request, row.hypothesis))
    if forbidden.search(text):
        raise ValueError("abstract challenge text must not contain concrete generated-world identifiers")
    return row


def challenge_fingerprints(challenge: AbstractChallenge | dict) -> dict[str, str]:
    row = challenge if isinstance(challenge, AbstractChallenge) else AbstractChallenge.model_validate(challenge)
    variables = {v.alias: v.type for v in row.entity_variables}
    structure = {
        "entity_types": sorted(variables.values()),
        "relationships": sorted(sorted([r.type, variables[r.left], variables[r.right]]) for r in row.relationship_constraints),
        "objective_types": sorted(o.kind for o in row.objectives),
        "objective_targets": sorted([o.kind, variables[o.target]] for o in row.objectives),
    }
    semantic = {
        **structure,
        "constraints": sorted([
            [variables[c.alias], c.field, c.op, c.value, c.predicate] for c in row.entity_constraints
        ], key=lambda x: repr(x)),
        "information": sorted([[variables[r.profile_alias], sorted(r.fact_keys)] for r in row.required_customer_information]),
        "preferences": sorted([[r.preference, sorted(r.accepted_values)] for r in row.required_customer_preferences]),
        "events": sorted([[e.kind, e.outcome, e.required] for e in row.external_event_constraints]),
        "objectives": sorted([[o.kind, o.collection, o.field, sorted(o.accepted_values), o.operation] for o in row.objectives]),
    }
    return {"structural": digest(structure), "semantic": digest(semantic)}
