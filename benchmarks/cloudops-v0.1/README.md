# Usami CloudOps v0.1

Enterprise Cloud Resource Management is an independent executable domain. Its schema, Reference specification, actual mutations, Oracle, goals, tools and events live in `usami_cloudops/`. SaaS remains `python -m usami`; CloudOps is `python -m usami_cloudops` or `usami-cloudops`. Both share the existing OpenAI-compatible transport and validated message protocol. No real cloud or payment service is contacted.

The release contains 45 fixed Service tasks (27 train / 9 validation / 9 public test-demo), 12 anonymous structures, and 2 unconditioned Discovery worlds × 3 trials. Public test-demo is not a private blind test. See [business rules](BUSINESS_MODEL.md), [quality audit](QUALITY_AUDIT.md), [verification](VERIFICATION.md), and [18 review examples](TASK_EXAMPLES.md).

## Install and inspect

Run from the repository root, using Python 3.9+:

```bash
python -m pip install -e '.[service,dev]' -c constraints-tested.txt
python -m usami_cloudops generate --seed 42 --out outputs/cloudops-world.json
python -m usami_cloudops inspect outputs/cloudops-world.json
python -m usami_cloudops validate --manifest benchmarks/cloudops-v0.1/service-validation.json
```

Generated worlds have a frozen clock, five users, two organizations and four projects. Seed changes fictional labels; size variants in the fixed Service dataset are not counted as new structures. Full worlds are host-side artifacts; LLMs receive scoped queries/observations, never the full file.

## Real Service and autonomous Customer

Configure `USAMI_LLM_MODEL`, `USAMI_LLM_BASE_URL` and `USAMI_LLM_API_KEY` in your local environment. On macOS, `USAMI_LLM_KEYCHAIN_SERVICE` and `USAMI_LLM_KEYCHAIN_ACCOUNT` can resolve an existing Keychain entry instead. Never put credentials in manifests. Roles can override these with `USAMI_SERVICE_LLM_*` / `USAMI_CUSTOMER_LLM_*`. `USAMI_LLM_OPTIONS` is a JSON object containing model options such as temperature and max_tokens. Customer uses strict JSON output; the provider must support the frozen settings and function calling for Service. Customer requests omit empty API function-tool fields; its prompt publishes complete per-write parameter schemas and send/stop action constraints.

```bash
# Freeze actual models/settings before the first model request.
python -m usami_cloudops profile --manifest benchmarks/cloudops-v0.1/service-validation.json --out outputs/cloudops-service-profile.json
python -m usami_cloudops run-suite --manifest outputs/cloudops-service-profile.json --out outputs/cloudops-service-runs

# Completely open exploration: no task, family, witness or attack script.
python -m usami_cloudops profile --manifest benchmarks/cloudops-v0.1/discovery-demo.json --out outputs/cloudops-discovery-profile.json
python -m usami_cloudops run-suite --manifest outputs/cloudops-discovery-profile.json --out outputs/cloudops-discovery-runs
```

Bundled release manifests use explicitly offline placeholder settings; `profile` binds real settings without changing the task data. Discovery defaults to Sandbox for writes; queries remain permission checked. Identity is fixed, exact structured Customer intents establish authority before Service runs, and state persists across turns. Each new trial starts at the frozen initial world. Final evidence contains both conversations, requests, arguments, results, state snapshots, authorization dispositions, termination and Oracle output.

For a small preregistered live demonstration:

```bash
python examples/cloudops/pilot.py --release benchmarks/cloudops-v0.1 --out outputs/cloudops-live-pilot
```

This binds both profiles before calls: three selected Service cases and one open Discovery world × three trials. It is not a full benchmark score. Provider failures and budget exhaustion stay in the records; they are not replaced by retries.

## Score, replay, reset and compare

```bash
python -m usami_cloudops run --manifest outputs/cloudops-service-profile.json --out outputs/cloudops-one.run.json
python -m usami_cloudops evaluate outputs/cloudops-one.run.json --manifest outputs/cloudops-service-profile.json
python -m usami_cloudops replay outputs/cloudops-one.run.json --manifest outputs/cloudops-service-profile.json
python -m usami_cloudops replay benchmarks/cloudops-v0.1/legal-billing-recovery.trace.json
python -m usami_cloudops evaluate benchmarks/cloudops-v0.1/sandbox-dependency.trace.json
```

Run evidence requires the external frozen manifest, not a configuration supplied inside the evidence itself. Replay uses recorded completions, compares every model request, rebuilds customer observations/intents and actual Engine events, and checks terminal equality. It makes no network calls. Raw traces are local software examples; their self-contained request events are not independently authenticated customer credentials.

`ServiceSession.reset()`, `InteractionSession.reset()` and `Engine.reset()` return to the frozen initial state. Existing run-suite files are replayed before aggregation. Atomic journals prevent silent retries of incomplete attempts. Full-suite rates appear only when all preregistered instance × trial rows exist; partial reports keep the missing rows and null aggregate rates.

For strategy comparisons, freeze a different Customer model or optional **general exploration method** with `profile --strategy '...'`. Do not encode a fixed task, family or witness in a Discovery strategy. `benchmark.assert_comparable(a, b)` requires the same world, identity, victim Service/settings, tools, mode, budgets, source pins and trials; Customer and general method may vary. `InteractionConfig.comparison_hash()` supports the same comparison at Python level.

## Deterministic software verification

```bash
python examples/cloudops/verify.py --release benchmarks/cloudops-v0.1 --out outputs/cloudops-verification
python -m usami_cloudops freeze --out outputs/cloudops-rebuilt
pytest -q
```

`reference-proof` reads privileged witnesses and `one-step` reads privileged goals. They verify software and scoring, not autonomous LLM performance. Discovery StopCustomer fixtures check the protocol only. Real model evidence is separately labeled in `pilot-report.json`.

Every manifest fixes domain/version, complete world and hash, identity, tools, mode, budgets, trials, models/settings and source hashes. Service also fixes natural-language request, declarative terminal Goal, preservation frame and finite unordered Customer-approved write choices. Witnesses and refusal certificates remain host-side. Discovery fixes none of those task fields. The complete shared Python runtime is pinned without rewriting SaaS manifests. A future code change must use a new release/profile or reproduce this release at its original Git commit.

## Python extension points

`generator.generate_world(seed)` → `service.Experiment` → `ServiceSession.respond(message, exact_intents)` → `finish()` provides the independent Service path. `customer.CustomerAgent` / `Action` / `IntentAdapter` / `InteractionSession` provide autonomous multi-turn exploration. `benchmark.run_instance`, `score`, `summarize`, `replay_run`, `assert_comparable` and `suite.run_suite` expose frozen experiments, complete evidence and fair comparison. Customer strategies need only replace the Customer completion client or its general method; no Evolver or training loop is implemented.
