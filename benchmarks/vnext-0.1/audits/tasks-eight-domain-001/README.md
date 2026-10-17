# Eight-domain native task audit — engineering checkpoint

This sample contains **8 certified tasks, not 320 Pilot tasks or 800 Core
tasks**. It is hand-selected, not an independent test split. Every input world
is independently generated and then frozen; no task edits that initial world.
No model, Reflection or Skill update was run. Model calls: **0**.

| Domain | Tasks | Outcome | Structural difficulty |
| --- | ---: | --- | --- |
| SaaS | 1 | completion | basic |
| CloudOps | 1 | completion | basic |
| FulfillmentOps | 1 | completion | basic |
| StayOps | 1 | completion | basic |
| After-sales | 1 | mixed completion/refusal | unclassified |
| Airline | 1 | mixed completion/refusal | unclassified |
| Property | 1 | mixed completion/refusal | unclassified |
| Education | 1 | mixed completion/refusal | unclassified |

The native witnesses contain 19 actual business writes in total. There are 115
trace-bound interaction counterfactual certificates. These are multiple facts,
preferences and consent checks in four dialogue tasks, **not 115 independent
tasks or discovered failures**. Oracle, business/process Replay and objective
frames pass for the recorded witnesses. Model capability is not measured.

## Files and verification

- `registration.json`: complete inputs and finite construction budgets, saved
  before task compilation. The generators do not receive those task goals.
- `completed-*.json`: actual task/record hash receipts for each certified case.
- `tasks/manifest.json` and `tasks/case-*.json.gz`: complete native task proofs.
- `audit/coverage.json`: evidence-backed capability matrix and honest gaps.
- `audit/registration.json`, `verification.json`: source archive commitment and
  actual audit result.
- Each stage includes exact runtime source pins and its source snapshot.
- `builder.py` and `builder-source.json`: the exact executed builder and SHA256;
  it is saved separately from the package-only runtime source archive.

Each domain is 39 tasks short of the nominal 40-task Pilot quantity. All cases
are train cases; split isolation is `NOT_TESTED_SINGLE_PARTITION`, with a null
isolation conclusion. No task or world is relabelled as Held-out.

This selection exercises scoped identity/requests and frames in all eight
domains, and actual refusal, mixed completion, information, preference and
consent evidence in the four dialogue cases. It does not supply dedicated time,
capacity, financial, entity-isolation, causal-alternative or commitment-revision
coverage. Those empty cells do not establish domain inapplicability. Dialogue
tasks remain unclassified rather than filling a difficulty quota from turn count.

To regenerate from the current matching checkout, use a **new** output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python \
  experiments/vast_coevo/examples/task_coverage_checkpoint.py --output NEW_CHECKPOINT
```

On the matching runtime:

```sh
.venv/bin/python -m usami_benchmark verify-archive \
  benchmarks/vnext-0.1/audits/tasks-eight-domain-001/tasks
.venv/bin/python -m usami_benchmark audit-tasks \
  benchmarks/vnext-0.1/audits/tasks-eight-domain-001/tasks \
  --output NEW_AUDIT --per-domain-target 40
```

Later source additions intentionally fail full source-set verification; extract
the saved runtime into a separate empty directory and use that as `PYTHONPATH`.
Use the absolute project virtualenv Python and the absolute saved `builder.py`
path to regenerate under that runtime; the extracted package archive does not
contain a virtualenv or the experiments directory.
The actual isolated-runtime verification is recorded in
`../../verification/logs/task-coverage-isolated-replay.log`. Its exit code is 0.
Historical artifacts have not been changed.
