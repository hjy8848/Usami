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
The full original objective and remaining P0–P6 acceptance work are tracked in
`experiments/rsi/reports/IMPLEMENTATION_STATUS.zh.md`.
