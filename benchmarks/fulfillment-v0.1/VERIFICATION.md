# FulfillmentOps verification

Software evidence is separate from live-model results and human realism ratings.

The new World, Agent and Benchmark tests passed: **73 passed**. The complete
repository passed: **550 passed** (including 477 existing SaaS/CloudOps tests).
Logs are `outputs/fulfillment-final-pytest.txt` and
`outputs/two-domains-full-pytest-fulfillment.txt` in the development workspace.

`verification.json` records re-generation of all 338 frozen initial states,
665 independently executed witnesses and 26 refusal certificates. Every witness
was checked against independent Reference snapshots, actual Engine mutations,
Oracle, terminal goal/frame and complete event reconstruction. The legal complete
fulfillment/delivery/return/refund trace and an actual Sandbox unpaid confirmation
violation are in `outputs/fulfillment-final-verification/`.

Two independently built datasets have identical parsed JSON values and canonical
hashes, including manifests, coverage and reviewer examples. Some raw file bytes
differ only in dictionary key presentation order; this is recorded explicitly,
and is not claimed as byte-stable Markdown or JSON formatting.

SaaS historical manifests: 170 Train, 68 Validation, 40 Test Demo and six Discovery
worlds loaded without changing historical hashes; all nine current published
pilot runs replayed exactly. CloudOps: 27 Train, nine Validation, nine Test Demo,
two Discovery worlds and all six current published pilot runs verified. Old
SaaS/CloudOps runtime packages and frozen releases are byte-unchanged. Older
CloudOps attempts with earlier source pins keep their existing original-source
replay procedures. The detailed log is `outputs/four-domain-historical-verification.txt`.

```bash
pytest -q tests/test_fulfillment_world.py tests/test_fulfillment_agents.py tests/test_fulfillment_benchmark.py
pytest -q
python -m usami_fulfillment build --out /tmp/fulfillment-independent
PYTHONPATH=. python examples/fulfillment/review_sample.py /tmp/fulfillment-independent
PYTHONPATH=. python examples/fulfillment/verify.py --out outputs/fulfillment-verification
```

Live attempts are saved separately under `pilot-v1/`, with both profiles frozen
before provider calls. The earlier `pilot/` directory records a preflight source
pin invalidation before any model completion; it is retained and is not a model
failure or an omitted score. No incomplete attempt is silently retried.

Human realism/quality review is **AWAITING HUMAN REVIEW**. Final four-domain
evidence is published separately in ../four-domain-verification/.
