"""Repeatable, zero-API protocol smoke. Arithmetic tasks are labelled fixtures."""
import argparse
from dataclasses import asdict
from pathlib import Path

from .archive import Archive
from .budget import Ledger
from .evaluation import Evaluator
from .fixtures import ArithmeticFixtureAdapter
from .isolation import DockerWorker
from .loop import recursive_run
from .programs import ProgramArtifact, ProgramStore
from .protocol import AdaptationPackage, FrozenModels, Limits, ModelSnapshot, canonical


def smoke(image, output):
    from .runtime import ResearchHost
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    limits = Limits(cpu_seconds=60, wall_seconds=180)
    snapshot = ModelSnapshot("offline-protocol-fixture", "no-model-parameters")
    store, archive = ProgramStore(root / "programs"), Archive(root / "archive")
    host = ResearchHost(store, archive, DockerWorker(image, limits), None,
                        FrozenModels(snapshot, snapshot, snapshot), Ledger(limits))
    p0 = ProgramArtifact("P", "def step(view,state):\n    return {'kind':'ANSWER','value':0,'state':{}}\n")
    store.save(p0)
    good_p = "def step(view,state):\n    return {'kind':'ANSWER','value':sum(view['numbers']),'state':{}}\n"
    # Handwritten successors test inheritance and failure semantics only.
    # They are not M0, model discoveries, warm-up data, or algorithm baselines.
    m1 = ProgramArtifact("M", "def next_step(view,state):\n"
        "    if view['mode']=='SELF_EDIT':\n"
        "        return {'action':'ILLEGAL_FIXTURE_DECISION','state':{}}\n"
        "    if not state:\n"
        "        return {'action':'STAGE','state':{'n':1},'kind':'P','source':" + repr(good_p)
        + ",'parent_ref':view['target']['ref']}\n"
        "    return {'action':'SUBMIT','state':{},'candidate_ref':view['observations'][-1]['candidate_ref']}\n")
    m0 = ProgramArtifact("M", "def next_step(view,state):\n"
        "    if view['mode']=='ADAPT_TASK':\n"
        "        return {'action':'SUBMIT','state':{},'candidate_ref':view['target']['ref']}\n"
        "    if not state:\n"
        "        return {'action':'STAGE','state':{'n':1},'kind':'M','source':" + repr(m1.source)
        + ",'parent_ref':view['target']['ref']}\n"
        "    return {'action':'SUBMIT','state':{},'candidate_ref':view['observations'][-1]['candidate_ref']}\n")
    packages, tasks = {}, {}
    for purpose in ("C_probe", "C_select"):
        tasks[purpose + "-probe"] = {"numbers": [2, 3]}
        tasks[purpose + "-query"] = {"numbers": [11, 5]}
        packages[purpose] = AdaptationPackage(purpose, ArithmeticFixtureAdapter.domain_id,
            purpose + "-family", purpose + "-lineage", "meta-train", purpose, p0.ref,
            (), (purpose + "-probe",), (purpose + "-query",), {})
    evaluator = Evaluator(host, ArithmeticFixtureAdapter(tasks, archive))
    result = recursive_run(host, evaluator, m0, (packages["C_probe"],), (packages["C_select"],))
    for row in result["history"]:
        trace = archive.load(row["root_trace_ref"])
        from .archive import verify_chain
        verify_chain(trace["events"])
    assert result["history"][0]["selection"]["decision"] == "ACCEPT"
    assert result["history"][1]["editor_ref"] == result["history"][0]["selected_ref"]
    assert result["history"][1]["selection"]["reasons"][0] == "CANDIDATE_FAILED"
    result.update({"fixture_only": True, "model_calls": 0, "model_tokens": 0,
                   "training_updates": 0, "costs": host.ledger.snapshot(),
                   "claim": "three-generation isolated execution, not trained RSI effectiveness"})
    (root / "summary.json").write_text(canonical(result) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Existing pinned Python image SHA256; never pulled")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = smoke(args.image, args.output)
    print(canonical({"output": str(Path(args.output).resolve()), "generations": result["generations"],
                     "decisions": [row["selection"]["decision"] for row in result["history"]],
                     "model_calls": 0, "training_updates": 0, "fixture_only": True}))


if __name__ == "__main__":
    main()
