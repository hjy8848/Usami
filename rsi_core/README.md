# Executable RSI core

The fixed Host runs immutable Python task programs (`P.step`) and researcher
programs (`M.next_step`) in isolated Docker workers. It implements
`MODEL / STAGE / PROBE / SUBMIT`, candidate-set freezing, nested `Adapt / F`,
private-query projection, paired selection, and frozen-model editor inheritance.
The package imports no Usami modules and can be built/installed independently.

```sh
pip install ./rsi_core
python -m rsi_core.smoke --image sha256:YOUR_REVIEWED_CACHED_PYTHON_IMAGE_DIGEST \
  --output /absolute/new/output-directory
```

The image must already exist. No image pull, API request or training occurs in
the protocol smoke. Fixtures verify execution contracts and are not learned
policies or scientific results. Usami integration lives separately in
`integrations/rsi_usami/` and uses the unchanged native runtime and scorer.

`training.py` currently exports validated root token/logprob/mask records and
group advantages. It does **not** implement or claim completed parameter RL.
`collection.collect_self_edit_group` executes independent roots under identical
phase allocations, reserves the entire group before sampling, selects on
`C_select`, and computes terminal paired rewards on private `C_reward` packages.
It retains all root trajectories, deduplicates candidate evaluation, and excludes
the whole group from training after infrastructure failure or unusable reward
evaluation. `collection.training_records` checks archived reward provenance
before exporting all roots.

`packages.PackageProvider` freezes a certified package manifest and samples
without replacement. It checks declared family/lineage boundaries, original
support/probe/query source roles, and distinct private query sources. Draws and
resume state are archived and recomputable. Exhaustion is explicit: there is no
automatic wraparound of a tiny reward bank. `collect_sampled_self_edit_group`
binds executed packages to the recorded draw. Usami's native certificate adapter
is in `integrations/rsi_usami/packages.py`; no Usami import enters the Core.
Independent source-label auditing and a sufficiently large real task bank are
still required. Metadata consistency checks do not establish structural novelty.
The full original objective and remaining P0–P6 acceptance work are tracked in
`experiments/rsi/reports/IMPLEMENTATION_STATUS.zh.md`.
