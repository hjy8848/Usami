# SaaS business dependency specification (v0.2)

All amounts are integer cents, time is frozen, and the payment provider is a local deterministic simulator. No external money moves. Owners provision access for existing directory users; activation is an administrator action, not impersonated invitation acceptance.

| Operation | Motivation and actor | Preconditions / negative branches | State and invariant | Compound causal use |
|---|---|---|---|---|
| invite_member | Owner provisions a known user's account | Own org; known user; member/billing role; duplicate pending is idempotent, active/inactive duplicate rejected | Adds pending membership; unique org/user; owner preserved | Invitation -> activation |
| activate_member | Owner enables a pending or suspended account | Active subscription; available seat; pending/inactive target; owner protected | status active; active count <= seats | Plan -> seats -> activation; payment -> restoration -> activation |
| deactivate_member | Owner suspends a departing account | Active non-owner target | status inactive; capacity requirements decrease | Deactivation -> seats -> downgrade |
| remove_member | Owner deletes an unused provisioning record | Pending/inactive non-owner; active must be suspended first | Deletes membership; owner and other tenant preserved | Deactivation -> removal; suspended user may be re-invited |
| change_plan / change_seats | Owner or billing admin adjusts cost/capacity | Active subscription; known plan; seats between active count and plan cap | Changes only plan/seats | Existing bidirectional capacity prerequisites |
| issue_renewal | Owner or billing admin requests the next service invoice | Deterministic cycle: active end or frozen clock after expiration; identical invoice creation is idempotent | Adds linked renewal invoice, configured price per seat; unique subscription/period/purpose | Issue -> payment -> renewal/restoration |
| pay_invoice | Owner or billing admin settles a linked invoice | Known simulated method; idempotency key scoped to invoice; an already paid invoice only accepts exact replay | Records failure or one full successful payment; same key+method returns original outcome; key conflict rejected | Failure -> corrected method with fresh key -> restoration |
| renew_subscription | Owner or billing admin extends service | Active; matching next-cycle renewal invoice paid and completely unrefunded | Extends end; links funding invoice; no double extension | Issue -> pay -> renew -> activate |
| reactivate_subscription | Owner or billing admin restores expired service | Expired; matching renewal cycle starts at frozen clock; invoice paid and unrefunded | Sets active, period and funding invoice; capacity unchanged | Pay -> restore -> expand seats -> activate |
| expire_subscription | Owner or billing admin records elapsed service | Frozen clock >= period end; active future cycle rejected | expired, auto-renew false | Explicit clock-derived lifecycle (no wall-clock advancement) |
| refund_invoice | Owner or billing admin corrects a charge | Paid/partially refunded; positive amount <= remaining; original method; <=14 days; scoped idempotency key | Remaining = amount - cumulative refunds; total never exceeds single payment; duplicate exact replay no mutation | Partial refund and bounded follow-up; over-refund refusal |
| change_member_role | Owner grants billing privileges | Active non-owner; cannot assign owner | Role only, no capacity change | Permission-sensitive tasks; never substitutes for deactivation |
| query tools | Authenticated active tenant member; invoices require billing role | Scope and role validated for each resource | No mutation or data on rejection | Service independently discovers state and resources |

Simulated methods `card_visa`, `card_mastercard`, `bank_transfer` succeed; `card_declined` records a failed attempt. Failure is a successful recording operation with an explicit payment outcome, not a settled invoice. A fresh key is required to change the method after failure. Successful payments and refunds have deterministic IDs derived from invoice and key; exact replay returns original data.

Invoices link to a subscription and a 30-day billing period. Historical invoices remain separate accounting records. Only the deterministic next renewal period can extend/restore service. Refunds do not silently roll back a service contract; access changes require separate authorized operations. No credit ledger is introduced: partial-refund accounting already provides meaningful bounded financial behavior without unexplained money creation.

The Reference specification and Engine transition implementation are separate. Counterfactual plan omission and bounded domain-wide prerequisite exclusion establish different levels of causal evidence. Search limits are reported; bounded failure is never a policy impossibility certificate.

Registered user IDs and display names are a public user directory in this fictional SaaS. Email addresses are projected only through the authenticated profile or accessible tenant roster. In v0.2, invoice-ID discovery and roster/directory projections are returned as core query data, so independent Reference and Oracle checks cover the whole projection.

An active subscription flag can briefly remain after its period ends (scheduler lag). This is a consistent elapsed state: activation and capacity writes still require period_end after frozen time. expire_subscription records expiration; an elapsed contract cannot be renewed as a live contract and must use the restoration path.
