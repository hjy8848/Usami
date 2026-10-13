# Usami SaaS Benchmark v0.2.0

Usami supplies one executable SaaS world and two independent evaluation tracks. Service Tasks measure legal completion of fixed business goals and certified policy handling. Customer Discovery lets an autonomous Customer choose and adapt requests against a fixed Service. No frontend is required.

Registered user IDs and display names are public; emails are limited to authenticated profiles and accessible tenant rosters. The supported world includes organization isolation, owner/billing/member roles, pending/active/inactive memberships, administrator provisioning, suspension/removal, plan/seat capacity, subscription expiration/reactivation/renewal, linked 30-day invoices, simulated successful/failed payments with idempotency, and bounded partial-refund accounting. See [business rules](BUSINESS_MODEL.md), [measured report](REPORT.md), [quality audit](QUALITY_AUDIT.md) and [verification](VERIFICATION.md).

Public suite: 170 Train + 68 Validation + 40 Test Demo = 278 Service instances. Twenty-two workflow labels cover 21 business families: failed and unpaid restoration are branches of one family. Exact canonical structure/semantic counts are in `coverage.json`. Six Discovery worlds use three preregistered trials each. Public models are explicitly offline placeholders, not reported LLM performance. There is no published blind test or human quality rating.

Install from the repository root with Python 3.9+. The suite runner uses POSIX file locking (macOS/Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[service,dev]' -c constraints-tested.txt
pytest -q
```

Inspect a representative task without sending proof material to a model:

```bash
python - <<'PY'
import json
m=json.load(open('benchmarks/v0.2.0/service-test-demo.json'))
i=m['instances'][0]
print(i['instance_id'], i['customer_identity'])
print(i['task']['message'])
print(json.dumps(i['task']['goal'], indent=2))
PY
```

Rebuild and validate offline. Independent fresh processes must produce byte-identical JSON files:

```bash
python -m usami.benchmark freeze-release --out outputs/rebuild-a
python -m usami.benchmark freeze-release --out outputs/rebuild-b
diff -r outputs/rebuild-a outputs/rebuild-b
python -m usami.benchmark validate --manifest benchmarks/v0.2.0/service-test-demo.json
python examples/benchmark/verify_v2.py --release benchmarks/v0.2.0 --out outputs/verification
python examples/benchmark/render_review_v2.py --release benchmarks/v0.2.0
```

Configure an OpenAI-compatible Service through environment variables. The API key stays outside manifests and traces:

```bash
export USAMI_SERVICE_LLM_MODEL='YOUR_MODEL'
export USAMI_SERVICE_LLM_BASE_URL='https://YOUR_GATEWAY/v1'
export USAMI_SERVICE_LLM_API_KEY='YOUR_KEY'
export USAMI_SERVICE_LLM_OPTIONS='{"max_tokens":4096,"temperature":0}'
# Or use an existing macOS Keychain entry instead of API_KEY:
# unset USAMI_SERVICE_LLM_API_KEY
# export USAMI_SERVICE_LLM_KEYCHAIN_SERVICE='litellm'
# export USAMI_SERVICE_LLM_KEYCHAIN_ACCOUNT='litellm-api-key'
python -m usami.benchmark profile --manifest benchmarks/v0.2.0/service-test-demo.json --out outputs/service-profile.json
```

Run one selected instance, then score it offline:

```bash
INSTANCE=$(python -c "import json; print(json.load(open('outputs/service-profile.json'))['instances'][0]['instance_id'])")
python -m usami.benchmark run --manifest outputs/service-profile.json --instance "$INSTANCE" --out outputs/single.run.json
python -m usami.benchmark score --manifest outputs/service-profile.json --run outputs/single.run.json
```

Run the entire frozen suite, or resume the same directory after interruption. Existing evidence must pass exact replay; duplicates, corrupt records and different profiles are rejected. Provider errors remain recorded outcomes, not automatically rerun until a success is obtained. An unfinished attempt marker after abrupt process death blocks silent retry; preserve it and preregister a fresh experiment/trial:

```bash
python -m usami.benchmark run-suite --manifest outputs/service-profile.json --out outputs/service-runs
# Optional pilot limit: --max-runs 3. This produces an incomplete summary with null official rates.
python -m usami.benchmark summarize --manifest outputs/service-profile.json --runs outputs/service-runs/*.run.json
```

The summary reports legal completion for achievable tasks, correct refusal separately, overall task success, frame preservation, independent Oracle results, family/structure breakdowns, per-trial variation and budgets. An official aggregate requires every instance × trial. Final prose alone cannot complete a business goal. Certified refusal uses the external policy certificate, preserves the entire world and communicates the exact public policy code in the completed reply. A write probe and JSON formatting are optional; structured report compliance is a separate diagnostic. This measures operational policy handling and code communication, while explanation rhetoric and truthfulness are not subjectively judged.

Offline baselines are explicit:

```bash
python -m usami.benchmark run-suite --manifest benchmarks/v0.2.0/service-test-demo.json --out outputs/reference-check --baseline reference-proof
python -m usami.benchmark run-suite --manifest benchmarks/v0.2.0/service-test-demo.json --out outputs/one-step --baseline one-step
```

`reference-proof` reads evaluator witnesses and establishes software competence only. `one-step` is a privileged, non-LLM one-action baseline using evaluator state and goal predicates; it cannot plan prerequisite chains. Neither is an LLM score or a fair capability comparison.

Customer Discovery is separate. Configure `USAMI_CUSTOMER_LLM_MODEL`, `USAMI_CUSTOMER_LLM_BASE_URL` and Customer API key/Keychain; keep the victim Service settings fixed. A method may choose its own Customer model and natural-language strategy without changing dataset/instance identity:

```bash
python -m usami.benchmark profile --manifest benchmarks/v0.2.0/discovery-demo.json --out outputs/discovery-profile.json --strategy 'Explore business decisions and adapt to actual replies.'
python -m usami.benchmark run-suite --manifest outputs/discovery-profile.json --out outputs/discovery-runs
```

Only Oracle-confirmed successful business violations count. Blocked attempts, authorization-only anomalies, unscored states, unique findings and repeats are separate. The explicit permissive Sandbox is an experimental execution mode, not evidence of an exploitable real billing backend. Preregistered trials are repetitions; no provider sampling determinism is promised.

Run a stratified actual-model pilot, selecting one instance per workflow before any calls and one Discovery world across all three trials:

```bash
python examples/benchmark/pilot_v2.py --release benchmarks/v0.2.0 --out outputs/pilot
```

For a genuinely private test, choose fresh seeds locally and write only to ignored private paths:

```bash
python examples/benchmark/build_v2.py --private-seed-base 9000000 --out private/v0.2-test
```

Test Demo holds out compound membership–subscription–billing goals rather than changing only seeds. Underlying atomic goal skills and operations occur in Train. Validation is explicitly in-distribution on separate worlds. Exact leakage checks are in `coverage.json`.

Historical v0.1 manifests intentionally reject current source pins. Their data has not been rewritten. Reproduce from the exact original commit:

```bash
git worktree add ../Usami-v0.1 e9e1bb0470c577e02e34186089490f96550367a9
cd ../Usami-v0.1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[service,dev]' -c constraints-tested.txt
python examples/benchmark/verify_release.py
```

This release does not claim parity with τ-bench or τ²-bench. Ground truth is independently executable; human realism review is pending. Tax, credit wallets, mid-cycle proration and independently authenticated multi-party invitation acceptance are outside the implemented policy.

Published pilot journals can be scored without credentials:

```bash
python -m usami.benchmark summarize --manifest benchmarks/v0.2.0/pilot/service-profile.json --runs benchmarks/v0.2.0/pilot/service/*.run.json
python -m usami.benchmark summarize --manifest benchmarks/v0.2.0/pilot/discovery-profile.json --runs benchmarks/v0.2.0/pilot/discovery/*.run.json
```

The actual observations were re-evaluated after a scoring-only correction. The original profile hashes and original scoring source are retained. Reconstruct the original source by copying this release's `usami/` tree and replacing `usami/benchmark/scoring_v2.py` with `pilot/original-source/scoring_v2.before_fix.py.txt`; all other source hashes match. `replay_pilot_v2.py` accepts only that one source difference and requires identical complete model requests and executions. This is recorded-response re-evaluation, not additional provider calls or a claim of a full-suite model score.
