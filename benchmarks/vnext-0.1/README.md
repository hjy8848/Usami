# Usami Benchmark vNext — active construction

This directory is not yet a complete eight-domain Benchmark release. The requested four new dialogue domains, 320-task Pilot, 800-task Core and multi-domain Discovery are still under implementation. No model results exist.

Current evidence:

- `audits/worlds-phase1/`: original 400-world attempt, exit 1; four real native StayOps consistency failures, full traces and exact source snapshot retained.
- `audits/worlds-phase1-corrected/`: separate corrected distribution audit, exit 0; four existing domains × 100 valid initial worlds, native generation provenance and explicit exclusions.
- `audits/worlds-phase1-final/`: current isolated namespace, 400 valid frozen worlds; all world contents match the corrected distribution before relocation.
- `audits/namespace-migration-verification.json`: actual 400/400 equality verification.
- `verification/legacy-generator-baseline.json`: source/seed hashes pinned to the pre-upgrade commit.
- `verification/logs/`: actual executed test/audit output. Initial Python 3.9 annotation collection error retained; corrected primitive tests use compatible Optional annotations.
- `verification/environment.json`: actual interpreter and dependency versions.

Task coverage fields deliberately remain NOT RUN until task certification is implemented. Structural diversity does not demonstrate model generalization. See `docs/benchmark-vnext/IMPLEMENTATION_REPORT.md` for active remaining work.
