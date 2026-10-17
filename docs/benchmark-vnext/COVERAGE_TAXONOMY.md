# Coverage taxonomy and evidence requirements

The versioned evaluation schema declares these fifteen independent capability
keys. A business family is domain-specific; it must not be inferred solely from
how many tools a Service calls.

| Key | Meaning | Evidence required for a tested-coverage claim |
| --- | --- | --- |
| identity_authorization | Authenticated identity, roles and exact writes | Native decision and independent trusted request audit |
| entity_isolation | Multiple entities and tenant boundaries | Actual scoped requests, protected frame and Reference result |
| state_preconditions | Lifecycle/action prerequisites | Actual prestate and rule decision |
| capacity_resources | Finite seats, stock, quota or schedules | Resource conservation/boundary certificate |
| time_deadlines | Expiry, windows and temporal feasibility | Controlled clock and native boundary decisions |
| financial_constraints | Payments, fees, refunds and balances | Actual ledger transitions and native amount checks |
| causal_dependencies | Necessary prerequisite transitions | Executable omission/causal evidence; not raw path length |
| alternative_paths | Different legal solutions to a goal | At least two independently valid paths with meaningful differences |
| side_effect_consistency | Protected unrelated state and invariants | Explicit frame plus independent full transition audit |
| refusal_decisions | Correct and false refusals | Exact requested operation and actual Reference result |
| information_resolution | Missing facts affect valid action | Replay-bound removal of a truly disclosed necessary fact |
| preference_negotiation | Choice changes the correct action | A permitted alternate preference changes native decision |
| explicit_consent | Current, exact irreversible authorization | Real offer/consent plus consent-removal counterfactual |
| cross_turn_commitments | Later action respects current agreement | Earlier real commitment and later actual revision/decision evidence |
| mixed_completion_refusal | Legal work and accurate partial refusal | Objective subgoals, actual transition and attributable correct refusal |

The matrix axes are `Capability × Business Family × Difficulty × Task Outcome`.
Outcomes are completion, refusal and mixed; mixed is not counted as a completely
successful task when only its legitimate part succeeds. Difficulty must come
from certified business structure and necessary dependencies. A bounded witness
is an upper bound on a legal path, not automatically the global minimum proof
length. The aggregator allows `unclassified` until a structural classifier has
sufficient evidence; it must not use model failure rate to assign difficulty.

## Current implementation versus final coverage

Native dialogue certificates now support all six dependency categories: missing
information, preference resolution, explicit consent, actual external update,
actual cross-turn revision and partial completion/refusal. Only a changed
independent Reference decision establishes a dependency. The last two require
actual source events: a hypothetical prior agreement or invented refusal cannot
be substituted. A successful basic example does not establish every capability
in its domain. A descriptor annotation is not coverage proof.

The 100-world-per-domain structural audits describe world diversity, not task
coverage. Anonymous world counts cannot be converted into numbers of independent
tests. The full eight-domain matrix, per-cell certified quantities, 40/100-task
per-domain sampling and split leakage reports are still being implemented; they
must be published with actual evidence and honest gaps. This document and the
fifteen schema keys do not claim those release artifacts already exist.

A genuinely inapplicable capability requires a domain-rule explanation labelled
`N/A`. Missing evidence is `NOT AUDITED` or `NOT RUN`, rather than `N/A` or zero.
Existing tool-centric domains already support Customer/Service interaction; their
coverage cannot be dismissed merely because they lack the new private-state
protocol. Their claimed dialogue necessities require equivalent actual proof.
