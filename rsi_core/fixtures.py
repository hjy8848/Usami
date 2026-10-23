"""Explicit protocol fixtures, never empirical H1/H2/H3 benchmark evidence."""
from dataclasses import asdict

from .protocol import CandidateError, InfrastructureError, TaskResult, digest


class ArithmeticFixtureAdapter:
    domain_id = "arithmetic-protocol-fixture"

    def __init__(self, tasks, archive):
        self.tasks, self.archive = dict(tasks), archive

    def capabilities(self):
        return {"domain_id": self.domain_id, "fixture_only": True,
                "task_interface": "return kind=ANSWER, value=integer, state=object"}

    def run_task(self, program, task_ref, models, ledger, worker, *, seed):
        task = self.tasks[task_ref]
        public = {"numbers": list(task["numbers"]), "request": "Return their sum."}
        try:
            decision = worker.invoke(program, public, {}, ledger, "solver")
            if (not isinstance(decision, dict) or set(decision) != {"kind", "value", "state"}
                    or decision["kind"] != "ANSWER" or type(decision["value"]) is not int
                    or not isinstance(decision["state"], dict)):
                raise CandidateError("invalid fixture task answer")
            status, score, error = "VERIFIED", float(decision["value"] == sum(task["numbers"])), ""
        except CandidateError as exc:
            decision, status, score, error = None, "CANDIDATE_FAILED", 0.0, str(exc)
        record = {"fixture_only": True, "program_ref": program.ref, "public": public,
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
