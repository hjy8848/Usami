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

`training.py` exports validated root token/logprob/mask records and group
advantages. Parameter RL has not been run or validated.
`collection.collect_self_edit_group` executes independent roots under identical
phase allocations, reserves the entire group before sampling, selects on
`C_select`, and computes terminal paired rewards on private `C_reward` packages.
It retains all root trajectories, deduplicates candidate evaluation, and excludes
the whole group from training after infrastructure failure or unusable reward
evaluation. `collection.training_records` checks archived reward provenance
before exporting all roots.

`verl_backend.py` adds an optional verl `0.9.1` adapter and a one-group GRPO
bundle exporter. It preserves archived behavior tokens, masks, logprobs, and
root rewards; GRPO groups roots by the registered context `uid` and uses
sequence-mean-token-mean loss. Multi-turn export requires every later tokenized
prompt to continue the exact previous prompt-and-generation stream. Other
trajectories are rejected because flattening them would change the conditioning
context. This is implementation code only: verl has not been installed or
exercised, no parameters have been updated, and checkpoint identity has not
been checked against local weight files. `verl_overlay.yaml` is a config
fragment, not a standalone trainer command. There is no recursive multi-group
training controller yet.

Install the optional pinned dependency in a compatible Python environment
with `pip install -e '.[verl]'` from `rsi_core/`. Installation does not launch
Ray, load model weights, call a model, or start training.

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
