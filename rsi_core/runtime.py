"""Fixed Host for MODEL/STAGE/PROBE/SUBMIT; candidates control only decisions."""
from dataclasses import asdict, dataclass
import json
import uuid

from .archive import chain, verify_chain
from .programs import ProgramArtifact
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

    def run(self, editor, target, mode, public_view, probes, probe, *, scope="root", seed=0):
        if editor.kind != "M" or mode not in {"SELF_EDIT", "ADAPT_TASK"}:
            raise ValueError("invalid trusted research context")
        if target.kind != ("M" if mode == "SELF_EDIT" else "P"):
            raise ValueError("target kind differs from Host-assigned mode")
        self.store.save(editor)
        self.store.save(target)
        run_id = uuid.uuid4().hex
        view = json.loads(canonical(public_view))
        if set(view) & {"target", "mode", "observations", "capabilities", "model_snapshot_refs"}:
            raise ValueError("caller public view overrides fixed Host fields")
        allowed_probes = tuple(probes)
        if len(set(allowed_probes)) != len(allowed_probes):
            raise ValueError("duplicate probe handles")
        view.update({"mode": mode, "target": {**asdict(target), "ref": target.ref},
                     "capabilities": {"stage_kind": target.kind, "probe_refs": allowed_probes,
                                      "max_candidates": self.max_candidates,
                                      "freeze_candidates_after_first_probe": True},
                     "model_snapshot_refs": asdict(self.models), "observations": []})
        state, events, candidates, staged, frozen = {}, [], {}, 0, False
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
                    _fields(output, ("action", "state", "kind", "source", "parent_ref"))
                    if frozen:
                        raise CandidateError("candidate set was frozen by the first PROBE")
                    if staged >= self.max_candidates:
                        raise CandidateError("candidate stage budget exhausted")
                    staged += 1  # Invalid syntax still consumes a stage attempt.
                    if output["kind"] != target.kind or output["parent_ref"] != target.ref:
                        raise CapabilityViolation("candidate role/parent escapes the fixed target")
                    try:
                        child = ProgramArtifact(output["kind"], output["source"], target.ref)
                        child.check(self.worker.limits.source_bytes)
                    except CandidateError as exc:
                        feedback = {"kind": "STAGE", "status": "INVALID", "reason": str(exc)}
                    else:
                        ref = self.store.save(child)
                        candidates[ref] = child
                        feedback = {"kind": "STAGE", "status": "VALID", "candidate_ref": ref}
                elif action == "PROBE":
                    _fields(output, ("action", "state", "candidate_ref", "probe_ref"))
                    frozen = True
                    ref = output["candidate_ref"]
                    if ref != target.ref and ref not in candidates:
                        raise CandidateError("PROBE must reference this run's registered candidate or parent")
                    if output["probe_ref"] not in allowed_probes:
                        raise CapabilityViolation("PROBE references an unavailable or private experiment")
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
                    status = "NOOP" if ref == target.ref or candidates[ref].source == target.source else "SUBMITTED"
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
