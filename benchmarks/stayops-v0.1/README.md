# StayOps v0.1

Standalone executable hotel domain with Service Task and open-ended Customer Discovery tracks. No frontend dependency.

```bash
python -m pip install -e '.[dev,service]' -c constraints-tested.txt
python -m usami_stayops world --seed 42 --out outputs/stayops-world.json
python -m usami_stayops verify benchmarks/stayops-v0.1/service-test-demo.json
python -m usami_stayops build --out outputs/stayops-rebuild
PYTHONPATH=. python examples/stayops/verify.py --out outputs/stayops-verification --compare outputs/stayops-rebuild
```

Real provider configuration uses environment variables; no credential belongs in a manifest or trace:

```bash
export USAMI_LLM_BASE_URL=http://10.130.138.46:8010/v1
export USAMI_LLM_MODEL=dashscope/qwen3.6-plus
export USAMI_LLM_KEYCHAIN_SERVICE=litellm
export USAMI_LLM_KEYCHAIN_ACCOUNT=litellm-api-key
export USAMI_LLM_OPTIONS='{"max_tokens":4096,"temperature":0}'
# Or supply USAMI_LLM_API_KEY locally. Role-specific USAMI_SERVICE_LLM_*
# and USAMI_CUSTOMER_LLM_* override the shared provider environment.
PYTHONPATH=. python examples/stayops/pilot.py --out outputs/stayops-new-pilot
```

The pilot script preregisters six different Service families and one unconditioned world × three trials before the first model call. Existing started attempts are never silently retried. To run a larger suite or a different Customer method, freeze a fresh profile:

```bash
python -m usami_stayops profile benchmarks/stayops-v0.1/discovery-demo.json --out outputs/stayops-profile.json
python -m usami_stayops run outputs/stayops-profile.json --out outputs/stayops-runs
python -m usami_stayops replay outputs/stayops-profile.json outputs/stayops-runs/stayops_world_59001_u0.r0.run.json
```

Reset means a new trial from the frozen initial world; state persists across turns within a trial. Replay reconstructs every model request, Customer intent, operation, result and whole state event without calling the provider. Runtime hashes and model settings are mandatory trusted external pins. Archived pilot sources preserve original-source replay if a later release changes runtime code.

Service tasks expose the natural-language request and finite approved operation choices, never goal predicates, witness order or Oracle answers. Customer Discovery exposes scoped initial observations, native `intend_<operation>`, `ask_service` and `stop_exploration`, plus actual Service replies. The Customer independently supplies exact single-use write intentions before Service runs. It receives no fixed goal/family/script or hidden Oracle feedback. A limited format recovery cannot change the declared intent and costs an actual model call.

Reusable Python interfaces: `usami_stayops.adapter`, `Engine`, `ServiceSession`, `CustomerSession`, `Manifest`, `run_instance`, `replay_run`, `score` and `assert_comparable`. The shared `usami_harness` handles transport, authorization, budgets and evidence, never hotel-specific state/rules. Future Customer algorithms may vary model/method while comparison pins freeze world, identity, victim Service, tools, budgets, source and trials.

See BUSINESS_MODEL.md, QUALITY_AUDIT.md, REPORT.md, VERIFICATION.md and the 55 stratified TASK_EXAMPLES.md cases. Public Test is a composition demo, not a private blind test. AWAITING HUMAN REVIEW.

Original runtime replay without a live credential:

```bash
python examples/domains/replay_archived.py benchmarks/stayops-v0.1/pilot-v1
```

The helper verifies every archived source hash and reconstructs both selected Service and open Discovery reports, including failed attempts, with recorded model completions only.
