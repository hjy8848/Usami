from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, model_validator

from usami.world.models import Model


class ChangePlan(Model):
    plan_id: str


class ChangeSeats(Model):
    seats: int = Field(strict=True, ge=0)


class RefundInvoice(Model):
    amount_cents: int = Field(strict=True, ge=0)
    payment_method: str


class ChangeRole(Model):
    role: Literal["owner", "billing_admin", "member"]


class NoParams(Model):
    pass


PARAMETERS = {
    "change_plan": ChangePlan, "change_seats": ChangeSeats,
    "cancel_renewal": NoParams, "refund_invoice": RefundInvoice,
    "change_member_role": ChangeRole,
    "get_organization": NoParams, "get_subscription": NoParams,
    "get_invoice": NoParams, "list_members": NoParams,
}
QUERIES = frozenset({"get_organization", "get_subscription", "get_invoice", "list_members"})


class Operation(Model):
    name: Literal["change_plan", "change_seats", "cancel_renewal", "refund_invoice",
                  "change_member_role", "get_organization", "get_subscription",
                  "get_invoice", "list_members"]
    org_id: str
    resource_id: str
    params: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def parameter_shape(self) -> Operation:
        PARAMETERS[self.name].model_validate(self.params)
        return self

    @property
    def is_query(self) -> bool:
        return self.name in QUERIES


class RequestContext(Model):
    """Created by the trusted caller/harness before execution, never by a service."""
    request_id: str
    requester_id: str
    org_id: str
    resource_id: str
    kind: Literal["query", "operation"]
    operation: Operation
    authorized_operations: List[Operation] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_scope(self) -> RequestContext:
        if (self.org_id, self.resource_id) != (self.operation.org_id, self.operation.resource_id):
            raise ValueError("request target must match the requested operation")
        if (self.kind == "query") != self.operation.is_query:
            raise ValueError("request kind must match operation")
        return self

    def authorizes(self, actor_id: str, operation: Operation) -> bool:
        return (actor_id == self.requester_id and operation == self.operation
                and operation in self.authorized_operations)


def make_request(request_id: str, actor_id: str, operation: Operation,
                 authorized: bool = True) -> RequestContext:
    return RequestContext(request_id=request_id, requester_id=actor_id,
                          org_id=operation.org_id, resource_id=operation.resource_id,
                          kind="query" if operation.is_query else "operation", operation=operation,
                          authorized_operations=[operation] if authorized else [])


class ExecutionResult(Model):
    success: bool
    error_code: Optional[str] = None
    data: Dict = Field(default_factory=dict)


class RuleDecision(Model):
    allowed: bool
    error_code: Optional[str] = None
    detail: str = ""
    expected_state: Optional["WorldState"] = None
    expected_data: Dict = Field(default_factory=dict)


from usami.world.models import WorldState  # resolve nested snapshot type
RuleDecision.model_rebuild()
