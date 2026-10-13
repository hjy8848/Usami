# Initial live attempts — preserved before public Customer schema repair

This directory retains all six original model runs and both profiles. Service passed all three selected cases. Customer trials ended `CUSTOMER_OUTPUT_INVALID` after 4, 0 and 4 actual Service turns respectively. No retry or model-result replacement occurred. All results remain in the complete original report.

The initial Customer prompt exposed a generic `params` dictionary but omitted per-operation schemas. The model omitted payment arguments in trials r0/r2 and placed a query inside write intents in r1. Strict validation correctly stopped the episodes. Valid preceding turns did change persistent state. The subsequent repair publishes required payment/quota/access/dependency/create inputs and restricts the public intent schema to writes; it changes no business rule, authority check, Oracle or scoring.

Final profiles have different source pins and are separate preregistered experiments, not retries inside these profiles. The exact initial Customer implementation is retained under `original-source/`; all other pinned Python sources are identical to the release. Replay the original evidence in an isolated temporary source snapshot:

```bash
python examples/cloudops/replay_initial.py --evidence benchmarks/cloudops-v0.1/pilot-initial
```

This validates the original source hashes, reconstructs both conversations and all actual Engine events, recomputes each score and requires the whole report to match. It makes no provider calls and does not modify the current checkout.
