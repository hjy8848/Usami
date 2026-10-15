# Usami method article

https://hjy8848.github.io/Usami/

Standalone static research article, separate from the local World Explorer.
No model requests, external fonts, telemetry, storage, build step or backend.
The editorial form is inspired by https://pub.sakana.ai/mass/; no third-party text,
figures or code is copied.

The page presents two distinct contributions:

1. Usami Benchmark: executable state, causal prerequisites, multiple valid paths,
   two evaluation Tracks, versioned manifests and independent verification.
2. VAST-CoEvo: shared interaction evidence, role-specific Reflection and selection,
   immutable snapshots, recursion and separate post-training evaluation.

## Teaching examples (not experimental results)

The website intentionally contains **no real experimental performance data**,
result plots, online traces or claims of measured improvement. Historical repository
records are unchanged, and are not included in the Pages artifact.

Example A is a local JavaScript teaching model for a small subset of the public
CloudOps `start_instance` rules in `usami_cloudops/rules.py`. It is not the actual
Python Engine or an official benchmark instance. The fixed authorization scope
contains only starts of `db`, `cache`, `app`; identity does not come from actions.

- All resources start stopped; dependencies are db/cache → app, project-local DAG.
- db: CPU 2 / memory 4, cache: 1 / 2, app: 2 / 4.
- Normal quota: CPU 8 / memory 16 / instances 3. Restricted preset CPU 4.
- Four presets isolate normal operation, Viewer denial, project suspension and quota.
- Check order mirrors selected reference rules: role, running no-op, project,
  dependencies, three quota dimensions. Denials do not change state.
- Normal goal admits db → cache → app and cache → db → app.
- Changing preset resets all mutable state. No role, quota or dependency writes.

Example B is a **fictional** Viewer unauthorized-write case. Its request, engine event,
Oracle classification, reflection principles and selection branches are illustrative,
not actual model output. Principle excerpts are not complete publishable SkillPatch
objects. Customer static PASS and the selected Service Gate outcome are assumptions.
The diagram shows evidence flow; actual updates run Customer first, Service second.
NOOP/rejection retains the old Service. No new generation of models is claimed.

## Preview and deploy

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory site
```

GitHub Pages uses `.github/workflows/pages.yml`, deploying only `site/` on changes
under `main`. All paths are relative to support `/Usami/`. No experimental bundles
or backend files are published. Schematics have captions and text alternatives;
core explanations remain visible without JavaScript. Animations start only on request.
