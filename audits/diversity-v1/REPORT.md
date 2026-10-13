# Usami Diversity & Coverage Audit

## Provenance and scope

Audit `usami-diversity-audit-1`; signature `usami-audit-signatures-1`. Generator `saas-generator-0.1.0`; rules `saas-rules-0.1.0`; scenarios `saas-scenarios-0.1.0`.

Fixed 1000 seeds: 0 … 999. Config hash `47f34c4a7c19d4ea8ddac5c81d2d79a927b0322f76c1d42419d099267705753a`; rules hash `57edc676aa4ffc9d49529dd4c839aa36efa4201851990dd43fa535aff4e24912`. Python 3.9.6, Pydantic 2.13.5.

Full ordered seed list, config, source SHA256s, world hashes, signature frequencies and canonical example payloads are in `results.json`. No timestamps, API calls or subjective LLM scores enter the metrics. Same source, config and runtime reproduce byte-identical output.

The population is the current `generate_scenarios` candidate pool. It contains reference-labeled, preconstructed operation sequences, not natural-language goals, autonomous agent trajectories or all possible legal operation sequences. Counts are observed under these signatures; they are not an exhaustive count of the SaaS domain.

## World diversity

| Metric | Observed |
| --- | --- |
| Worlds | 1000 |
| business_instance | 1000 |
| policy_state_topology | 1000 |
| role_topology | 985 |

Business instance fingerprints retain names, IDs, dates and amounts. Role topology instead canonicalizes the user–organization incidence graph with roles/statuses under all organization permutations and sorted anonymous user rows; policy topology additionally includes normalized organization state. Exact graph canonicalization is restricted to ≤6 organizations; larger configs report Unknown for those two metrics. A unique whole-world graph does not imply a unique local task.

**users_count**

| Value | Count |
| --- | --- |
| 8 | 1000 |

**organizations_count**

| Value | Count |
| --- | --- |
| 3 | 1000 |

**memberships_count**

| Value | Count |
| --- | --- |
| 10 | 80 |
| 11 | 86 |
| 12 | 97 |
| 13 | 96 |
| 14 | 105 |
| 15 | 83 |
| 16 | 60 |
| 17 | 52 |
| 18 | 23 |
| 19 | 28 |
| 20 | 13 |
| 21 | 9 |
| 22 | 4 |
| 23 | 3 |
| 3 | 2 |
| 4 | 12 |
| 5 | 13 |
| 6 | 32 |
| 7 | 56 |
| 8 | 63 |
| 9 | 83 |

**subscriptions_count**

| Value | Count |
| --- | --- |
| 3 | 1000 |

**invoices_count**

| Value | Count |
| --- | --- |
| 12 | 1000 |

**membership_role_status**

| Value | Count |
| --- | --- |
| billing_admin/active | 3877 |
| billing_admin/inactive | 678 |
| member/active | 3983 |
| member/inactive | 685 |
| owner/active | 3000 |

**user_organization_degree**

| Value | Count |
| --- | --- |
| 0 | 891 |
| 1 | 2985 |
| 2 | 3134 |
| 3 | 990 |

**user_active_organization_degree**

| Value | Count |
| --- | --- |
| 0 | 1226 |
| 1 | 3352 |
| 2 | 2758 |
| 3 | 664 |

**organization_members**

| Value | Count |
| --- | --- |
| 1 | 447 |
| 2 | 456 |
| 3 | 409 |
| 4 | 401 |
| 5 | 494 |
| 6 | 238 |
| 7 | 305 |
| 8 | 250 |

**organization_active_members**

| Value | Count |
| --- | --- |
| 1 | 535 |
| 2 | 499 |
| 3 | 496 |
| 4 | 473 |
| 5 | 411 |
| 6 | 288 |
| 7 | 220 |
| 8 | 78 |

**subscription_plan**

| Value | Count |
| --- | --- |
| business | 1034 |
| starter | 950 |
| team | 1016 |

