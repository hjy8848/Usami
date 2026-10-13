# Four-domain regression and reproducibility

Workspace RSI (local identity a5514551195b), baseline main/729d825b9acddcb7d39f3e6e39763b4d69ae6c3b. The workspace_info connector failed internally during identity checks; the authorized local C2C registry independently confirmed the bound workspace name and root. No workspace identity was inferred from a folder name.

The final full repository test command `.venv/bin/pytest -q` passed 605 tests in 133.94 seconds: 477 existing tests, 73 new FulfillmentOps tests and 55 new StayOps tests. full-pytest.txt contains the actual output. New installed CLI entry points generate both worlds with zero invariant violations. Python 3.9.6/Pydantic 2.13.5/httpx 0.28.1 are recorded with each new live pilot.

Existing `usami/`, `usami_cloudops/`, `benchmarks/v0.2.0/` and `benchmarks/cloudops-v0.1/` remain byte-unchanged relative to the baseline. No historical source hash was rewritten. Historical CloudOps pre-schema, schema-stage and transport-failure attempts use retained original-source snapshots; cloudops-original-replays.txt records all 15 older attempts, including failures.

Each new domain separately exceeds the published quantity/causal targets using its actual certified dataset, with independent models/rules/appliers and a shared domain-neutral transport/authorization/evidence harness. Customer identity and authority precede Service tools. Four worlds cannot interchange typed states, operations or manifests. Each trial resets from its immutable initial state; turns persist within a trial. Source archives allow original-source replay across later code releases.

Run current published manifest and actual model evidence verification:

```bash
PYTHONPATH=. python examples/domains/verify_four.py
python examples/domains/replay_archived.py benchmarks/fulfillment-v0.1/pilot-v1
python examples/domains/replay_archived.py benchmarks/stayops-v0.1/pilot-v1
python examples/cloudops/replay_initial.py --evidence benchmarks/cloudops-v0.1/pilot-initial
python examples/cloudops/replay_initial.py --evidence benchmarks/cloudops-v0.1/pilot-schema
python examples/cloudops/replay_initial.py --evidence benchmarks/cloudops-v0.1/customer-comparison-before-transport-fix
```

The per-domain verification/rebuild-check files contain complete frozen recipe/witness/refusal checks and two independent dataset rebuilds. Fulfillment parsed JSON/canonical hashes match despite some dictionary presentation byte differences. StayOps matches both canonical data and raw bytes. These software results are not model performance or human realism scores.

For controlled Customer comparisons within each domain, freeze world, identity, Service model/settings, tools, source, budgets and trial list, and use assert_comparable. Change only Customer model/method. Across four domains, report results separately: their policies, typed action protocols and scenario sizes are not identical. Old CloudOps Customer protocol failures remain real outcomes and should be included as a baseline limitation, not silently repaired in old evidence.

Neither new domain implements Customer Evolver, training or automatic Service repair. Both allow open-ended adaptive requests without a fixed task/witness. All models see scoped observations and actual Service replies; privileged full-world/Oracle evidence is saved for offline auditors. Actual model pilots are small selected samples. Human realism review is AWAITING HUMAN REVIEW and public tests are demos. StayOps Validation has one instance and requires a larger later release for tuning/generalization estimates.

Final manifest/pilot gate: all four domains verified; 33 current published real runs exactly replayed (SaaS 9, CloudOps 6, FulfillmentOps 9, StayOps 9), plus the 15 historical CloudOps attempts above. Both new archived-source pilots reconstruct all nine original attempts and exact summaries without provider calls. See four-domain-final-verification.json/txt and the archived-replay logs.
