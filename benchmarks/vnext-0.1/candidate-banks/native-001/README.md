# Native candidate bank 001 — incomplete balanced release

This is a finite native construction run, with **zero model calls**. It is not
an autonomous Designer run, scored Agent benchmark or completed Pilot/Core.

- Eight independently generated train worlds, seed 314159.
- Full world pool frozen before enumerating any task.
- 16 preregistered candidates per domain: 128 total.
- Native proof bound: 128 search nodes, depth 12, one witness.
- 83 certified task records; 45 exact construction rejections retained.
- 65 tasks enter the requested strata; `quota_complete` is false.

| Domain | Basic | Medium | Complex | Pure refusal | Selected |
| --- | ---: | ---: | ---: | ---: | ---: |
| SaaS | 2 | 0 | 0 | 12 | 14 |
| CloudOps | 2 | 0 | 0 | 11 | 13 |
| FulfillmentOps | 1 | 0 | 0 | 12 | 13 |
| StayOps | 2 | 0 | 0 | 11 | 13 |
| After-sales | 0 | 0 | 0 | 0 | 0 |
| Airline | 0 | 0 | 0 | 3 | 3 |
| Property | 0 | 0 | 0 | 3 | 3 |
| Education | 0 | 0 | 0 | 6 | 6 |

Targets remain 8/12/8/12 per domain (40 total per domain). Dialogue tasks whose
necessary business difficulty is unproved are retained as certificates, not
silently labelled basic/medium/complex. No name or question alias fills another
rooted structure slot. This catalogue is sparse in necessary causal legal task
families and has no standalone After-sales refusal family. More world hashes
alone cannot repair those missing strata.

`plan.json`, `candidate-schedule.json` and `world-pool.json` were fixed before
proof execution. `attempts/` preserves every candidate result and rejection
reason. `records/` contains the full successful native certificates. Selection,
coverage, all shortfalls and content hashes are retained separately. Rejected
construction is not a Service error, and bounded search failure is not proof of
impossibility. All worlds are train worlds; no independent evaluation is claimed.

The build and full-bank reconstruction both exited 0. All 128 candidate outcomes,
including the 45 rejections, were independently rebuilt. The current-tree full
regression passed 1264 tests in 868.24 seconds, exit 0. Raw logs are under
`../../verification/logs/`; `verification.json` binds the actual rebuild receipt
to the exact runtime source pins. These results validate this checkpoint and do
not establish a completed Pilot/Core or model learning gain.

```sh
.venv/bin/python -m usami_benchmark verify-dataset \
  benchmarks/vnext-0.1/candidate-banks/native-001
```

Exact runtime sources are pinned and archived. Later source changes require
extracting this archived runtime into a separate directory and setting
`PYTHONPATH` to that directory. Do not rewrite manifests to make newer sources
pass verification.
