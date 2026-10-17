# Usami Benchmark vNext — implementation ledger

This is an active engineering ledger, not a completed release claim. The full request is the eight-domain upgrade dated 2026-10-17. No paid LLM run is authorized or required.

## Requirement trace

| Work package | Evidence required for completion | Current status |
| --- | --- | --- |
| Preserve four historical domains/releases | Old generator hashes, historical tests and Replay | Four legacy seed/source pins verified; old Web/native regression passed after namespace isolation |
| Three structural generators | 100 worlds each, native invariants, ID-neutral signatures, ≥30 meaningful structures or actual gap | Implemented under isolated vNext namespace; 100 valid audited worlds per existing domain; native StayOps consistency issue recorded |
| Four dialogue domains | Domain-specific rules/appliers, private Customer state, information/consent dependencies, proof and Replay | Pending |
| Eight-domain contracts and audit | Unified provenance, taxonomy, structural/permission/decision/task coverage | WorldSpec/FrozenWorld/pool/signatures and private dialogue reducer implemented; task/decision coverage pending |
| Pilot 320 / Core 800 | Frozen certified tasks, truthful counts, stratified coverage and leakage audit | Pending |
| Multi-domain Frozen Discovery | Real source-bound branches, fixed Customer, static-only inheritance and exact Replay | Existing CloudOps path inspected; expansion pending |
| Evaluation and ablations | Equal domain/track weights, immutable manifests, fixed budgets and offline validation | Pending |
| Full tests/docs/examples | Executed test logs, source pins and eleven requested documents | Phase-1 and primitive tests passed; final full regression 1069 passed; remaining documents pending |

## Architecture findings

The repository contains four real domains, with independent business rules and mutations. Fulfillment and StayOps share `usami_harness` Engine/Oracle/Service plumbing through explicit adapters. CloudOps has an older independent runtime; SaaS has versioned rules, generators and GoalServiceSession. Existing fixed manifests and experiment archives are not migration targets.

Current native CloudOps/Fulfillment/StayOps `generate_world()` fixtures mainly vary display labels. Their replacements must therefore be separate versioned generators, not silent changes to those fixtures. The structural generator version describes the distribution; native world schema/rules versions remain explicit and unchanged when business semantics are reused.

The latest Frozen-World training defaults to `explicit-selection-v2`, with quality scoring and both dynamic gates false. This remains mandatory for the new eight-domain training path. Independent Benchmark scoring is separate from training selection.

## Work remaining

All items labelled pending remain part of the active objective. Completing Phase 1 does not constitute completion of the eight-domain Benchmark.

## Checkpoint: structural generators and dialogue primitives

Implemented independent structural generator modules for CloudOps, Fulfillment and StayOps (currently `usami_benchmark/generators/<domain>.py`), plus strict WorldSpec registration, immutable multi-domain pools and ID-neutral graph signatures. No native legacy source file was changed.

The first audit attempted 400 worlds and exited 1 because four StayOps histories revealed a native Reference/invariant conflict. All original failure evidence and exact sources are retained. Corrected admissibility excludes invalid expected states only during independent initial-state generation; it does not alter Service execution. The second audit exited 0 and produced 100 valid worlds / 100 anonymous signatures per existing domain, with four explicit StayOps exclusions. Native simulator correction and per-task boundary coverage remain outstanding.

Executed checks so far: 113 generator/native-world regressions passed; 10 private fact/preference/consent protocol tests passed. The final complete repository regression passed 1069 tests in 500.95 seconds (exit 0). World-only audit fields for task proof, Reference boundary coverage and causal depth remain NOT RUN.

The full objective remains active: four complete native dialogue domains, 320/800 certified-task targets, eight-domain coverage/weighting and strict leakage audit, multi-domain Frozen Designer execution and full evidence/selection Replay are not yet implemented. No actual LLM experiment has run.

The first full regression stopped with 909 passed / 1 failed: historical Web loading pins every Python file in native domain directories. Adding a new generator there changed the expected runtime file set. New distributions were therefore relocated to `usami_benchmark/generators/`; historical verifiers and frozen manifests were not relaxed. The earlier audit source archives retain their original implementation locations for exact replay.


The final namespace-isolated 400-world audit exited 0. All 400 complete world hashes equal the corrected pre-relocation run. Verification: `audits/namespace-migration-verification.json`. Original source archives and both earlier audits remain intact. The 41-case new-generator/dialogue/Web compatibility regression passed after relocation.

Next engineering priority: implement a genuinely versioned correction/adapter for the known StayOps rule/invariant conflict without changing published native runtime files or weakening old source verification. Then complete After-sales end to end, validate objective multi-turn necessity, and extend the proven mechanism to Airline, Property and Education. The remaining dataset, coverage, evaluation and multi-domain VAST requirements are unchanged.


## Verified checkpoint result

- `pytest -q tests/test_vnext_generators.py tests/test_cloudops_world.py tests/test_fulfillment_world.py tests/test_stayops_world.py -x`: 113 passed, exit 0.
- Dialogue protocol primitives: 10 passed, exit 0; initial Python 3.9 annotation collection failure and correction are recorded.
- Post-isolation generator/dialogue/Web compatibility: 41 passed, exit 0.
- Final `pytest -q -x`: 1069 passed in 500.95 seconds, exit 0.
- Final four-domain world audit: 400/400 valid, exit 0, 100 anonymous structures/domain, exact namespace migration verified.
- All raw outputs are under `benchmarks/vnext-0.1/verification/logs/`.
- No existing tracked business code, old benchmark data or historical experiment has been modified. No real LLM experiment has run.

This is a committed engineering checkpoint, not completion of the user objective. The four new business domains, real dialogue Engine/Oracle/certificates, complete 320/800 task releases, capability/semantic leakage audits, equal-weight scoring and eight-domain VAST evidence/selection Replay remain mandatory active work.
