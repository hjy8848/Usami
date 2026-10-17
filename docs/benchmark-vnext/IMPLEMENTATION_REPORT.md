# Usami Benchmark vNext — implementation ledger

This is an active engineering ledger, not a completed release claim. The full request is the eight-domain upgrade dated 2026-10-17. No paid LLM run is authorized or required.

## Requirement trace

| Work package | Evidence required for completion | Current status |
| --- | --- | --- |
| Preserve four historical domains/releases | Old generator hashes, historical tests and Replay | Four legacy seed/source pins verified; old Web/native regression passed after namespace isolation |
| Three structural generators | 100 worlds each, native invariants, ID-neutral signatures, ≥30 meaningful structures or actual gap | Implemented under isolated vNext namespace; 100 valid audited worlds per existing domain; native StayOps consistency issue recorded |
| Four dialogue domains | Domain-specific rules/appliers, private Customer state, information/consent dependencies, proof and Replay | After-sales and Airline native cores, shared runtime, task certificates and offline mixed/refusal examples implemented; domain breadth and Property/Education pending |
| Eight-domain contracts and audit | Unified provenance, taxonomy, structural/permission/decision/task coverage | WorldSpec/FrozenWorld/pool/signatures and private dialogue reducer implemented; task/decision coverage pending |
| Pilot 320 / Core 800 | Frozen certified tasks, truthful counts, stratified coverage and leakage audit | Pending |
| Multi-domain Frozen Discovery | Real source-bound branches, fixed Customer, static-only inheritance and exact Replay | Existing CloudOps path inspected; expansion pending |
| Evaluation and ablations | Equal domain/track weights, immutable manifests, fixed budgets and offline validation | Pending |
| Full tests/docs/examples | Executed test logs, source pins and eleven requested documents | Phase-1 full regression 1069 passed; later 49-case dialogue milestone passed; After-sales checkpoint full regression 1094 passed; remaining documents pending |

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


## Phase-2 checkpoint: native After-sales and executable dialogue

Implemented real order-line disputes, evidence verification, refund approval thresholds, original-channel settlement, replacement inventory, return pickup/receipt and duplicate-settlement boundaries. Reference expected mutations and actual mutations are separate. Manager and carrier outcomes are frozen simulator events; neither model can fabricate their outcomes. Service receives scoped observations, not private profiles or hidden simulator verification flags.

The shared dialogue runtime independently establishes Customer identity and exact requested writes, records actual quote presentation, validates truthful disclosures, revokes superseded consent and retains full business/process/external traces. A real OpenAI-compatible two-Agent runner journals exact requests, replies, tools, usage by role, budgets and bounded protocol recovery. Fixture tests use that same runner; no paid calls were made.

Native Reference search creates private reachability witnesses. Objective scoring accepts different legal outcomes/paths, enforces the domain frame and checks exact correct-refusal subgoals. Counterfactual certificates prove changes to actual Reference legality after removing facts/consent, changing allowed preferences, or receiving a frozen manager event. The mixed example completes a real remedy and refuses a duplicate request without invoking a forbidden write.

Initial added tests passed 49 cases before the serialization-roundtrip extension. CLI certification found a separate ordering issue on reloading sorted JSON: proof ordering depended on dictionary insertion order. The failed bundle/source archive and verification traceback are retained as `examples/aftersales-mixed-001/`. Proofs now have canonical content-hash ordering, a JSON-roundtrip assertion has been added, and `examples/aftersales-mixed-002/` certified and independently verified successfully. This is an offline native proof, not a model result.

World audits: `audits/aftersales-native-002/` contains 100/100 valid worlds, 100 anonymous structures and 99 ownership topologies. The first After-sales audit aborted due to a new scanner variable-shadowing error before any world registration; its source and traceback remain in `aftersales-native-001/`. A corrected new run was saved separately. `audits/stayops-v2-001/` contains 100/100 valid worlds and 100 structures/topologies under explicitly registered `stayops-structural-v2` / `stayops-0.2.0`. The old native StayOps rules remain untouched. Its versioned correction permits future assignments of a currently dirty unoccupied room while retaining current occupancy/cleanliness constraints.

### Still mandatory

- Finish After-sales domain breadth (including initial historical case distributions, richer account and cross-order scenarios) and comprehensive boundary/task audit.
- Implement distinct Airline, Property and Education native state machines and generators; do not copy the refund flow into renamed domains.
- Complete all eight native task composers, stratified Pilot/Core manifests, capability/depth/decision coverage, equal-weight scoring and semantic split/leakage audit.
- Complete cross-turn commitment/partial-completion dependency coverage beyond the present counterfactual and mixed-task examples.
- Extend Frozen Task Discovery and source-bound bidirectional evidence/Reflection/static-only version selection to eight domains.
- Finish all requested documents, datasets, final source-pinned verification and full release audit. The current work is not an eight-domain release.

