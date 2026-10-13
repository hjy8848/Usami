# CloudOps v0.1 quality and diversity audit

Machine evidence: [coverage.json](coverage.json), frozen manifests and [18 readable examples](TASK_EXAMPLES.md). Values describe this curated corpus and explicit signatures, not a theoretical upper bound or τ-bench equivalence. External human business-quality review is **pending**.

| Measure | Result |
|---|---:|
| Fixed Service tasks | 45 (train 27 / validation 9 / test-demo 9) |
| Business families | 12 |
| Independent anonymous structures | 12 |
| Semantic decision signatures | 12 |
| Completion / policy-refusal tasks | 29 / 16 |
| Cross-project tasks | 4 / 45 (8.89%) |
| Cross-subsystem tasks | 16 / 45 (35.56%) |
| Witness omission depth 0 / 1 / 2 | 16 / 18 / 11 |
| Tasks with multiple certified legal routes | 10 |
| Certified legal witnesses | 42 |
| Train / test-demo overlap (structure and semantics) | 0 / 0 |
| Train / validation overlap (structure and semantics) | 9 / 9 |

Train/validation intentionally share nine families; test-demo holds out safe retirement, create-and-attach stack and live dependency reconfiguration. IDs, names, seeds, CPU/memory sizing and reordered solutions do not inflate structure counts. Signatures retain operation/argument shapes, resource relationships, permission scope, initial decision code, relevant state facts, declared goals and causal edge types. Integer thresholds are normalized. Renaming and proportional sizing invariance are tested.

The 12 families are billing recovery, capacity expansion, dependency startup, scoped onboarding, quota reduction, cross-project isolation, viewer refusal, cycle refusal, duplicate-charge refusal, safe retirement, create stack and live reconfiguration. Cross-subsystem means the finite task write choices span billing/compute, quota/compute or access/compute. Cross-project here is the explicit mismatched-resource isolation family; it is not inferred merely because a world has multiple projects.

## Coverage and causal evidence

Frozen task choices cover 10 of the 11 writes. **Revoke access is implemented and unit tested, but not represented as a fixed Service task.** Queries, payment failure/retry, Admin ceilings, all quota dimensions, suspended starts and additional boundaries are covered by tests rather than counted as extra task structures. `actual_initial_decision_coverage` records first observable Reference outcomes on frozen candidates; it is not exhaustive predicate coverage and includes resources that must first be created.

Reachability searches the finite unordered approved operation set, maximum depth six and 2,048 search nodes, retaining up to eight irreducible solutions and bounded state-order alternatives. Every published witness runs through actual Reference Engine, independent Oracle, Goal/frame and exact replay. Refusal certificates are recomputed from rules and preserved initial state.

For each witness, omit one predecessor and execute the remaining sequence: record each explicit rejection and whether the conjunctive Goal remains satisfied. A first failure with no intervening failed operation is a direct edge; failures after an intervening failure are indirect edges. Depth is the longest mediated edge chain in the retained certificate, not a proof over all possible plans. The report separately lists direct/indirect edge counts. Merely having several steps does not imply causal depth.

## Track separation and evidence limits

Service freezes a goal and frame but never supplies internal predicates, witness order, Oracle answers or refusal certificates to the LLM. Finite exact Customer-approved writes are disclosed unordered, as authorization choices; the model selects queries, actions and order. This constrained-intent protocol is not free-form inference of customer authorization.

Discovery stores no task or family. Its frozen worlds must equal the unconditioned seed generator. Customer receives a permission-filtered initial observation, public tool descriptions, actual Service replies and remaining budget. It receives no hidden world, witness or Oracle finding. Exact writes are declared independently before Service calls and episode duplicates do not renew authority. New IDs require a real Service reply before use in a later intent. Role checks remain separate from intent verification.

Discovery comparison pins victim Service/settings, identities, world states, tool set, mode, budgets, trials and source. Customer model/general method may differ. Whole episodes, errors, budget endings and previously collected attempts remain visible. No training, Customer Evolver, automatic repair or statistical claim about broader model quality is included.

Offline privileged proof/one-step clients and StopCustomer fixtures establish software behavior only. The live pilot is separately labeled and covers a small preregistered subset, not a full 45-task or all-world Customer benchmark. Private blind testing, additional structures, exhaustive rule coverage and external human review remain future work.
