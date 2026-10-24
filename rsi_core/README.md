# Executable RSI core v0.2

The fixed Host runs immutable Designer programs `M.next_step` and Service
policies `P.step` in isolated Docker workers. A Service version is an atomic
`(fixed B, P, K)` snapshot; a Designer version binds the research model `φ` to
program `M`. The Host keeps model/environment calls, task certification,
budgets, scoring, and publication outside candidate control.

The Service root mode is `IMPROVE_SERVICE`: M can propose a frozen-world task,
the Host certifies and runs it on the parent Service, M stages a complete P/K
candidate, and a candidate probe requires the parent baseline first. Direct
`service_probe`, `service_select`, and `service_reward` task sets are certified
and distinct from Designer self-edit adaptation packages (`C_probe`,
`C_select`, `C_reward`). `EVALUATE_ADAPT` creates evaluation-only P/K children
that cannot enter the main Service chain.

The Usami baseline and probe projections are versioned and include public
Service tool calls/results, strict task score/status, and an aggregate safety
flag. Oracle annotations and hidden task outcomes remain in the trusted
Episode/Replay artifact and are excluded from Designer-visible observations.

`rsi_core.period.run_period` runs K registered Service-improvement groups, then
one M self-edit group from the final accepted Service snapshot. It freezes
`φ`, B, evaluator, and sampling identities throughout those phases. An optional
period-end update hook receives the archived collection groups plus separate
`r_service` and `r_self` records with within-group GRPO advantages, so it can
call `export_verl_period` while φ is still frozen. It is called once after both
root types. Without that hook the record is `READY_FOR_TRAINING`; it does not
claim that the period has completed RL or changed parameters. A failed hook is
archived as `TRAINING_FAILED` and cannot publish a new φ snapshot.

```sh
pip install ./rsi_core
python -m rsi_core.smoke --image sha256:YOUR_REVIEWED_CACHED_PYTHON_IMAGE_DIGEST \
  --output /absolute/new/output-directory
```

The protocol smoke uses a cached image and arithmetic fixtures. It makes no
model calls and performs no parameter update. The Usami integration is separate
in `integrations/rsi_usami/` and reuses the native runtime, scorer, Oracle, and
Replay.

`training.py` validates root tokens, masks, behavior log-probabilities, reward
receipts, and group identity. It labels Service-improvement roots `r_service`
and M self-edit roots `r_self`; GRPO advantages reject mixing root types,
starting contexts, or frozen model snapshots.

`verl_backend.py` retains the optional verl 0.9.1 single-group exporter and adds
a period bundle exporter containing both root types, one uid per original GRPO
group, and explicit equal root-type/context loss weights. The weighted loss
field needs an RSI-aware verl loss hook; stock verl does not consume it. These
are data/configuration adapters only: verl has not been installed or run, no
model weights have been updated, and checkpoint identity has not been checked.
No training starts during import or export.

`packages.PackageProvider` registers adaptation packages with independently
verified certificates and no-replacement draws. `ServiceTaskProvider` uses a
separate registry for direct Service tasks and prevents task family/lineage
reuse across probe, selection, reward, and audit roles. Usami's native
certificate adapter is in `integrations/rsi_usami/packages.py`.

Implementation and verification boundaries are tracked in
`experiments/rsi/reports/IMPLEMENTATION_STATUS.zh.md`.
