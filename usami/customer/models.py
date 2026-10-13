"""Untrusted choices made by a Customer LLM, never role or identity grants."""
from typing import List, Literal

from pydantic import Field, model_validator

from usami.protocol import Operation, PARAMETERS, QUERIES
from usami.world.models import Model


class CustomerAction(Model):
    type: Literal["send_message", "stop"]
    message: str = ""
    requested_operations: List[Operation] = Field(default_factory=list)
    reason: str = ""

    @model_validator(mode="after")
    def action_shape(self):
        if self.type == "stop":
            if self.message or self.requested_operations:
                raise ValueError("stop cannot send a message or request operations")
        elif not self.message.strip() and not self.requested_operations:
            raise ValueError("send_message needs context or a structured business request")
        if any(op.is_query for op in self.requested_operations):
            raise ValueError("requested_operations describes writes; ask queries in the message")
        return self


def action_schema(tools):
    """Describe the Customer's nested Operation shape using core parameter models."""
    target_types = {"refund_invoice": "invoice ID", "change_member_role": "membership ID (not a user or organization ID)"}
    operations = []
    for name in tools:
        if name not in PARAMETERS or name in QUERIES:
            continue
        operations.append({"type": "object", "additionalProperties": False,
            "required": ["name", "org_id", "resource_id", "params"], "properties": {
                "name": {"const": name}, "org_id": {"type": "string", "description": "Observed organization ID"},
                "resource_id": {"type": "string", "description": "Observed " + target_types.get(name, "subscription ID")},
                "params": PARAMETERS[name].model_json_schema()}})
    schema = CustomerAction.model_json_schema()
    schema.pop("$defs", None)
    schema["properties"]["requested_operations"]["items"] = {"anyOf": operations} if operations else False
    return schema
