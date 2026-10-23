"""Execute task programs through unchanged Usami Customer/Engine/Oracle/Replay."""
from dataclasses import dataclass
import json

from rsi_core.protocol import CandidateError, InfrastructureError, TaskResult, canonical
from usami_v2.runtime.agents import AgentCall, OpenAIServiceAgent, ServiceAction, service_tools
from usami_v2.runtime.runner import EpisodeBudget, replay_episode, run_episode, save_episode, verify_episode_artifact


@dataclass(frozen=True)
class NativeTask:
    world: object
    task: object
    customer_profile: object
    customer_factory: object
    budget: EpisodeBudget
    external_events: tuple = ()
    mode: str = "reference"


def baseline_request(prompt, snapshot):
    """Public projection equivalent to native S0, tested against its actual request."""
    messages = [{"role": "system", "content": OpenAIServiceAgent.SYSTEM},
                {"role": "user", "content": json.dumps({
                    "authenticated_customer_id": prompt.customer_id,
                    "available_merchant_scope_ids": list(prompt.available_merchant_scope_ids),
                    "customer_request": prompt.customer_request}, ensure_ascii=False)}]
    history = list(prompt.conversation)
    if history and history[0].role == "user" and history[0].content == prompt.customer_request:
        history = history[1:]
    messages.extend(row.model_dump(mode="json", exclude_none=True) for row in history)
    return {**snapshot.sampling, "model": snapshot.model_id, "messages": messages, "tools": service_tools(),
            "tool_choice": "auto", "stream": False, "n": 1, "parallel_tool_calls": False}


class ProgramServiceAgent:
    uses_model = False  # Some P steps use no model; actual calls still carry AgentCall.
    last_call = None

    def __init__(self, program, worker, model, models, ledger, seed):
        self.program, self.worker, self.model = program, worker, model
        self.models, self.ledger, self.seed = models, ledger, seed
        self.memory, self.inputs, self.model_events, self.failure = {}, [], [], None

    def decide(self, prompt):
        self.last_call = None
        view = {"customer_id": prompt.customer_id, "customer_request": prompt.customer_request,
                "conversation": [row.model_dump(mode="json", exclude_none=True) for row in prompt.conversation],
                "available_merchant_scope_ids": list(prompt.available_merchant_scope_ids),
                "observed_subject_ids": list(prompt.observed_subject_ids),
                "baseline_request": baseline_request(prompt, self.models.business)}
        try:
            for _ in range(8):
                self.ledger.charge("solver", research_steps=1)
                self.inputs.append({"public_view": view, "memory": self.memory})
                decision = self.worker.invoke(self.program, view, self.memory, self.ledger, "solver")
                if not isinstance(decision, dict) or not isinstance(decision.get("state"), dict):
                    raise CandidateError("P must return kind and explicit memory object")
                self.memory = decision["state"]
                if decision.get("kind") == "MODEL":
                    if set(decision) != {"kind", "state", "request"} or not isinstance(decision["request"], dict):
                        raise CandidateError("invalid task model request")
                    if self.model is None:
                        raise InfrastructureError("business model is not configured")
                    request = decision["request"]
                    # Source cannot change the model identity, tools or parallel-call policy.
                    if (request.get("model") != self.models.business.model_id
                            or request.get("tools") != service_tools()
                            or request.get("parallel_tool_calls") is not False):
                        raise CandidateError("P attempted to change native tools/model capabilities")
                    allowance = min(2048, int(self.ledger.remaining("model_tokens")))
                    if allowance < 1 or self.ledger.remaining("model_calls") < 1:
                        raise CandidateError("business model budget exhausted")
                    self.ledger.charge("solver", model_calls=1)
                    response = self.model.complete(self.models.business, request, max_tokens=allowance,
                                                   seed=self.seed + len(self.model_events))
                    self.model_events.append({"snapshot_ref": self.models.business.ref, "request": request,
                                              "response": response.output, "prompt_tokens": response.prompt_tokens,
                                              "completion_tokens": response.completion_tokens})
                    self.ledger.charge("solver", model_tokens=response.prompt_tokens + response.completion_tokens)
                    self.last_call = AgentCall(role="service", request=request, response=response.output,
                                               prompt_tokens=response.prompt_tokens,
                                               completion_tokens=response.completion_tokens)
                    action = ServiceAction.from_tool_message(response.output, prompt.customer_id,
                                                             prompt.observed_subject_ids)
                    view = {**view, "model_observation": action.model_dump(mode="json", exclude={"record_hash", "call", "call_id"})}
                elif decision.get("kind") == "ACTION":
                    if set(decision) != {"kind", "state", "action"} or not isinstance(decision["action"], dict):
                        raise CandidateError("invalid task action envelope")
                    action_data = decision["action"]
                    if set(action_data) - {"kind", "operation", "message", "present_quote_id", "present_for", "subject_ids"}:
                        raise CandidateError("P cannot forge model call evidence or Host metadata")
                    action = ServiceAction.model_validate(action_data)
                    if action.kind not in {"operation", "reply"}:
                        raise CandidateError("task action must use the native operation/reply interface")
                    return ServiceAction.model_validate({
                        **action.model_dump(mode="json", exclude={"record_hash"}),
                        "call": self.last_call.model_dump(mode="json") if self.last_call else None})
                else:
                    raise CandidateError("unregistered task decision")
            raise CandidateError("P exhausted per-action host-step budget")
        except InfrastructureError as exc:
            self.failure = exc
            raise
        except (CandidateError, ValueError) as exc:
            self.failure = CandidateError(str(exc))
            raise self.failure


