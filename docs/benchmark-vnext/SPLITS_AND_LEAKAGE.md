# World partitions, task leakage and private Held-out

`usami_benchmark.splits` implements independently regenerated world-split checks
and finite private Held-out generation. It does **not** yet implement the final
all-domain task-semantic/task-combination leakage audit. Those axes are explicitly
`NOT RUN`, even when world isolation passes.

## Public world audit

`audit_world_splits(entries)` accepts content-addressed `FrozenWorld` entries.
Every entry is independently regenerated from its source specification and must
match its world, structural signature and generator/rules source hashes. A changed
signature or source hash cannot pass merely because the outer object was resealed.
The audit compares both exact world hashes and anonymous structures across
partitions, grouped by domain. Re-registering the same business world with a
`test_demo` label changes its registration hash but still exposes both overlaps.
A different seed alone is not isolation proof. Duplicate registrations are errors.

The report retains partition/domain counts, source-registration commitment and
pairwise overlap counts. Anonymous colour refinement is conservative and is not a
complete isomorphism or semantic equivalence proof. These caveats also apply to
the structure-based `partition_for` helper; it cannot certify task novelty.

## Generating a private world pool

`generate_private_heldout(specs, known_worlds, root, requested_count=...)` requires
a finite, predeclared schedule of unconditioned `WorldSpec`s already labelled
`heldout`. It saves the full schedule and exact exclusion policy before generating
any candidate. Candidates sharing a known world or anonymous structure are
excluded; accepted candidates are also checked against one another. The function
never reads Designer/Service performance, task goals, skills or model responses.
It does not silently resample after a shortfall. Reports retain actual quantities,
excluded candidates and generation failures; incomplete pools remain incomplete.

The output must be a new directory outside this public repository. Its root is
created with private directory permissions and stores the complete seeds/worlds;
it must not be committed. No paid model is called, and evaluation remains
`NOT RUN`. A generated pool is not yet a scored Held-out experiment.

The caller must supply the complete known-world registry for the research scope.
This check establishes disjointness from **that supplied registry**, not from
unknown/unregistered historical data. Historical runtimes require their pinned
sources; do not relabel previously learned records or rewrite their source hashes.

## Remaining isolation axes

The final release must additionally audit task semantic decision signatures,
business-family/capability combinations and task structures, distinguishing world,
task-combination, business-structure and cross-domain generalization. These checks
must derive from actual certified native tasks. No such conclusion follows from
world disjointness, registry content hashes or the evaluation plan alone. Training
and development evidence must never be relabelled as final test evidence.

## Executed public-world checkpoint

`audits/eight-domain-world-splits-001/report.json` independently regenerated the
800 already archived worlds (100 per domain). It observed 567 train, 122
validation and 111 test-demo worlds; all three pairwise exact-world and anonymous
structure overlap counts are zero. StayOps uses the explicitly registered v2
pool. All source specifications and source-pool paths are retained. This is
world-isolation evidence, not the 800-task Core release or semantic task isolation.
