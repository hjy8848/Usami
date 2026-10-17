# Usami Benchmark vNext — active construction

This directory is not yet a complete eight-domain Benchmark release. All eight
native world/task runtimes are implemented; the balanced 320-task Pilot,
800-task Core and multi-domain Discovery remain unfinished. No model results
exist for this upgrade.

Current evidence:

- `audits/worlds-phase1/`: original 400-world attempt, exit 1; four real native StayOps consistency failures, full traces and exact source snapshot retained.
- `audits/worlds-phase1-corrected/`: separate corrected distribution audit, exit 0; four existing domains × 100 valid initial worlds, native generation provenance and explicit exclusions.
- `audits/worlds-phase1-final/`: current isolated namespace, 400 valid frozen worlds; all world contents match the corrected distribution before relocation.
- `audits/namespace-migration-verification.json`: actual 400/400 equality verification.
- `verification/legacy-generator-baseline.json`: source/seed hashes pinned to the pre-upgrade commit.
- `verification/logs/`: actual executed test/audit output. Initial Python 3.9 annotation collection error retained; corrected primitive tests use compatible Optional annotations.
- `verification/environment.json`: actual interpreter and dependency versions.

Task coverage fields in the original world-only audits deliberately remain
`NOT RUN`; new task audits are separate artifacts rather than retroactive edits.
Structural diversity does not demonstrate model generalization. See
`docs/benchmark-vnext/IMPLEMENTATION_REPORT.md` for active remaining work.

Education checkpoint: all eight independent world generators are executable.
Four dialogue domains have native rules, mutations, scoped queries, frozen
Customer profiles, task proofs and Replay. See `examples/education-native-001/`,
`audits/dialogue-state-v2-001/` and the 1153-test full regression log. These are
engineering verification artifacts, not real-model results. The 320/800 task
releases, complete coverage/leakage and eight-domain Discovery integration are
still in progress; this directory is not yet the complete vNext release.

The unified compiler/runner now supports native task certification and exact
episode Replay for all eight domains. `audits/tasks-eight-domain-001/` adds eight
source-pinned native task examples and an evidence-derived coverage matrix with
actual shortfalls. It is an engineering sample, not the Pilot/Core dataset.
Task audit reports distinguish world, rooted task and coarse decision groups;
one-partition examples do not claim split isolation. See
`docs/benchmark-vnext/COVERAGE_TAXONOMY.md` for the offline `audit-tasks` command.
