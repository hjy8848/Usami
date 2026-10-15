# Usami research website

Public URL: https://hjy8848.github.io/Usami/

A standalone static research presentation, separate from the local World Explorer.
The page presents two distinct contributions: the Usami executable business
benchmark (worlds, two evaluation tracks, goal-based generation and verification)
and VAST-CoEvo Skill co-evolution (training, selection and experimental evidence).
Co-evolution diagnostics are not presented as benchmark leaderboard results.
No build step, external fonts, backend, model calls, analytics, or user data storage.
All assets are local. `assets/worlds.svg` and the mark are original SVG illustrations.
The editorial research-page format was inspired by https://pub.sakana.ai/mass/;
no third-party text, figures or source code was copied.

## Preview

From the repository root:

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:4173/. The mechanism animation is an illustration, not a live
experiment. World maps show conceptual relationships, not full schemas or live state.
The page works under a repository subpath and requires no root-relative assets.

## Deployment

`.github/workflows/pages.yml` publishes only `site/` through GitHub Actions.
Repository Settings → Pages → Build and deployment must use **GitHub Actions**.
A push to `main` changing the site or workflow triggers deployment. The workflow can
also be dispatched manually. No experimental bundles, credentials or backend files
are included in the Pages artifact.

## Evidence and updates

Experimental results displayed in `index.html` (initial no-JS view) and `app.js`
(interactive views) are transcribed from these immutable historical reports:

- `experiments/vast_coevo/results/customer-paired-001/SUMMARY.json`: 40 Episodes,
  C0 0 / C1 20 successful business violations, three primary reference rules.
- `experiments/vast_coevo/results/service-repair-001/REPORT.md`: 80 diagnostic cross
  Episodes within a 116-Episode run; 8 / 15 / 3 / 12 violations. Both candidates
  failed the historical dynamic acceptance checks.
- `experiments/vast_coevo/results/multigen-heldout-recovery-002/FINAL_REPORT.md`:
  72 held-out Episodes, 17 / 15 / 14 correct of 24; identical Service Snapshot.
- `experiments/vast_coevo/results/training-evidence-audit-001/REPORT.md`:
  two post-Reflection cross Episodes had verified dependency violations omitted
  from Reflection inputs. This nuance supplements the earlier final report.
- `experiments/vast_coevo/results/recursive-training-v3-implementation-001/SUMMARY.json`:
  953 regression tests; no online v3 performance or measured cost-saving evidence.

The plots have explicit units and directions. They distinguish discovered failures,
Service repair, static acceptance, dynamic acceptance and held-out generalization.
Do not recast historical candidate diagnostics as formally accepted evolution or
compare held-out labels with identical Snapshot hashes as learned improvements.

When updating a study, update both initial HTML and JS if applicable, preserve the
source report link and its limitations, and verify keyboard tab navigation,
step selection, playback/pause, slider, all four worlds and all three study views.
Reduced-motion preference disables transitions; playback starts only on request.