**subscription_status**

| Value | Count |
| --- | --- |
| active | 2029 |
| expired | 971 |

**subscription_auto_renew**

| Value | Count |
| --- | --- |
| False | 1992 |
| True | 1008 |

**subscription_seats_vs_capacity**

| Value | Count |
| --- | --- |
| eq | 460 |
| lt | 2540 |

**subscription_seats_vs_members**

| Value | Count |
| --- | --- |
| eq | 449 |
| gt | 2551 |

**subscription_joint_state**

| Value | Count |
| --- | --- |
| active/False/eq/eq | 38 |
| active/False/eq/lt | 111 |
| active/False/gt/eq | 124 |
| active/False/gt/lt | 748 |
| active/True/eq/eq | 42 |
| active/True/eq/lt | 111 |
| active/True/gt/eq | 112 |
| active/True/gt/lt | 743 |
| expired/False/eq/eq | 34 |
| expired/False/eq/lt | 113 |
| expired/False/gt/eq | 110 |
| expired/False/gt/lt | 714 |

**invoice_status**

| Value | Count |
| --- | --- |
| paid | 6000 |
| refunded | 3000 |
| unpaid | 3000 |

**invoice_refund_class**

| Value | Count |
| --- | --- |
| already_refunded | 3000 |
| eligible | 3000 |
| stale | 3000 |
| unpaid | 3000 |

**invoice_payment_method**

| Value | Count |
| --- | --- |
| None | 3000 |
| bank_transfer | 2996 |
| card_mastercard | 2936 |
| card_visa | 3068 |

**invoice_history_length**

| Value | Count |
| --- | --- |
| 0 | 9000 |
| 1 | 3000 |

**heldout_world_combination**

| Value | Count |
| --- | --- |
| False | 815 |
| True | 185 |

Cross-organization role differences: 3193/8000 user instances (39.91% of all; 44.91% of connected; 77.42% of multi-organization users). Roles include inactive memberships; active organization degrees are reported separately.

Amounts, exact seats, member/capacity slack and payment methods have full histograms in JSON. Per source, every organization has exactly one subscription and four invoices: eligible paid, stale paid, unpaid and already refunded. Full refund only; amounts are integer multiples of 100 cents. Owner allocation is deterministic by organization index; membership selection/roles/status, plan, seats, active/expired state, renewal, cycle offsets and coherent payment histories are sampled. Entity counts for users/organizations are configuration constants. Default membership count is capped at eight per organization, even when configured with more users. Plan rank is stored but does not drive reference legality.

## Scenario structural diversity

Template signatures preserve operation types, first-encounter anonymous typed entities, owner/subscription/resource links, actor membership roles/status across involved organizations and measured legality dependencies. Semantic signatures add policy-relative prestate/parameter comparisons, authorization, exact reference verdict, actually visited guards and normalized state changes. Names/IDs, category labels, absolute payment amounts/dates and arbitrary seat values are excluded when comparisons are unchanged. Active/expired, equal/less/greater boundary conditions and no-op versus mutation remain distinct. Relative capacity comparisons distinguish plan direction; names/ranks do not.

| Level | Samples | Unique | Repeats | Repeat ratio | Singletons | H bits | Effective diversity | Top10 share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| template | 82699 | 24 | 82675 | 99.97% | 0 | 3.640 | 12.47 | 80.81% |
| semantic | 82699 | 293 | 82406 | 99.65% | 4 | 6.288 | 78.13 | 38.53% |

Repetition = 1 − unique/sample count, conditional on the stated abstraction. It measures equivalent measured decision problems, not whether all repeated tasks are useless for statistical evaluation. Shannon H measures distribution spread; 2^H is the number of equally frequent classes with that entropy, not an extra count of novel structures.

### Growth

