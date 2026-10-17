# Usami research presentation

Static GitHub Pages article for Usami Benchmark and VAST-CoEvo, independent of the
local World Explorer. The editorial direction is inspired by the MASS research
page. No third-party text, figures, code or result plots are copied.

## Narrative

The article starts with a concrete service interaction and asks where the next
useful learning problem comes from. It then explains two distinct contributions:

1. Usami: executable business worlds whose identities, objects, relationships,
   goals and valid action paths support task composition, independent of any
   evolution algorithm. The world library includes eight native domain modules;
   this is not a claim that an eight-domain benchmark release is complete.
2. VAST-CoEvo: initial Service execution produces verified success/failure
   trajectories; a Designer uses their weak points to choose new challenges; a
   fixed Customer mediates real multi-turn interaction; Designer and Service
   retain separate, recursively used Skills while model weights remain fixed.

Implementation-level Track names and static selection details are folded into
optional disclosures, after the main explanation. Related work links to primary
papers for tau-bench, Self-Challenging Language Model Agents and MASS.

## Teaching interactions

The page contains no real model-run results or live inference, telemetry, browser
storage, external fonts, backend service, or build step.

- The CloudOps task composer uses one deeply frozen teaching world, containing
  three projects and two existing members with project-scoped roles. Readers
  select an identity, a project and any nonempty subset of db/cache/app targets.
  Selecting an identity derives its existing role; it does not edit permissions.
- Each run copies the selected project. Actions and reset never mutate the world
  or other projects. The browser illustrates a subset of Reference-style startup
  decisions, not research Sandbox execution or the actual Python Engine.
- Parallel dependency tasks admit multiple valid orders. Chain, quota, project
  state, role and task-scope constraints affect the decisions independently.
- The success/failure trajectories and Skill examples are authored mechanism
  illustrations, not raw model outputs or experimental measurements. A successful
  trajectory includes an observable plan correction that motivates a new probe.
- The recursive diagram explicitly starts from initial-task execution. Its
  default static-only version branches preserve the current implementation's
  publication semantics; evaluation remains separate from training.

## Preview and deploy

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory site
```

`.github/workflows/pages.yml` deploys only `site/` from main. Relative assets work
under `/Usami/`; experiment bundles and backend files are not part of the artifact.
Animations require user input. Figures have captions, text alternatives and
keyboard-accessible controls. Asset cache versions are derived from content hashes.
