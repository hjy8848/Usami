"""Fixed Host for MODEL/STAGE/PROBE/SUBMIT; candidates control only decisions."""
from dataclasses import asdict, dataclass
import json
import uuid

from .archive import chain, verify_chain
from .programs import ExperienceArtifact, ProgramArtifact, ServiceSnapshot
from .protocol import CapabilityViolation, CandidateError, FrozenModels, InfrastructureError, canonical, digest


@dataclass(frozen=True)
class ResearchResult:
    run_id: str
    editor_ref: str
    target_ref: str
    mode: str
    scope: str
    status: str
    submitted_ref: str
    candidates: tuple
    events: tuple
    error: str
    archive_ref: str
    forbidden_behavior: bool = False


def _fields(decision, names):
    if set(decision) != set(names):
        raise CandidateError("decision fields disagree with the fixed action contract")


class ResearchHost:
    def __init__(self, store, archive, worker, model, models: FrozenModels, ledger,
                 *, max_candidates=2, max_steps=32, max_output_tokens=2048):
        if not 1 <= max_candidates <= 2 or max_steps < 1 or max_output_tokens < 1:
            raise ValueError("invalid research protocol limits")
        self.store, self.archive, self.worker = store, archive, worker
        self.model, self.models, self.ledger = model, models, ledger
        self.max_candidates, self.max_steps = max_candidates, max_steps
        self.max_output_tokens = max_output_tokens

    def run(self, editor, target, mode, public_view, probes, probe, *, scope="root", seed=0,
            certify_challenge=None, run_baseline=None):
        if editor.kind != "M" or mode not in {
                "IMPROVE_SERVICE", "SELF_EDIT", "EVALUATE_ADAPT", "ADAPT_TASK"}:
            raise ValueError("invalid trusted research context")
        if mode == "SELF_EDIT" and target.kind != "M":
            raise ValueError("SELF_EDIT must target the research program M")
        if mode == "IMPROVE_SERVICE" and not isinstance(target, ServiceSnapshot):
            raise ValueError("IMPROVE_SERVICE must target a complete fixed-B/P/K Service snapshot")
        if mode == "EVALUATE_ADAPT" and (
                not isinstance(target, ServiceSnapshot) or not target.evaluation_only):
            raise ValueError("EVALUATE_ADAPT must target an evaluation-only Service copy")
        if mode == "ADAPT_TASK" and target.kind != "P":
            raise ValueError("legacy ADAPT_TASK must target a P program")
        if mode == "EVALUATE_ADAPT" and run_baseline is not None:
            raise ValueError("nested adaptation cannot publish baseline or challenge actions")
        if isinstance(target, ServiceSnapshot) and target.business_model_ref != self.models.business.ref:
            raise ValueError("Service snapshot changes the fixed business model B")
        self.store.save(editor)
        self.store.save(target)
        run_id = uuid.uuid4().hex
        view = json.loads(canonical(public_view))
        if set(view) & {"target", "mode", "observations", "capabilities", "model_snapshot_refs"}:
            raise ValueError("caller public view overrides fixed Host fields")
        allowed_probes = tuple(probes)
        if len(set(allowed_probes)) != len(allowed_probes):
            raise ValueError("duplicate probe handles")
        if isinstance(target, ServiceSnapshot):
            target_view = {"kind": target.kind, "ref": target.ref,
                           "business_model_ref": target.business_model_ref,
                           "policy": {**asdict(target.policy), "ref": target.policy.ref},
                           "experience_ref": target.experience_ref,
                           "experience": target.experience.value,
                           "parent_ref": target.parent_ref,
                           "evaluation_only": target.evaluation_only}
            stage_kind = "SERVICE_BUNDLE"
        else:
            target_view = {**asdict(target), "ref": target.ref}
            stage_kind = target.kind
        if mode == "IMPROVE_SERVICE" and (certify_challenge is None or run_baseline is None):
            raise ValueError("IMPROVE_SERVICE requires fixed challenge certification and baseline callbacks")
        view.update({"mode": mode, "target": target_view,
                     "capabilities": {"stage_kind": stage_kind, "probe_refs": allowed_probes,
                                      "challenge_refs": (),
                                      "max_candidates": self.max_candidates,
                                      "freeze_candidates_after_first_probe": True},
                     "model_snapshot_refs": asdict(self.models), "observations": []})
        state, events, candidates, staged, frozen = {}, [], {}, 0, False
        certified_challenges, baseline_refs = {}, set()
        status, submitted, error, forbidden = "FAILED", "", "", False
        try:
            for step in range(self.max_steps):
                self.ledger.charge(scope, research_steps=1)
                input_record = {"program_ref": editor.ref, "view": view, "state": state}
                output = self.worker.invoke(editor, view, state, self.ledger, scope)
                if not isinstance(output, dict) or not isinstance(output.get("state"), dict):
                    raise CandidateError("research step must return a decision and explicit object state")
                canonical(output)
                state = output["state"]
                action = output.get("action")
                events.append({"kind": "decision", "input": input_record, "output": output})
                if action == "MODEL":
                    _fields(output, ("action", "state", "request", "response_schema"))
                    if not isinstance(output["request"], dict) or not isinstance(output["response_schema"], dict):
                        raise CandidateError("MODEL request/schema must be objects")
                    from jsonschema import Draft202012Validator, SchemaError
                    try:
                        Draft202012Validator.check_schema(output["response_schema"])
                    except SchemaError as exc:
                        raise CandidateError("MODEL response schema is invalid: " + exc.message) from exc
                    if self.model is None:
                        raise InfrastructureError("research model is not configured")
                    if self.ledger.remaining("model_calls") < 1:
                        raise CandidateError("model call budget exhausted")
                    allowance = min(self.max_output_tokens, int(self.ledger.remaining("model_tokens")))
                    if allowance < 1:
                        raise CandidateError("model token budget exhausted")
                    request = {"request": output["request"], "response_schema": output["response_schema"]}
                    snapshot = self.models.behavior if scope == "root" else self.models.evaluator
                    self.ledger.charge(scope, model_calls=1)
                    completion = self.model.complete(snapshot, request, max_tokens=allowance, seed=seed + step)
                    self.ledger.charge(scope, model_tokens=completion.prompt_tokens + completion.completion_tokens)
                    events.append({"kind": "model", "scope": scope, "model_ref": snapshot.ref,
                                   "request": request, "completion": asdict(completion)})
                    problems = list(Draft202012Validator(output["response_schema"]).iter_errors(completion.output))
                    if problems:
                        raise CandidateError("model output violates candidate response schema: " + problems[0].message)
                    feedback = {"kind": "MODEL", "output": completion.output}
                elif action == "STAGE":
                    fields = (("action", "state", "kind", "policy_source", "experience", "parent_ref")
                              if isinstance(target, ServiceSnapshot) else
                              ("action", "state", "kind", "source", "parent_ref"))
                    _fields(output, fields)
                    if frozen:
                        raise CandidateError("candidate set was frozen by the first PROBE")
                    if staged >= self.max_candidates:
                        raise CandidateError("candidate stage budget exhausted")
                    staged += 1  # Invalid syntax still consumes a stage attempt.
                    if output["kind"] != stage_kind or output["parent_ref"] != target.ref:
                        raise CapabilityViolation("candidate role/parent escapes the fixed target")
                    try:
                        if isinstance(target, ServiceSnapshot):
                            policy = ProgramArtifact("P", output["policy_source"], target.policy.ref)
                            policy.check(self.worker.limits.source_bytes)
                            experience = ExperienceArtifact.from_value(output["experience"], target.experience.ref)
                            child = ServiceSnapshot(
                                target.business_model_ref, policy, experience, target.ref,
                                evaluation_only=(mode == "EVALUATE_ADAPT" or target.evaluation_only))
                        else:
                            child = ProgramArtifact(output["kind"], output["source"], target.ref)
                            child.check(self.worker.limits.source_bytes)
                    except (CandidateError, ValueError) as exc:
                        feedback = {"kind": "STAGE", "status": "INVALID", "reason": str(exc)}
                    else:
                        ref = self.store.save(child)
                        candidates[ref] = child
                        feedback = {"kind": "STAGE", "status": "VALID", "candidate_ref": ref}
                elif action == "PROPOSE_CHALLENGE":
                    _fields(output, ("action", "state", "proposal"))
                    if mode != "IMPROVE_SERVICE" or certify_challenge is None:
                        raise CapabilityViolation("challenge construction is unavailable in this research mode")
                    if not isinstance(output["proposal"], dict):
                        raise CandidateError("challenge proposal must be an object")
                    receipt = certify_challenge(output["proposal"])
                    if not isinstance(receipt, dict) or receipt.get("status") not in {
                            "CERTIFIED", "INVALID", "UNVERIFIED", "CAPABILITY_UNSUPPORTED"}:
                        raise InfrastructureError("fixed challenge certifier returned an invalid receipt")
                    event = {"kind": "challenge_certification", "proposal": output["proposal"],
                             "receipt": receipt}
                    events.append(event)
                    if receipt["status"] == "CERTIFIED":
                        required = ("task_ref", "certificate_ref", "certification_scope", "frozen")
                        if (any(not receipt.get(key) for key in required[:3])
                                or receipt.get("frozen") is not True):
                            raise InfrastructureError("certifier did not bind a frozen task and certificate")
                        task_ref = receipt["task_ref"]
                        if task_ref in certified_challenges:
                            raise CandidateError("a certified challenge reference may be registered only once")
                        certified_challenges[task_ref] = receipt
                        view["capabilities"]["challenge_refs"] = tuple(certified_challenges)
                        feedback = {"kind": "PROPOSE_CHALLENGE", "status": "CERTIFIED",
                                    "task_ref": receipt["task_ref"],
                                    "certification_scope": receipt["certification_scope"]}
                    else:
                        feedback = {"kind": "PROPOSE_CHALLENGE", "status": receipt["status"],
                                    "reason_code": receipt.get("reason_code", "")}
                elif action == "RUN_BASELINE":
                    _fields(output, ("action", "state", "task_ref"))
                    task_ref = output["task_ref"]
                    if mode != "IMPROVE_SERVICE" or run_baseline is None:
                        raise CapabilityViolation("baseline execution is unavailable in this research mode")
                    if staged:
                        raise CandidateError("RUN_BASELINE must precede candidate generation")
                    if task_ref not in certified_challenges:
                        raise CapabilityViolation("baseline must use a challenge certified in this root")
                    if task_ref in baseline_refs:
                        raise CandidateError("baseline already ran for this certified challenge")
                    result = run_baseline(target, task_ref)
                    if (not isinstance(result, dict) or result.get("service_ref") != target.ref
                            or result.get("task_ref") != task_ref
                            or result.get("replay_verified") is not True
                            or result.get("status") not in {"VERIFIED", "UNKNOWN", "CANDIDATE_FAILED"}):
                        raise InfrastructureError("fixed baseline runner returned an invalid observation")
                    canonical(result)
                    baseline_refs.add(task_ref)
                    events.append({"kind": "baseline_execution", "task_ref": task_ref,
                                   "service_ref": target.ref, "result": result})
                    feedback = {"kind": "RUN_BASELINE", "task_ref": task_ref, "result": result}
                elif action == "PROBE":
                    _fields(output, ("action", "state", "candidate_ref", "probe_ref"))
                    frozen = True
                    ref = output["candidate_ref"]
                    if ref != target.ref and ref not in candidates:
                        raise CandidateError("PROBE must reference this run's registered candidate or parent")
                    if output["probe_ref"] not in allowed_probes and output["probe_ref"] not in certified_challenges:
                        raise CapabilityViolation("PROBE references an unavailable or private experiment")
                    if (mode == "IMPROVE_SERVICE" and output["probe_ref"] in certified_challenges
                            and output["probe_ref"] not in baseline_refs):
                        raise CandidateError("certified challenge must be run on the parent before candidate probing")
                    candidate = target if ref == target.ref else candidates[ref]
                    result = probe(candidate, output["probe_ref"])
                    canonical(result)
                    feedback = {"kind": "PROBE", "candidate_ref": ref,
                                "probe_ref": output["probe_ref"], "result": result}
                elif action == "SUBMIT":
                    _fields(output, ("action", "state", "candidate_ref"))
                    ref = output["candidate_ref"]
                    if ref != target.ref and ref not in candidates:
                        raise CandidateError("SUBMIT must reference a registered version")
                    submitted = ref
                    unchanged = ref == target.ref
                    if not unchanged and isinstance(target, ServiceSnapshot):
                        child = candidates[ref]
                        unchanged = (child.policy.source == target.policy.source
                                     and child.experience.ref == target.experience.ref)
                    elif not unchanged and isinstance(target, ProgramArtifact):
                        unchanged = candidates[ref].source == target.source
                    status = "NOOP" if unchanged else "SUBMITTED"
                    if status == "NOOP":
                        submitted = target.ref
                    break
                else:
                    raise CandidateError("unregistered research action")
                events.append({"kind": "observation", "value": feedback})
                # Each iteration owns a new view; previously archived inputs
                # must not acquire observations from the future by aliasing.
                view = {**view, "observations": view["observations"] + [feedback]}
            else:
                raise CandidateError("research decision budget exhausted without SUBMIT")
        except CandidateError as exc:
            error = str(exc)
            status = "FAILED"
            forbidden = isinstance(exc, CapabilityViolation)
        except InfrastructureError as exc:
            error = str(exc)
            status = "INFRASTRUCTURE_FAILED"
        record = {"run_id": run_id, "editor_ref": editor.ref, "target_ref": target.ref,
                  "mode": mode, "scope": scope, "status": status, "submitted_ref": submitted,
                  "candidates": list(candidates), "stage_attempts": staged,
                  "models": asdict(self.models), "seed": seed,
                  "events": chain(events), "error": error, "forbidden_behavior": forbidden,
                  "consumption": self.ledger.snapshot()}
        ref = self.archive.save(record)
        if status == "INFRASTRUCTURE_FAILED":
            raise InfrastructureError(error + "; archived research run " + ref)
        return ResearchResult(run_id, editor.ref, target.ref, mode, scope, status,
                              submitted, tuple(candidates), tuple(record["events"]), error, ref, forbidden)

    def verify(self, result):
        saved = self.archive.load(result.archive_ref)
        verify_chain(saved["events"])
        for ref in [saved["editor_ref"], saved["target_ref"]] + saved["candidates"]:
            self.store.load(ref)
        if saved["submitted_ref"] and saved["submitted_ref"] not in saved["candidates"] + [saved["target_ref"]]:
            raise ValueError("unregistered archived submission")
        return {"verified": True, "run_id": saved["run_id"], "events": len(saved["events"]),
                "model_replay": "recorded responses; no stochastic API rerun"}
