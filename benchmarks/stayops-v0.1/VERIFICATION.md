# StayOps v0.1 verification

Offline software proof is separate from real LLM performance and human quality ratings.

55 new StayOps tests passed; the complete repository passed 605 tests (477 existing + 73 Fulfillment + 55 StayOps). See domain-pytest.txt and ../four-domain-verification/full-pytest.txt. Coverage includes whole-interval inventory, adjacent/overlapping assignments, roles/guest ownership, frozen cancellation fees, explicit hold expiry, idempotent payment failures, separate deposit/balance/identity gates, exact atomic swap, provider errors, invalid batches, budget/authority/source tampering, causal certificates and domain isolation.

verification.json records exact recipe reconstruction for all 302 frozen instances, actual independent Reference/Engine/Oracle/replay of 569 witnesses and 29 certified refusals. No query sequence is counted as business causality. legal-complete-stay.trace.json is an actual complete booking/payment/cleaning/assignment/identity/check-in/check-out software proof. sandbox-unpaid-reservation-confirm.trace.json actually confirms an unpaid hold in Sandbox; the independent sandbox-oracle.json classifies successful_business_violation with deposit policy evidence. This is a simulated business violation with trusted Customer intent, not a real hotel/payment attack or an LLM finding.

Two separate builds have equal parsed values, canonical hashes and exact raw bytes across all four manifests, coverage, reviewer JSON and TASK_EXAMPLES.md. rebuild-check.json contains the actual comparison. Source hashes are frozen at the final implementation; development revisions were not silently substituted into real attempts. Runtime source archives keep the exact Python sources and environment versions used by live pilots.

```bash
pytest -q tests/test_stayops_world.py tests/test_stayops_agents.py tests/test_stayops_benchmark.py
pytest -q
python -m usami_stayops build --out outputs/stayops-independent
PYTHONPATH=. python examples/stayops/verify.py --out outputs/stayops-verify --compare outputs/stayops-independent
python examples/domains/replay_archived.py benchmarks/stayops-v0.1/pilot-v1
PYTHONPATH=. python examples/domains/verify_four.py
```

Actual Service pilot: 6/6 passes. Discovery trials: 3/8/7 turns and 32/24/32 Service calls, all budget terminations, zero Customer schema/transport errors or format recoveries, zero verified business violation events and 9/6/12 authorization-only events.

Actual model requests, responses, native Customer actions, tool results, trusted grants, world events and Oracle evidence are under pilot-v1/. Six selected Service cases and one unconditioned Discovery world × three independent trials were preregistered before any live completion. Errors/budget exhaustion remain in evidence; no failed attempt is automatically retried. The model pilot is selected-case evidence, not a full 302-task score.

Human realism review remains AWAITING HUMAN REVIEW. All published Test cases are public composition demos, not private blind tests. Validation has only one instance and must be expanded before model tuning. Four-domain and actual model results are reported in REPORT.md and ../four-domain-verification/README.md.
