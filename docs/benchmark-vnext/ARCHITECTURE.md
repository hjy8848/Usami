# Architecture and migration boundaries

## Target, not a completed eight-domain release

The complete objective is an eight-domain executable Benchmark. Track A comprises SaaS, CloudOps, Fulfillment and StayOps. Track B comprises independently implemented After-sales, Airline, Property and Education service environments. Domain weights are intended to be 1/8 each; track weights 1/2 each. Actual eight-domain datasets and scoring are not yet delivered in this checkpoint.

## Existing authoritative implementations

- SaaS: `usami/world` defines versioned state, rules and generators; `usami/benchmark` contains certified goals and frozen manifests.
- CloudOps: `usami_cloudops` has its own Engine, policy, actual transitions, Oracle and service/interaction runtime.
- Fulfillment/StayOps: domain-local models, rules, actual mutations, observations and goals; `usami_harness` supplies adapter-parameterized event execution, request authority, Oracle, search, Service and Customer sessions.
- VAST: `integrations/usami` keeps business models outside the algorithm core. Frozen Discovery currently has a CloudOps-specific composer. `explicit-selection-v2` defaults to evidence-only static inheritance and is retained.

No previous frozen manifest, source pin, historical score or raw experiment record is migration input. Precise historical replay requires the original source snapshot. New source files change outer source pin sets naturally; historical manifests are not rewritten to match them.

## Versioned new boundaries

`usami_benchmark.contracts.WorldSpec` registers domain, generator version, native rules version, generator configuration, seed, partition and unconditioned generation mode. It accepts no task, skill, reward or model performance input.

`usami_benchmark.registry` explicitly selects the structural distribution; it does not replace old `generate_world()`. The native world schema remains the existing domain version where native business semantics are reused. Distribution version and business rules version are distinct provenance fields.

`usami_benchmark.worlds.FrozenWorld` stores complete world bytes, original hash, independent anonymous structure and permission signatures, source hashes, generator diagnostics and registration hash. `WorldPool.load()` verifies the registration seal and returns an isolated copy. A Discovery pool refuses Test Demo/Held-out registrations.

`usami_dialogue` currently implements the private fact/preference/consent contract and trusted reducer. It is not yet an implementation of the four requested industries. Domain-specific state machines, independent policy/appliers and full dialogue trace execution are still required before Track B is complete.

## What is shared and what is not

Canonical JSON, hashes, immutable archives, actor-fixed model calls, event chains, budgets, native search plumbing and per-domain adapters can be shared. Business entities, policy decisions, stock/seat/room/money arithmetic, service eligibility and actual mutations must remain domain-specific.

For Track B, private Customer facts must not be fields silently exposed in Service observations. Trusted Customer events may reveal an exact subset, revise permitted preferences and confirm an actual offer. Business policy must independently require those facts/confirmations. Counting turns cannot substitute for proving a change in allowed business actions.

## Outstanding integration

Eight-domain native binding, multi-domain Task Composer, dialogue Engine/Oracle, dataset construction, capability matrix, macro scoring, leakage audit and VAST controller integration remain active work. This checkpoint does not claim those mechanisms are finished.
