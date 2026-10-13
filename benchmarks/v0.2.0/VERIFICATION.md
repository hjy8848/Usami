# v0.2 verification evidence

Status: **EXECUTED** — mandatory implementation and software criteria passed. Machine evidence: `acceptance.json`, `verification.json`, `build-comparison.json`, `coverage.json`, `coverage-details.json`, `pilot-report.json` and nine complete actual-observation journals under `pilot/`. External human ratings remain pending.

- Bound repository HEAD before edits: `e9e1bb0470c577e02e34186089490f96550367a9`; clean working tree, branch main.
- Independently confirmed baseline: 251 passing tests.
- Final complete regression: **414 passed in 47.85s**; original contracts plus operation boundaries, invariant failures, tenant substitution, fixed actors, parameter normalization, semantic/structural signatures, initial-goal scope, compatibility, replay tampering, budgets, model anomalies and safe suite resume.
- v0.1 archived exact commit independently tested: 251 passed; original frozen Train manifest validated, hash `bd865a4384cf6b7973abf1609cef3f73a5f75bfaaef93548fa0b1cbcfb045082`.
- Two fresh-process release builds: seven frozen JSON artifacts byte-identical; exact file SHA256 values in `build-comparison.json`.
- All 324 retained legal routes executed in the actual Engine; terminal goals and frames checked; independent Oracle and event replay agree.
- Full instance × trial coverage for both explicit offline baselines: 278 × 2 = 556 Service executions, all independently replayed and scored.
- Discovery protocol check: six worlds × three trials = 18 complete stop-only fixture replays. This is a software check, not an exploration result.
- Actual LiteLLM connectivity: Qwen3.6 Plus returned HTTP 200 and `OK`; API key read from local Keychain, never written to artifacts.

Executed reproducible commands (repository root):

```bash
.venv/bin/python -m pytest -q
.venv/bin/python examples/benchmark/build_v2.py --out outputs/build-a
.venv/bin/python examples/benchmark/build_v2.py --out outputs/build-b
diff -r outputs/build-a outputs/build-b
.venv/bin/python examples/benchmark/verify_v2.py --release benchmarks/v0.2.0 --out outputs/verification
.venv/bin/python examples/benchmark/render_review_v2.py --release benchmarks/v0.2.0
.venv/bin/python examples/benchmark/audit_release_v2.py --release benchmarks/v0.2.0
.venv/bin/python -m usami.benchmark validate --manifest benchmarks/v0.2.0/service-test-demo.json
.venv/bin/python -m usami.benchmark validate --manifest benchmarks/v0.2.0/discovery-demo.json
```

Actual model observation collection (provider configured in environment/Keychain):

```bash
python examples/benchmark/pilot_v2.py --release benchmarks/v0.2.0 --out outputs/service-pilot --families seat_activate,owner_refusal,failed_restore,partial_refund,renew_cycle,restore_upgrade_onboard --service-only
python examples/benchmark/discovery_pilot_v2.py --release benchmarks/v0.2.0 --out outputs/discovery-pilot
```

A pilot exposed a scoring issue: a correct natural-language Owner refusal was classified as unsuccessful solely because it lacked a JSON report or write probe. Before release, the business metric was corrected to use an independently proven policy constraint, preserved world and communicated public code; formatting remains diagnostic. Oracle and business rules were unchanged.

The published observations were re-evaluated after this **scoring-only** correction. `examples/benchmark/replay_pilot_v2.py` verifies the original source snapshot hashes, allows only `scoring_v2.py` to differ, and re-executes the actual LLM response journals while requiring byte-identical model requests and equal full executions/episodes. It does not claim any new provider calls. Original profile hashes and the sole changed original source file are retained under `pilot/`; all other original source hashes match the release source. Errors and all preregistered trials stay in the denominator.

Actual observations: Qwen3.6 Plus completed all five achievable Service cases and correctly handled the Owner policy case under the operational metric (six of six). The three Customer trials produced one unique, independently verified successful business violation; one Customer output error, one authorization-only anomaly and one unscored subsequent operation remain visible. Full release real-model scores are **not established**.

The violation was membership activation with no available seats in explicit Sandbox mode. Oracle evidence cites `NO_AVAILABLE_SEATS` and `SEATS_BELOW_MEMBERS`, with the actual before/after snapshots and event `event_000012`. This validates the discovery path and evidence classification, not an exploit against an external SaaS or hardened Reference backend.

Public structured review: 55 examples, no human ratings. Private test: specification and generator support only; public Demo is not a blind test. Explanation rhetoric and truthfulness are not evaluated by a subjective judge.