| Worlds | Scenarios | Templates | Semantics |
| --- | --- | --- | --- |
| 1 | 97 | 18 | 42 |
| 10 | 871 | 22 | 108 |
| 25 | 2086 | 23 | 189 |
| 50 | 4095 | 24 | 231 |
| 100 | 8176 | 24 | 254 |
| 200 | 16434 | 24 | 270 |
| 500 | 41363 | 24 | 291 |
| 1000 | 82699 | 24 | 293 |

### Top 10 template

| Signature prefix | Count | Example seed | Category | Operations (display only) | Verdicts |
| --- | --- | --- | --- | --- | --- |
| 1a20528afe33 | 24000 | 0 | refund | refund_invoice |  |
| 3220a4c3581a | 9000 | 0 | single | change_seats |  |
| 478ed6f9799d | 7860 | 0 | permission | change_member_role |  |
| 97d5d3f6d4b3 | 6000 | 0 | single | cancel_renewal |  |
| 8f0fc6a8b44f | 3983 | 0 | query | get_subscription |  |
| f929b3bc12ad | 3983 | 0 | permission | cancel_renewal |  |
| 044b586384fd | 3000 | 0 | multi_step_refund | refund_invoice → refund_invoice |  |
| 1245971fe2a3 | 3000 | 0 | query | get_subscription |  |
| 535e9a059ed8 | 3000 | 0 | permission | change_member_role |  |
| 55a05f2a4444 | 3000 | 0 | multi_step_refund | refund_invoice → refund_invoice |  |

### Top 10 semantic

| Signature prefix | Count | Example seed | Category | Operations (display only) | Verdicts |
| --- | --- | --- | --- | --- | --- |
| 1ede212e7b85 | 3983 | 0 | permission | change_member_role | [True, None] |
| dbc71e0140a1 | 3877 | 0 | permission | change_member_role | [True, None] |
| 45ebbb101191 | 3000 | 0 | permission | change_member_role | [False, 'OWNER_IMMUTABLE'] |
| 76d98437eb04 | 3000 | 0 | refund_constraint | refund_invoice | [False, 'REFUND_AMOUNT_MISMATCH'] |
| 7e20c1fee4cc | 3000 | 0 | refund | refund_invoice | [True, None] |
| 8182bc45afe4 | 3000 | 0 | refund_constraint | refund_invoice | [False, 'REFUND_WINDOW_EXPIRED'] |
| a28de446cd02 | 3000 | 0 | multi_step_refund | refund_invoice → refund_invoice | [True, None]; [False, 'DUPLICATE_REFUND'] |
| bd1648709199 | 3000 | 0 | multi_step_refund | refund_invoice → refund_invoice | [False, 'REFUND_WINDOW_EXPIRED']; [False, 'REFUND_WINDOW_EXPIRED'] |
| c0e9d63e12f2 | 3000 | 0 | refund | refund_invoice | [False, 'REFUND_WINDOW_EXPIRED'] |
| ea14271995e8 | 3000 | 0 | refund_constraint | refund_invoice | [False, 'REFUND_WINDOW_EXPIRED'] |

The abbreviated operation sequences above are labels for reading the table, not the signature definition. Full payloads and scenario IDs allow reproduction of every observed class.

## Combination complexity

| Metric | Distribution (scenario count) |
| --- | --- |
| business_guards_visited | {'0': 5922, '1': 10966, '10': 5318, '2': 14913, '3': 13860, '4': 18087, '5': 3000, '6': 9000, '7': 1633} |
| cross_organization | {'False': 79699, 'True': 3000} |
| decision_sensitive | {'False': 75748, 'True': 6951} |
| dependencies | {'0': 72748, '1': 3899, '2': 2782, '3': 2621, '4': 649} |
| depth | {'0': 72748, '1': 9302, '2': 649} |
| distinct_operations | {'1': 75748, '2': 1633, '3': 5318} |
| final_state_sensitive | {'False': 75748, 'True': 6951} |
| mixed_allowed_rejected | {'False': 72748, 'True': 9951} |
| organizations | {'1': 79699, '2': 3000} |
| related_entities | {'3': 22633, '4': 43888, '5': 7860, '6': 8318} |
| steps | {'1': 69748, '2': 6000, '5': 6951} |
| subsystems | {'1': 77381, '3': 5318} |

