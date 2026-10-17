# Reproducing native worlds, proofs and execution

All commands below run from the repository root using the project's Python
environment. Native proof construction and Replay require no network or API key.
Recorded/scripted model transport exercises real tools and native state, but is
not evidence of a model's business competence.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/test_vnext*.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m usami_benchmark.audit \
  --domains aftersales airline property education --count 100 --start-seed 10000 \
  --root /tmp/usami-new-dialogue-audit
```

Audit output directories must be new. Generation is pinned by domain,
generator/rules versions, seed and configuration; task selection cannot edit a
registered world. Full world content, anonymous grouping, source hashes and
compressed pool integrity accompany each audit. A world census does not prove
certified-task coverage.

## Source-pinned native examples

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m usami_dialogue verify-examples \
  benchmarks/vnext-0.1/examples/education-native-001
```

This command requires the exact archived runtime. Later source additions or
changes intentionally cause a source-pin failure. Do not edit a manifest or
rescore the old record to make it pass. Extract that example's
`source-snapshot.zip` into a new empty directory, verify its repository-relative
paths, then run the same command with the extracted directory as working
directory and `PYTHONPATH`, using an absolute artifact path. The archived source
includes the actual native domains, common dialogue infrastructure and their
local Python dependencies; use the project's existing installed dependencies.

Native task verification recomputes independent world generation, task scopes,
Reference/actual transitions, Oracle, objective goals, frames, interaction
counterfactuals and Replay. The private witness is host-side only, and is not the
path that a production Service must follow.

## Scripted agent journals

`verification/fixtures/education-agent-001/journal.json.gz` contains the initial
world, typed task-agent configuration, complete model requests/responses and
actual execution. Decode it with sorted JSON, validate `TaskRunConfig` and
`AgentExecution`, then call `usami_dialogue.agents.replay` with the native domain
adapter. Replay reconstructs exact model requests and actual tool execution,
without contacting a model. The source snapshot procedure above also applies.
The archived isolated-replay log verifies this on the exact recorded runtime.
Missing usage in fixtures remains unknown, even when stored primitive counters
are zero; see `usage_complete: false`. It is not a measured zero-token run.

## Compatibility and verification scope

Historical four-domain runtimes, manifests and experimental records remain
unchanged. New versions occupy separate packages/registrations. Native dialogue
model journals use v2 canonical prompt serialization; v1 journals require their
original archived runtime. World audit v2 separates current, latent and future
states; v1 archives retain their own schema and sources.

The education checkpoint's 1153-test full regression is recorded with exit 0.
Later changes require their own verification; this number is not a final-release
claim. Failed test/verification attempts remain in the logs with their actual
errors and are distinguished from later successful runs. No real LLM run or
Held-out evaluation is authorized or represented by these fixtures.
