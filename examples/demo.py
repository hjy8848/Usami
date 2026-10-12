"""Run with `python examples/demo.py`; all results come from the real engine/oracle."""
from pathlib import Path

from usami import (WorldEngine, evaluate_trace, generate_scenarios, generate_world, replay_trace,
                   reset_world, simulate_scenario)
from usami.evaluation.splits import create_manifest


def main():
    out = Path("outputs/demo")
    out.mkdir(parents=True, exist_ok=True)
    world = generate_world(42)
    (out / "world.json").write_text(world.model_dump_json(indent=2) + "\n")
    scenarios = generate_scenarios(world)
    dependent = next(s for s in scenarios if s.category == "multi_step_plan")
    (out / "scenario.json").write_text(dependent.model_dump_json(indent=2) + "\n")
    trace = simulate_scenario(world, dependent)
    trace.save(out / "trace.json")
    report = evaluate_trace(trace)
    assert report.status == "pass"
    assert replay_trace(trace).state.state_hash == trace.final_state_hash
    (out / "report.json").write_text(report.model_dump_json(indent=2) + "\n")
    engine = WorldEngine(world)
    for step in dependent.steps:
        req = step.request
        engine.register_request(req)
        engine.execute(req.requester_id, req.operation, req.request_id)
    assert engine.state == trace.final_state
    assert reset_world(engine) == world
    other = next(s for s in scenarios if s.category == "multi_step_refund")
    for step in other.steps:
        req = step.request
        engine.register_request(req)
        engine.execute(req.requester_id, req.operation, req.request_id)
    alternate = engine.finish()
    alternate.save(out / "alternate-trace.json")
    assert evaluate_trace(alternate).status == "pass"
    create_manifest("validation", [1000000, 1000001]).save(out / "validation-manifest.json")
    print(f"World: {world.world_id}, scenarios: {len(scenarios)}")
    print(f"Dependent sequence: {[s.expected_allowed for s in dependent.steps]}")
    print(f"Oracle: {report.status}; replay/reset: verified; alternate sequence: verified")
    print(f"Frozen validation manifest and traces: {out.resolve()}")


if __name__ == "__main__":
    main()