Multi-step scenarios: 12951/82699 (15.66%). Scenarios with measured legality dependencies: 9951/82699 (12.03%; 76.84% of multi-step). Cross-organization: 3000/82699 (3.63%). Mixed allowed/rejected: 9951/82699 (12.03%). Reversal changes decision bag in 6951 and final business state in 6951 scenarios.

Dependency test: omit each successful state-changing step, reexecute the remaining prefix with the same real reference and trusted authorization, and compare later (allowed, error) verdicts. Edges can include mediated effects; depth is the longest path in this leave-one-out legality graph, not a claim of identified direct causality. Failed/no-op steps cannot generate edges. Read-to-write information dependencies and agent reasoning are Unknown/not measured. Order sensitivity tests full reversal only, comparing verdict bags grouped by actor+operation and final state after removing refund execution-nonce IDs; all permutations are not enumerated.

| Dependency operation pair | Observed edges |
| --- | --- |
| change_member_role->cancel_renewal | 7939 |
| change_member_role->refund_invoice | 5318 |
| change_plan->change_plan | 649 |
| change_plan->change_seats | 649 |
| change_seats->change_plan | 2367 |
| refund_invoice->refund_invoice | 3000 |

## Business rule coverage

Inventory is extracted from actual `ReferenceRules.decide` rejection guards. Python line tracing observes which guards the unmodified function checks and which return executes. `visited` means condition evaluated (pass or veto), not a rejection. Permission guards with the same error remain separate. Authorization is a trusted harness/Engine gate and is reported separately from business policy. Policy checks on unauthorized samples are audit evaluations, not a claim that Engine executes those checks before rejecting authorization.

| Guard | Source line | Error | Condition | Visited | Pass | Veto |
| --- | --- | --- | --- | --- | --- | --- |
| g01 | 110 | UNSUPPORTED_RULES_VERSION | world.rules.version != RULES_VERSION | 116503 | 116503 | 0 |
| g02 | 112 | INVALID_WORLD | check_invariants(world) | 116503 | 116503 | 0 |
| g03 | 114 | UNKNOWN_ACTOR | actor_id not in world.users | 116503 | 116503 | 0 |
| g04 | 116 | ORG_NOT_FOUND | operation.org_id not in world.organizations | 116503 | 116503 | 0 |
| g05 | 119 | CROSS_ORG_ACCESS | member is None | 116503 | 113581 | 2922 |
| g06 | 130 | RESOURCE_NOT_FOUND | resource is None | 113581 | 113581 | 0 |
| g07 | 133 | CROSS_ORG_RESOURCE | resource_org != operation.org_id | 113581 | 110581 | 3000 |
| g08 | 136 | PERMISSION_DENIED | member.role != 'owner' | 21496 | 21496 | 0 |
| g09 | 138 | PERMISSION_DENIED | (not operation.is_query or name == 'get_invoice') and member.role == 'member' | 89085 | 79784 | 9301 |
| g10 | 145 | INVALID_PLAN | target is None | 7899 | 7899 | 0 |
| g11 | 147 | SUBSCRIPTION_NOT_ACTIVE | resource.status != 'active' | 7899 | 6928 | 971 |
| g12 | 149 | SEAT_LIMIT_EXCEEDED | resource.seats > target.max_seats | 6928 | 4000 | 2928 |
| g13 | 153 | SUBSCRIPTION_NOT_ACTIVE | resource.status != 'active' | 12266 | 9353 | 2913 |
| g14 | 158 | SEATS_BELOW_MEMBERS | seats < max(1, active_count) | 9353 | 7324 | 2029 |
| g15 | 160 | SEAT_LIMIT_EXCEEDED | seats > world.rules.plans[resource.plan_id].max_seats | 7324 | 5295 | 2029 |
| g16 | 164 | SUBSCRIPTION_NOT_ACTIVE | resource.status != 'active' | 11318 | 9376 | 1942 |
| g17 | 168 | DUPLICATE_REFUND | resource.status == 'refunded' or resource.refunds | 41318 | 35318 | 6000 |
| g18 | 170 | INVOICE_NOT_PAID | resource.status != 'paid' | 35318 | 32318 | 3000 |
| g19 | 172 | REFUND_WINDOW_EXPIRED | world.clock - resource.paid_at > timedelta(days=world.rules.refund_window_days) | 32318 | 17318 | 15000 |
| g20 | 174 | REFUND_AMOUNT_MISMATCH | operation.params['amount_cents'] != resource.refundable_amount_cents | 17318 | 14318 | 3000 |
| g21 | 176 | REFUND_METHOD_MISMATCH | operation.params['payment_method'] != resource.payment_method | 14318 | 11318 | 3000 |
| g22 | 183 | OWNER_IMMUTABLE | resource.role == 'owner' or operation.params['role'] == 'owner' | 21496 | 18496 | 3000 |
| g23 | 185 | MEMBERSHIP_NOT_ACTIVE | resource.status != 'active' | 18496 | 18496 | 0 |

