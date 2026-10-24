"""Explicit protocol fixtures, never empirical H1/H2/H3 benchmark evidence."""
from dataclasses import asdict

from .protocol import CandidateError, InfrastructureError, TaskResult, digest
from .programs import ServiceSnapshot


class ArithmeticFixtureAdapter:
    domain_id = "arithmetic-protocol-fixture"

    def __init__(self, tasks, archive):
        self.tasks, self.archive = dict(tasks), archive

    def capabilities(self):
        return {"domain_id": self.domain_id, "fixture_only": True,
                "feedback_protocol": "rsi-arithmetic-public-feedback-v0.2",
                "task_interface": "return kind=ANSWER, value=integer, state=object"}

    def research_feedback(self, result):
        return {"protocol": "rsi-arithmetic-public-feedback-v0.2",
                "run_ref": result.run_ref, "status": result.status,
                "score": result.score, "correct": result.feedback.get("correct"),
                "error": result.feedback.get("error", "")}

    def run_task(self, program, task_ref, models, ledger, worker, *, seed):
        task = self.tasks[task_ref]
        if isinstance(program, ServiceSnapshot):
            if program.business_model_ref != models.business.ref:
                raise CandidateError("Service snapshot does not use the fixed business model B")
            policy, experience = program.policy, program.experience.value
        else:
            policy, experience = program, {}
        public = {"numbers": list(task["numbers"]), "request": "Return their sum.",
                  "service_experience": experience}
        try:
            decision = worker.invoke(policy, public, {}, ledger, "solver")
            if (not isinstance(decision, dict) or set(decision) != {"kind", "value", "state"}
                    or decision["kind"] != "ANSWER" or type(decision["value"]) is not int
                    or not isinstance(decision["state"], dict)):
                raise CandidateError("invalid fixture task answer")
            status, score, error = "VERIFIED", float(decision["value"] == sum(task["numbers"])), ""
        except CandidateError as exc:
            decision, status, score, error = None, "CANDIDATE_FAILED", 0.0, str(exc)
        record = {"fixture_only": True, "program_ref": program.ref, "policy_ref": policy.ref,
                  "public": public,
                  "decision": decision, "status": status, "score": score, "error": error,
                  "models": asdict(models), "seed": seed}
        ref = self.archive.save(record)
        return TaskResult(ref, score, status, True, feedback={"correct": score == 1, "error": error})

    def replay(self, run_ref):
        record = self.archive.load(run_ref)
        if record["decision"] is not None:
            expected = float(record["decision"]["value"] == sum(record["public"]["numbers"]))
            if expected != record["score"]:
                raise InfrastructureError("fixture result does not match independent arithmetic")
        return {"verified": True, "fixture_only": True}
