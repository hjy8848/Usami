# Research code reference audit

Audit baseline: `4e6de2196f94c6c70100ac28bffbc442c4bcaacc`.
This pass identifies active legacy code and safe deletion candidates; it does
not remove modules.

| Area | Evidence found | Decision |
| --- | --- | --- |
| `usami/benchmark/` | Used by `python -m usami.benchmark` in the root README and benchmark release/verification instructions; imports also appear in current tests, domain integrations, and benchmark tooling. | Keep. It remains an executable benchmark interface. |
| `integrations/usami/` | The root README and VAST-CoEvo docs expose `python -m integrations.usami`; current adapters, designer/frozen controllers, examples, and tests import it. | Keep. It remains the active integration and experiment entry point. |
| `examples/benchmark/` | Its release, build, pilot, render, replay, and verification scripts are named in `benchmarks/v0.1.0` and `benchmarks/v0.2.0` reproduction instructions. | Keep for now. Although the path audit found no runtime import dependency on these scripts, the published reproduction instructions depend on them. |

No file in these reviewed areas met the deletion bar: zero runtime references,
zero documented reproduction references, and no unique replay or release role.
Further cleanup should be based on a broader call-graph audit and an explicit
replacement for any documented CLI, not on directory age or apparent overlap.