| Operation | Allowed | Rejected | Policy allowed | Policy rejected |
| --- | --- | --- | --- | --- |
| cancel_renewal | 7347 | 16272 | 9376 | 14243 |
| change_member_role | 18496 | 3000 | 18496 | 3000 |
| change_plan | 4000 | 3899 | 4000 | 3899 |
| change_seats | 5295 | 6971 | 5295 | 6971 |
| get_invoice | 0 | 0 | 0 | 0 |
| get_organization | 0 | 0 | 0 | 0 |
| get_subscription | 6983 | 2922 | 6983 | 2922 |
| list_members | 0 | 0 | 0 | 0 |
| refund_invoice | 11318 | 30000 | 11318 | 30000 |

### Operation × actual rule matrix

| Operation | Guard | Allowed samples | Rejected samples | Passed | Vetoed |
| --- | --- | --- | --- | --- | --- |
| cancel_renewal | g01 | 7347 | 16272 | 23619 | 0 |
| cancel_renewal | g02 | 7347 | 16272 | 23619 | 0 |
| cancel_renewal | g03 | 7347 | 16272 | 23619 | 0 |
| cancel_renewal | g04 | 7347 | 16272 | 23619 | 0 |
| cancel_renewal | g05 | 7347 | 16272 | 23619 | 0 |
| cancel_renewal | g06 | 7347 | 16272 | 23619 | 0 |
| cancel_renewal | g07 | 7347 | 16272 | 20619 | 3000 |
| cancel_renewal | g09 | 7347 | 13272 | 11318 | 9301 |
| cancel_renewal | g16 | 7347 | 3971 | 9376 | 1942 |
| change_member_role | g01 | 18496 | 3000 | 21496 | 0 |
| change_member_role | g02 | 18496 | 3000 | 21496 | 0 |
| change_member_role | g03 | 18496 | 3000 | 21496 | 0 |
| change_member_role | g04 | 18496 | 3000 | 21496 | 0 |
| change_member_role | g05 | 18496 | 3000 | 21496 | 0 |
| change_member_role | g06 | 18496 | 3000 | 21496 | 0 |
| change_member_role | g07 | 18496 | 3000 | 21496 | 0 |
| change_member_role | g08 | 18496 | 3000 | 21496 | 0 |
| change_member_role | g22 | 18496 | 3000 | 18496 | 3000 |
| change_member_role | g23 | 18496 | 0 | 18496 | 0 |
| change_plan | g01 | 4000 | 3899 | 7899 | 0 |
| change_plan | g02 | 4000 | 3899 | 7899 | 0 |
| change_plan | g03 | 4000 | 3899 | 7899 | 0 |
| change_plan | g04 | 4000 | 3899 | 7899 | 0 |
| change_plan | g05 | 4000 | 3899 | 7899 | 0 |
| change_plan | g06 | 4000 | 3899 | 7899 | 0 |
| change_plan | g07 | 4000 | 3899 | 7899 | 0 |
| change_plan | g09 | 4000 | 3899 | 7899 | 0 |
| change_plan | g10 | 4000 | 3899 | 7899 | 0 |
| change_plan | g11 | 4000 | 3899 | 6928 | 971 |
| change_plan | g12 | 4000 | 2928 | 4000 | 2928 |
| change_seats | g01 | 5295 | 6971 | 12266 | 0 |
| change_seats | g02 | 5295 | 6971 | 12266 | 0 |
| change_seats | g03 | 5295 | 6971 | 12266 | 0 |
| change_seats | g04 | 5295 | 6971 | 12266 | 0 |
| change_seats | g05 | 5295 | 6971 | 12266 | 0 |
| change_seats | g06 | 5295 | 6971 | 12266 | 0 |
| change_seats | g07 | 5295 | 6971 | 12266 | 0 |
| change_seats | g09 | 5295 | 6971 | 12266 | 0 |
| change_seats | g13 | 5295 | 6971 | 9353 | 2913 |
| change_seats | g14 | 5295 | 4058 | 7324 | 2029 |
| change_seats | g15 | 5295 | 2029 | 5295 | 2029 |
| get_subscription | g01 | 6983 | 2922 | 9905 | 0 |
| get_subscription | g02 | 6983 | 2922 | 9905 | 0 |
| get_subscription | g03 | 6983 | 2922 | 9905 | 0 |
| get_subscription | g04 | 6983 | 2922 | 9905 | 0 |
| get_subscription | g05 | 6983 | 2922 | 6983 | 2922 |
| get_subscription | g06 | 6983 | 0 | 6983 | 0 |
| get_subscription | g07 | 6983 | 0 | 6983 | 0 |
| get_subscription | g09 | 6983 | 0 | 6983 | 0 |
| refund_invoice | g01 | 11318 | 30000 | 41318 | 0 |
| refund_invoice | g02 | 11318 | 30000 | 41318 | 0 |
| refund_invoice | g03 | 11318 | 30000 | 41318 | 0 |
| refund_invoice | g04 | 11318 | 30000 | 41318 | 0 |
| refund_invoice | g05 | 11318 | 30000 | 41318 | 0 |
| refund_invoice | g06 | 11318 | 30000 | 41318 | 0 |
| refund_invoice | g07 | 11318 | 30000 | 41318 | 0 |
| refund_invoice | g09 | 11318 | 30000 | 41318 | 0 |
| refund_invoice | g17 | 11318 | 30000 | 35318 | 6000 |
| refund_invoice | g18 | 11318 | 24000 | 32318 | 3000 |
| refund_invoice | g19 | 11318 | 21000 | 17318 | 15000 |
| refund_invoice | g20 | 11318 | 6000 | 14318 | 3000 |
| refund_invoice | g21 | 11318 | 3000 | 11318 | 3000 |