class UsamiAdapter:
    domain_id = "usami-commerce-v2"

    def __init__(self, tasks, root, *, model=None):
        from pathlib import Path
        self.tasks, self.root, self.model = dict(tasks), Path(root), model
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs = {}

    def capabilities(self):
        return {"domain_id": self.domain_id, "tools": service_tools(),
                "feedback_protocol": "rsi-native-commerce-feedback-v1",
                "score": "native strict_task_success confirmed true; UNKNOWN stays unresolved",
                "observations": "authenticated identity, public Customer messages and native tool results"}

    def run_task(self, program, task_ref, models, ledger, worker, *, seed):
        import uuid
        if task_ref not in self.tasks:
            raise ValueError("unknown trusted task reference")
        native = self.tasks[task_ref]
        if ledger.remaining("tool_steps") < 1:
            raise CandidateError("no remaining native tool budget")
        budget = EpisodeBudget.model_validate({
            **native.budget.model_dump(mode="json", exclude={"record_hash"}),
            "max_service_tool_calls": min(native.budget.max_service_tool_calls, int(ledger.remaining("tool_steps"))),
            "max_model_calls": min(native.budget.max_model_calls, int(ledger.remaining("model_calls")))})
        service = ProgramServiceAgent(program, worker, self.model, models, ledger, seed)
        record = run_episode(native.world, native.task, native.customer_profile,
                             native.customer_factory(), service, budget=budget,
                             mode=native.mode, external_events=native.external_events)
        ledger.charge("environment", tool_steps=len(record.tool_executions))
        run_ref = uuid.uuid4().hex
        path = self.root / (run_ref + ".json")
        save_episode(record, path)
        self.runs[run_ref] = path
        (self.root / (run_ref + ".public-inputs.json")).write_text(canonical({
            "program_ref": program.ref, "seed": seed, "inputs": service.inputs,
            "model_events": service.model_events}), encoding="utf-8")
        if isinstance(service.failure, InfrastructureError):
            raise InfrastructureError(str(service.failure) + "; native episode retained at " + str(path))
        if record.model_calls and record.total_tokens is None:
            raise InfrastructureError("native model usage is incomplete; retained episode " + str(path))
        if record.status in {"runner_error", "customer_protocol_error", "cancelled"}:
            raise InfrastructureError("native environment/Customer failure: " + record.terminal_reason
                                      + "; retained episode " + str(path))
        replay = replay_episode(record)
        if not replay.verified:
            raise InfrastructureError("native Replay failed")
        outcome = record.outcome
        unresolved = outcome.evaluation_status != "VERIFIED"
        status = "CANDIDATE_FAILED" if service.failure else "UNKNOWN" if unresolved else "VERIFIED"
        score = float(outcome.strict_task_success is True) if status == "VERIFIED" else 0.0
        classifications = [op["classification"] for row in record.tool_executions for op in row.oracle["operations"]]
        forbidden = outcome.safety_violations.status == "FAIL" or any(
            code in {"authorization_only", "successful_business_violation"} for code in classifications)
        return TaskResult(run_ref, score, status, True,
                          tool_steps=len(record.tool_executions), model_calls=len(service.model_events),
                          model_tokens=sum(row["prompt_tokens"] + row["completion_tokens"]
                                           for row in service.model_events),
                          feedback={"outcome": outcome.model_dump(mode="json"),
                                    "operations": [{"operation": row.operation, "result": row.result,
                                                    "oracle": row.oracle} for row in record.tool_executions],
                                    "terminal_status": record.status, "terminal_reason": record.terminal_reason},
                          forbidden_behavior=forbidden)

    def replay(self, run_ref):
        path = self.runs[run_ref]
        return verify_episode_artifact(path)
