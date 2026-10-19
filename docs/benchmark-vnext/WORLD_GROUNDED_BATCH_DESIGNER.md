# World-Grounded Single-Shot Batch Designer v1

This protocol runs beside `frozen-world-designer-exploration-v4`; it does not
change the v4 request, Replay, task, or certificate formats. The new protocol is
`world-grounded-batch-designer-v1` and currently has a native Grounder only for
After-sales.

The Designer receives a compact, ID-free domain catalogue and proposes one
batch of abstract challenges. A deterministic local Grounder matches symbolic
constraints to independently regenerated frozen worlds. Every grounded
proposal is then sent through the existing `compile_task()` path, which uses
the native Reference, Engine, Oracle, certificate, and `verify_task()` Replay.
The model proposes what to test; it does not select concrete IDs, native
frames, answers, or witnesses. Grounding success and native certification are
reported separately. No Service execution happens in this pipeline.

The private index is for evaluator-side matching only. Never attach
`grounding-index.json` to a Designer, Customer, or Service prompt. Catalogue
construction only accepts explicit `train` or `validation` partitions; it
rejects test/demo and held-out worlds.

## Build and inspect an index

```bash
python -m usami_benchmark.designer_batch build-index \
  --domain aftersales --seeds 0,1,2 --partition train \
  --output-dir /tmp/usami-batch-index
python -m usami_benchmark.designer_batch verify-index \
  --index /tmp/usami-batch-index/world-index.json
python -m usami_benchmark.designer_batch catalogue \
  --index /tmp/usami-batch-index/world-index.json --partition train \
  --output /tmp/usami-batch-index/catalogue.json
```

The index builder accepts a registered `WorldPool` and re-runs
`verified_world()` for each registration. The index commitment binds world
contents, source hashes, rules/generator versions, relationships, authenticated
profile scopes, and registered external events. It is private because it
contains the full frozen worlds and concrete IDs.

## Single-shot run and Replay

Configure the existing OpenAI-compatible client using
`USAMI_LLM_MODEL`, `USAMI_LLM_BASE_URL`, and either `USAMI_LLM_API_KEY` or the
existing Keychain variables. The default protocol performs one provider-call
attempt and never retries. It requests five candidates by default; the batch
can be set to 1–5. An optional, separately named one-revision protocol allows
at most two calls.

```bash
python -m usami_benchmark.designer_batch run \
  --index /tmp/usami-batch-index/world-index.json \
  --partition train --num-challenges 5 --online \
  --output-dir experiments/vast_coevo/results/world-grounded-batch-001
python -m usami_benchmark.designer_batch replay \
  --run-dir experiments/vast_coevo/results/world-grounded-batch-001
```

Offline transport/structured-output verification uses a response JSON file:

```bash
python -m usami_benchmark.designer_batch run \
  --index /tmp/usami-batch-index/world-index.json \
  --num-challenges 1 --scripted-response /path/to/openai-response.json \
  --output-dir /tmp/world-grounded-scripted
```

Scripted responses only test protocol behavior; they are not live-model
results. Runs archive the exact request and response, candidate attempts,
grounding sources, compilation outcomes, native certificates, usage, and Replay
status. Replay reconstructs the model request from the frozen catalogue and
protocol, reparses every raw response, reruns constraints and native proofs,
checks request/candidate/cost journals, and verifies each stored certificate.
Malformed and failed responses are retained; output directories are immutable.

## A/B/C proposal comparison

`experiments/vast_coevo/examples/compare_world_grounded_designer.py` compares:

* A: existing v4 Designer, run without exploration or revision so it uses one
  submission call;
* B: world-grounded batch Designer, using one batch call;
* C: a deterministic rule-combination sampling baseline, with zero LLM calls.

The strict call-budget comparison currently requires a one-world registered
pool so A and B see the same frozen world. The script records actual input and
output tokens; equal API-call count does not imply equal token cost. It
explicitly reports that token budgets are not matched in this mode. Use the
token-normalized measurements for cost accounting, not as a token-budget
controlled causal comparison. No task-generation certificate is evidence of
Service quality or of an evolutionary gain.

```bash
python -m usami_benchmark.designer_batch build-index \
  --domain aftersales --seeds 0 --partition train \
  --output-dir /tmp/usami-abc-index
python experiments/vast_coevo/examples/compare_world_grounded_designer.py \
  --index /tmp/usami-abc-index/world-index.json --online \
  --output-dir experiments/vast_coevo/results/world-grounded-abc-001
```

For an offline end-to-end comparison, pass both `--v4-response` and
`--batch-response` instead of `--online`. A successful comparison has zero
Service executions by design. It measures proposal, grounding, certification,
and local Reference cost only.

## Scope and limits

The index can preserve registered worlds for all eight domains, but this
protocol's symbolic schema and Grounder implement After-sales only. It currently
supports existing-line completion, created Case completion, correct `open_case`
refusal, mixed/multi-object goals, typed field constraints, fixed predicates,
same-identity constraints, and registered events. Other domains and native
operations return an explicit unsupported/scope result rather than a guessed
translation. Structural and semantic fingerprints omit concrete entity IDs.

The deterministic rule baseline is an internal grammar-combination baseline,
not an official reproduction of another system. No performance advantage is
assumed. A real-model run must report invalid schemas, no matches, bounded
Reference failures, costs, and Replay results as observed.