### Rejections and combinations

| Rejection | Count |
| --- | --- |
| CROSS_ORG_ACCESS | 2922 |
| CROSS_ORG_RESOURCE | 3000 |
| DUPLICATE_REFUND | 6000 |
| INVOICE_NOT_PAID | 3000 |
| OWNER_IMMUTABLE | 3000 |
| PERMISSION_DENIED | 9301 |
| REFUND_AMOUNT_MISMATCH | 3000 |
| REFUND_METHOD_MISMATCH | 3000 |
| REFUND_WINDOW_EXPIRED | 15000 |
| SEATS_BELOW_MEMBERS | 2029 |
| SEAT_LIMIT_EXCEEDED | 4957 |
| SUBSCRIPTION_NOT_ACTIVE | 4855 |
| UNAUTHORIZED_OPERATION | 3000 |

| Actually visited business guard set | Count |
| --- | --- |
|  | 5922 |
| g08+g22 | 3000 |
| g08+g22+g23 | 18496 |
| g09 | 16284 |
| g09+g10+g11 | 971 |
| g09+g10+g11+g12 | 6928 |
| g09+g13 | 2913 |
| g09+g13+g14 | 2029 |
| g09+g13+g14+g15 | 7324 |
| g09+g16 | 11318 |
| g09+g17 | 6000 |
| g09+g17+g18 | 3000 |
| g09+g17+g18+g19 | 15000 |
| g09+g17+g18+g19+g20 | 3000 |
| g09+g17+g18+g19+g20+g21 | 14318 |

