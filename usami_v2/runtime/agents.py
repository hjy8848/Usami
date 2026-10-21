"""Optional OpenAI-compatible Customer/Service decision adapters.

No provider is contacted on import. Callers must explicitly construct these
adapters with an existing CompletionClient and invoke the episode Runner.
"""
import json
from typing import Any, Dict, List, Optional, Protocol, Tuple

from pydantic import Field

from usami.service.client import CompletionClient
from usami.service.models import ModelSettings, ServiceError, strict_json
from usami_v2.commerce.models import Operation, PARAMETERS
from usami_v2.runtime.customer import CustomerDecision, CustomerProfile, OfferPresentation
from usami_v2.contracts import Sealed


class AgentMessage(Sealed):
    role: str
    content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Tuple[Dict[str, Any], ...] = ()


class CustomerPrompt(Sealed):
    public_request: str
    last_service_message: str = ""
    offer: Optional[OfferPresentation] = None
    conversation: Tuple[AgentMessage, ...] = ()


class ServicePrompt(Sealed):
    customer_id: str
    customer_request: str
    conversation: Tuple[AgentMessage, ...] = ()
    # These are public tool results already delivered to the Service.
    observed_subject_ids: Tuple[str, ...] = ()


class AgentCall(Sealed):
    role: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    prompt_tokens: Optional[int] = Field(default=None, ge=0, strict=True)
    completion_tokens: Optional[int] = Field(default=None, ge=0, strict=True)


class ServiceAction(Sealed):
    kind: str
    operation: Optional[Operation] = None
    message: str = ""
    present_quote_id: Optional[str] = None
    present_for: str = "commit_accepted_quote"
    subject_ids: Tuple[str, ...] = ()
    call: Optional[AgentCall] = None
    call_id: str = ""

    @classmethod
    def from_tool_message(cls, raw, customer_id, observed_subject_ids=()):
        message = _one_tool_call(raw)
        call = message["tool_calls"][0]
        name, args = call["function"]["name"], _json_arguments(call["function"]["arguments"])
        completion = AgentCall(
            role="service", request={}, response=raw,
            prompt_tokens=_usage(raw, "prompt_tokens"), completion_tokens=_usage(raw, "completion_tokens"))
        if name == "respond_to_customer":
            if not isinstance(args.get("message"), str) or not args["message"].strip():
                raise ServiceError("MODEL_OUTPUT_INVALID", "Service reply must contain nonempty message text")
            subjects = tuple(args.get("subject_ids") or ())
            if not set(subjects).issubset(set(observed_subject_ids)):
                raise ServiceError("MODEL_OUTPUT_INVALID", "Service reply references an object it never observed")
            return cls(kind="reply", message=args["message"], present_quote_id=args.get("present_quote_id"),
                       present_for=args.get("present_for") or "commit_accepted_quote", subject_ids=subjects,
                       call=completion, call_id=call["id"])
        if name not in PARAMETERS:
            raise ServiceError("MODEL_OUTPUT_INVALID", "Service selected an unregistered commerce tool")
        try:
            operation = Operation(name=name, scope_id=args["scope_id"], resource_id=args["resource_id"],
                                  params=args.get("params", {}))
        except (KeyError, TypeError, ValueError):
            raise ServiceError("MODEL_OUTPUT_INVALID", "Service tool arguments do not match the native schema") from None
        # A Request is created only by the Runner for this exact tool call; the
        # Reference still independently checks identity, delegation and consent.
        return cls(kind="operation", operation=operation, call=completion, call_id=call["id"])


def _usage(raw, name):
    usage = raw.get("usage", {}) if isinstance(raw, dict) else {}
    value = usage.get(name) if isinstance(usage, dict) else None
    return value if type(value) is int and value >= 0 else None


def _json_arguments(text):
    try:
        value = strict_json(text)
    except (TypeError, ValueError):
        raise ServiceError("MODEL_OUTPUT_INVALID", "Tool arguments are not valid JSON") from None
    if not isinstance(value, dict):
        raise ServiceError("MODEL_OUTPUT_INVALID", "Tool arguments must be a JSON object")
    return value


def _safe_failure(role, request, exc):
    """Keep the attempted request and a credential-safe failure code, never headers."""
    code = getattr(exc, "code", None)
    if not isinstance(code, str) or not code:
        code = "AGENT_REQUEST_FAILED"
    return AgentCall(role=role, request=request,
                     response={"error": {"type": type(exc).__name__, "code": code}})


def _one_tool_call(raw):
    try:
        choices = raw["choices"]
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError
        message = choices[0]["message"]
        calls = message.get("tool_calls")
        if message.get("role") != "assistant" or not isinstance(calls, list) or len(calls) != 1:
            raise ValueError
        call = calls[0]
        if (call.get("type") != "function" or not isinstance(call.get("id"), str)
                or not call["id"] or not isinstance(call.get("function", {}).get("name"), str)
                or not isinstance(call["function"].get("arguments"), str)):
            raise ValueError
        if choices[0].get("finish_reason") != "tool_calls":
            raise ValueError
        return message
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ServiceError("MODEL_OUTPUT_INVALID", "Expected exactly one complete structured function call") from None


def _schema_with_defs(model):
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})
    schema.pop("title", None)
    return schema, definitions