### Offline example commands

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m usami_aftersales verify \
  --bundle benchmarks/vnext-0.1/examples/aftersales-mixed-002/bundle.json
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m usami_aftersales certify \
  --seed 1 --profile profile_u1_order0_line1 --mixed --resolution refund \
  --max-search-nodes 256 --max-paths 1 --output /tmp/usami-aftersales-new-certificate
```

Use a new output directory. Archived bundles contain exact sources and reject current source mismatches; if the runtime advances, use the corresponding archived source snapshot. Actual LLM execution is separately available via `python -m usami_aftersales run --online` with environment-configured models/credentials and frozen budgets. It is not invoked by certification or verification. Customer/Service-specific settings can override the shared environment via `USAMI_CUSTOMER_LLM_*` / `USAMI_SERVICE_LLM_*`. No key or HTTP authorization header is stored.


Full regression for the After-sales checkpoint finished with exit 0: **1094 passed in 508.69 seconds**. Raw log: `benchmarks/vnext-0.1/verification/logs/aftersales-checkpoint-full-1094.log`. This result predates the subsequent Airline implementation and cannot be used to claim validation of that later code.


## Phase-2 checkpoint: Airline and shared certified-task execution

Airline now has a distinct native ticketing model, independent expected/actual transitions, flight/cabin seat conservation, spatial and temporal connection constraints, passenger-document verification, voluntary fare restrictions versus airline cancellation, fee/refund computation, baggage limits, simulated payment capacity, current-quote consent, actual ledger accounting, scoped queries, frozen operational updates and full Replay.

The shared `usami_dialogue.planner` now handles private native Reference search for both implemented dialogue domains; it does not drive production Service decisions. Airline composers cover rebooking, refund, baggage, standalone policy refusal and appropriate mixed completion/duplicate refusal. Correct refusal certification uses a real unattempted Customer request and independently checked policy reason. Pure refusal frames preserve ticket and financial state while allowing the necessary identity-verification record.

A separate `business-dialogue-task-agents-v1` configuration binds the exact task, private certificate and witness before any paid model call. It derives a Customer-facing business request from domain-validated goals. Reference outcomes, policy refusal codes and witnesses remain host-side. The earlier `business-dialogue-agents-v1` config/journal shape is retained. The fixed Customer's weights and policy are unchanged; selected task goals guide what it wants, without changing its objective facts or revealing an answer. The After-sales online CLI now uses this certified task variant. No online invocation was performed.

Actual validation:

- `pytest -q tests/test_vnext*`: **69 passed in 44.03s**, exit 0. This includes the two native domains, original generator/StayOps tests, process/counterfactual/certificate checks, production Function Calling runner with explicitly scripted transport, exact model-request Replay, task goal isolation and rejection of invalid certification before any model call.
- Airline world audit: **100/100 valid**, **100 ID-neutral structures**, **97 ownership topologies**, no invalid worlds. Task-scale decision/depth/coverage measurements remain NOT RUN.
- Four archived Airline native examples: refund (mixed), rebook, baggage (mixed), standalone fare-refund refusal. All verified through independent Oracle and actual transition Replay.
- The entire example source snapshot was extracted to a fresh isolated directory. The four cases verified successfully using only that archived runtime (exit 0). This checks that Replay does not accidentally depend on the current checkout.
- The prior 1094-test full repository regression is the preceding After-sales checkpoint result, not a final validation claim for all subsequent work. A final full regression is still required for the full eight-domain release.

Artifacts: `audits/airline-native-001/`, `examples/airline-native-002/`, and `verification/logs/`. The earlier `airline-native-001` example is retained with its exact sources; the second example includes the later certified-task protocol and stricter pure-refusal frame. Neither is a model experiment. Source-pinned example verification intentionally rejects a modified runtime; use the corresponding archived source snapshot.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m usami_dialogue verify-examples \
  benchmarks/vnext-0.1/examples/airline-native-002
```

Remaining scope is unchanged: After-sales historical/account/cross-order expansion, complete Property and Education domains, all eight native task bindings and certified datasets, coverage/leakage/macro evaluation, fixed-Customer multi-domain Designer/Service Discovery and selection Replay, and final release verification. No paid LLM training, actual learning gain or cross-domain generalization has been demonstrated.