| Derived potential multiple vetoes (not exercised interaction) | Count |
| --- | --- |
| g07+g16 | 971 |
| g09+g16 | 1286 |
| g11+g12 | 628 |
| g13+g14 | 971 |
| g13+g15 | 971 |
| g17+g18 | 6000 |
| g18+g21 | 3000 |
| g19+g20 | 3000 |
| g19+g21 | 3000 |

Business guard sets exclude g01–g07 existence/integrity/scope gates. Co-visitation is coverage of a decision path, not proof that all constraints independently affected the outcome. Derived multiple vetoes evaluate actual AST predicates with reconstructed prerequisite locals, including masked constraints; missing prerequisites are Unknown. They never replace a reference verdict or count as exercised vetoes. No causal cross-rule interaction is inferred solely from co-visitation; dependency edges provide separate evidence of changes in legality.

Never visited guards: []. Never vetoed guards: ['g01', 'g02', 'g03', 'g04', 'g06', 'g08', 'g10', 'g23']. Invariant error inventory: ['BROKEN_RELATIONSHIP', 'DUPLICATE_MEMBERSHIP', 'DUPLICATE_REFUND', 'DUPLICATE_REFUND_ID', 'ENTITY_ID_MISMATCH', 'INVALID_CLOCK', 'INVALID_PAYMENT_TIME', 'INVALID_PLAN', 'INVALID_PLAN_CONFIG', 'INVALID_REFUNDABLE_AMOUNT', 'INVOICE_INCONSISTENT', 'OWNER_INCONSISTENT', 'REFUND_AMOUNT_MISMATCH', 'REFUND_METHOD_MISMATCH', 'REFUND_WINDOW_EXPIRED', 'SEATS_BELOW_MEMBERS', 'SEAT_LIMIT_EXCEEDED', 'SUBSCRIPTION_INCONSISTENT']. Generated/reference states satisfy invariants, so corruption guards are not expected to veto. Core tests exercise invalid-state and parameter cases separately; this is scenario-population coverage, not test-suite coverage.

## Split overlap

The repository ships a frozen public validation manifest, generator configurations and a training stream; no frozen standard train task set or private task test set is shipped. The existing validator prevents identical world/business instances across splits. It also enforces a real world-level holdout: one user is active billing_admin in an active-subscription organization with eligible invoice, and active member elsewhere with expired subscription and stale invoice. Train homogeneous subscription status excludes it; composed test forces it. This is stronger than seed separation, but does not enforce scenario-signature separation or require a task to use the held-out conjunction.

The following are audit-derived public demo manifests generated through the existing selector (12 scenarios/world), never a new official/blind test set. Configs, seed lists, hashes, per-split rule sets and signature distributions are in JSON.

- test: 100 worlds, 1200 tasks, 24 templates, 168 semantic classes, 100 heldout-conjunction worlds. Manifest `1c1570caa9653ce36b381e99e59c2a1110b267410196deb07b16312262b74b72`.
- train: 100 worlds, 1200 tasks, 23 templates, 175 semantic classes, 0 heldout-conjunction worlds. Manifest `cafc4fa67bcf2117f0890e4368949eaf7ce4a8cfbc6cb852577b0679f2d48f2f`.
- validation: 100 worlds, 1200 tasks, 24 templates, 183 semantic classes, 18 heldout-conjunction worlds. Manifest `676cfcd32d1aa4d62dfb05481ae609f9083589f3419fdefc52b3bc4134a3524a`.

