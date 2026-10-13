# FulfillmentOps v0.1

Independent executable business domain in `usami_fulfillment`, with shared
domain-neutral execution/LLM protocols in `usami_harness`.

Two separate tracks:

- Service Task: frozen initial state, independent exact write intentions,
  declarative joint goal, protected frame, model/settings, tools and budgets.
  Internal certificates are never sent to Service. The Service chooses tools
  and operation order. Public test is a composition demo, never a blind test.
- Open Customer Discovery: an unconditioned generated world, fixed identity,
  victim Service/settings, tools, public policies, budgets and preregistered
  trials. No fixed task, family, attack script, goal or witness is supplied.
  Customer declares typed operation intentions before Service acts and sees only
  its scoped initial view plus actual Service replies.

```bash
python -m usami_fulfillment world --seed 42 --out /tmp/fulfillment-world.json
python -m usami_fulfillment build --out /tmp/fulfillment-rebuild
python -m usami_fulfillment verify benchmarks/fulfillment-v0.1/service-train.json
PYTHONPATH=. python examples/fulfillment/verify.py --out outputs/fulfillment-verification \
  --compare /tmp/fulfillment-rebuild
```

Install optional real transport with `pip install -e '.[service]'`. Configure
`USAMI_LLM_MODEL`, `USAMI_LLM_BASE_URL` and `USAMI_LLM_API_KEY` externally. macOS
Keychain is supported through `USAMI_LLM_KEYCHAIN_SERVICE` and
`USAMI_LLM_KEYCHAIN_ACCOUNT`. Do not put credentials in manifests or traces.
Optional `USAMI_SERVICE_LLM_*` and `USAMI_CUSTOMER_LLM_*` override role settings.
Customer uses native function calling; omit `response_format` in its options.

```bash
python -m usami_fulfillment profile benchmarks/fulfillment-v0.1/discovery-demo.json \
  --out /tmp/fulfillment-live.json
python -m usami_fulfillment run /tmp/fulfillment-live.json --out outputs/fulfillment-live
python -m usami_fulfillment replay /tmp/fulfillment-live.json /path/to/saved.run.json
PYTHONPATH=. python examples/fulfillment/pilot.py --out outputs/fulfillment-pilot
```

Every run is preregistered before the first provider call. Provider/protocol
errors and budget exhaustion are saved, rather than silently retried or removed.
Optional format recovery consumes a real Customer call and preserves the original
error; a retry must independently repeat exactly the same business intention.
Replay reconstructs both model request streams, independent customer intentions,
tool replies, actual events and final Oracle evaluation without network access.

See `coverage.json`, `QUALITY_AUDIT.md`, `VERIFICATION.md` and `pilot-report.json`
for measured evidence. Human business-quality ratings are **AWAITING HUMAN REVIEW**.
The two-domain project is incomplete until StayOps and cross-domain gates pass.

Original runtime replay without a live credential:

```bash
python examples/domains/replay_archived.py benchmarks/fulfillment-v0.1/pilot-v1
```

The helper verifies every archived source hash and reconstructs both selected Service and open Discovery reports, including failed attempts, with recorded model completions only.