def service_tools():
    tools = []
    for name, parameter_model in sorted(PARAMETERS.items()):
        schema, definitions = _schema_with_defs(parameter_model)
        tools.append({"type": "function", "function": {
            "name": name, "description": "Execute one registered commerce operation through the business engine.",
            "parameters": {"type": "object", "properties": {
                "scope_id": {"type": "string"}, "resource_id": {"type": "string"}, "params": schema,
            }, "required": ["scope_id", "resource_id", "params"], "additionalProperties": False,
                **({"$defs": definitions} if definitions else {})}}})
    tools.append({"type": "function", "function": {
        "name": "respond_to_customer", "description": "Send the next customer-facing message or present an existing quote.",
        "parameters": {"type": "object", "properties": {
            "message": {"type": "string"}, "present_quote_id": {"type": ["string", "null"]},
            "present_for": {"type": "string", "enum": ["commit_accepted_quote", "release_accepted_refund"]},
            "subject_ids": {"type": "array", "items": {"type": "string"}},
        }, "required": ["message", "present_quote_id", "present_for", "subject_ids"],
           "additionalProperties": False}}})
    return tools


CUSTOMER_TOOLS = [{"type": "function", "function": {
    "name": "customer_turn", "description": "Respond naturally and declare only Customer-side intent.",
    "parameters": {"type": "object", "properties": {
        "message": {"type": "string"},
        "delegate_line_ids": {"type": "array", "items": {"type": "string"}},
        "allowed_preparations": {"type": "array", "items": {"type": "string"}},
        "accept_quote_id": {"type": ["string", "null"]},
        "accept_operation": {"type": ["string", "null"], "enum": ["commit_accepted_quote", "release_accepted_refund", None]},
        "reject_quote_id": {"type": ["string", "null"]},
        "withdraw_delegation_ids": {"type": "array", "items": {"type": "string"}},
        "disclose_fact_ids": {"type": "array", "items": {"type": "string"}},
        "finish": {"type": "boolean"},
    }, "required": ["message", "delegate_line_ids", "allowed_preparations", "accept_quote_id",
                    "accept_operation", "reject_quote_id", "withdraw_delegation_ids", "disclose_fact_ids", "finish"],
       "additionalProperties": False}}}]


class OpenAICustomerAgent:
    """Customer-only model adapter; never pass its private prompt to Service."""

    uses_model = True

    def __init__(self, client: CompletionClient):
        self.client = client
        self.settings: ModelSettings = client.settings.model_copy(deep=True)
        self.last_call: Optional[AgentCall] = None

    def decide(self, prompt: CustomerPrompt, profile: CustomerProfile):
        self.last_call = None
        profile = profile.checked()
        system = (
            "Simulate the authenticated customer. You may disclose only facts in the private profile, "
            "delegate only the listed business lines/preparations, and accept only the exact quote shown. "
            "Do not claim an operation completed. A quote acceptance is transaction consent only for the "
            "named quote and operation. Keep natural-language preferences consistent across turns.\n"
            "PRIVATE CUSTOMER PROFILE: " + json.dumps(profile.model_dump(mode="json"), ensure_ascii=False)
        )
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps({
                        "public_request": prompt.public_request,
                        "last_service_message": prompt.last_service_message,
                        "presented_offer": prompt.offer.model_dump(mode="json") if prompt.offer else None,
                        "conversation": [row.model_dump(mode="json") for row in prompt.conversation],
                    }, ensure_ascii=False)}]
        request = self.settings.request(messages, CUSTOMER_TOOLS)
        request["tool_choice"] = {"type": "function", "function": {"name": "customer_turn"}}
        try:
            raw = self.client.complete(request)
        except Exception as exc:
            self.last_call = _safe_failure("customer", request, exc)
            raise
        self.last_call = AgentCall(role="customer", request=request, response=raw,
                                   prompt_tokens=_usage(raw, "prompt_tokens"),
                                   completion_tokens=_usage(raw, "completion_tokens"))
        call_message = _one_tool_call(raw)
        function = call_message["tool_calls"][0]["function"]
        if function["name"] != "customer_turn":
            raise ServiceError("MODEL_OUTPUT_INVALID", "Customer selected an unregistered action")
        try:
            decision = CustomerDecision.model_validate(_json_arguments(function["arguments"]))
        except ValueError:
            raise ServiceError("MODEL_OUTPUT_INVALID", "Customer decision violates its response contract") from None
        return decision


class OpenAIServiceAgent:
    """Function-calling Service; it receives public task text and tool outputs only."""

    uses_model = True

    SYSTEM = (
        "You are a commerce customer-service agent. Decide what to query and what action to take from "
        "the customer's public request and public tool results. You never receive hidden TaskSpec goals, "
        "Customer preferences, proof witnesses or Oracle decisions. Tool writes are not Customer consent. "
        "Never commit a quote unless the Customer runtime has separately recorded exact consent; never claim "
        "completion without a successful tool result. Present the actual quote to the Customer before asking "
        "for acceptance. Use one tool call per response and continue reasoning from its result."
    )

    def __init__(self, client: CompletionClient):
        self.client = client
        self.settings: ModelSettings = client.settings.model_copy(deep=True)
        self.last_call: Optional[AgentCall] = None

    def decide(self, prompt: ServicePrompt):
        self.last_call = None
        messages = [{"role": "system", "content": self.SYSTEM},
                    {"role": "user", "content": "Customer request: " + prompt.customer_request}]
        messages.extend(row.model_dump(mode="json", exclude_none=True) for row in prompt.conversation)
        request = self.settings.request(messages, service_tools())
        try:
            raw = self.client.complete(request)
        except Exception as exc:
            self.last_call = _safe_failure("service", request, exc)
            raise
        self.last_call = AgentCall(role="service", request=request, response=raw,
                                   prompt_tokens=_usage(raw, "prompt_tokens"),
                                   completion_tokens=_usage(raw, "completion_tokens"))
        action = ServiceAction.from_tool_message(raw, prompt.customer_id, prompt.observed_subject_ids)
        data = action.model_dump(mode="json", exclude={"record_hash"})
        data["call"] = self.last_call.model_dump(mode="json")
        return ServiceAction.model_validate(data)