| Pair | Level | Common | Left unique | Right unique | Jaccard | Right classes seen left | Right tasks seen left | Right-only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train_vs_test | template | 23 | 23 | 24 | 95.83% | 95.83% | 99.75% | 1 |
| train_vs_test | semantic | 132 | 175 | 168 | 62.56% | 78.57% | 94.25% | 36 |
| train_vs_validation | template | 23 | 23 | 24 | 95.83% | 95.83% | 99.92% | 1 |
| train_vs_validation | semantic | 145 | 175 | 183 | 68.08% | 79.23% | 94.50% | 38 |
| validation_vs_test | template | 24 | 24 | 24 | 100.00% | 100.00% | 100.00% | 0 |
| validation_vs_test | semantic | 138 | 183 | 168 | 64.79% | 82.14% | 95.83% | 30 |

- train_vs_test: right-only actual visited rule sets []; right-only dependency operation pairs [].
- train_vs_validation: right-only actual visited rule sets []; right-only dependency operation pairs [].
- validation_vs_test: right-only actual visited rule sets []; right-only dependency operation pairs [].

Actual shipped validation: 2 worlds / 24 tasks; seeds [1000000, 1000001]; 13 templates and 21 semantic classes. Manifest `810a668b341815cc5d23000c076b513e9ba3d08acb99e5458ce771fa1bc864f5`.

## Diversity bottlenecks and recommendations

**Confirmed:** 79699/82699 candidates involve one organization. Candidate chains have lengths ['1', '2', '5']; multi-step construction is limited to repeat refund, plan/seat downgrade and role/billing families (`scenario.py`). Cross-scope rejections are single-step cases, not cross-organization causal workflows. World topology diversity therefore substantially exceeds the local task variety measured here.

**Confirmed:** get_organization, get_invoice and list_members have zero candidate occurrences. Inactive memberships occur in worlds but role-change targets are selected only from active memberships. Role changes are requested by owners; billing-admin/member role-management denial is absent. Unknown actor/org/resource and invalid plan cases are absent because constructors select real references/plans. g01/g02 are integrity policy guards, for which intentionally corrupting benchmark worlds would be a different evaluation track.

**Confirmed:** invoices are independent organization-owned records; no invoice–subscription billing-cycle link exists. No operation changes active-member count, pays an invoice, activates/renews a subscription or advances frozen time. These states cannot be reached by randomly concatenating current operations. Engine/Oracle remain unchanged.

**Likely:** routine service goal diversity and compositional transfer are constrained by these constructor families. The overlap data support this concern, but predict neither LLM accuracy nor exploit yield.

**Not yet measurable:** exhaustive theoretical signature count, direct causal rule interaction, customer attack novelty, LLM capability, information-flow dependencies and real private-test overlap. These require exhaustive domain enumeration, purpose-built causal tasks, measured agent trajectories or access to an actual private test manifest.

See `ROADMAP.md` for versioned Service-goal evaluation versus open-ended discovery, causal generation and prioritized subsystem proposals. This audit adds no business operations or benchmark scoring changes.

## Verification and limits

All 116503 candidate steps were recomputed through real ReferenceRules and matched generated labels and expected state hashes. 24 distinct template representatives additionally used actual Engine execution, trusted-request Oracle evaluation and exact event replay; every check passed. This subset is explicitly smaller than the full candidate pool. Demo splits and shipped validation were also reference checked.

No Engine, Generator, Reference Rules or Oracle files are edited; their source SHA256s are frozen in the results. Tests, exact invocation, artifact digest and known limitations are recorded in `VERIFICATION.md`. Finite seeds do not prove asymptotic saturation. Abstraction choices are versioned and inspectable: changing their granularity changes the measured number of classes.
