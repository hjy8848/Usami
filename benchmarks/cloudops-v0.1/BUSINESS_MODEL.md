# CloudOps business specification

All entities and transitions are simulated, deterministic and project scoped. CPU, memory, counts and cents are strict integers. The clock is fixed at 2026-01-15T12:00:00Z. Generation includes an immutable organization owner identity, explicit project grants, instance DAGs, current invoice pointers and deterministic payment ledgers.

## Permission matrix

| Capability | Org Owner in this organization | Project Admin | Operator | Viewer |
|---|---|---|---|---|
| Read project, resources and members | Yes | Yes | Yes | Yes |
| Read invoice/payment ledger | Yes | Yes | No | No |
| Start / stop compute | Explicit Admin/Operator grant required | Yes | Yes | No |
| Create / delete / edit dependencies | Explicit Admin grant required | Yes | No | No |
| Change quota / pay / resume | Yes | Yes | No | No |
| Grant / revoke Operator or Viewer | Yes | Yes | No | No |
| Grant / change / revoke Admin | Yes | No | No | No |

Organization ownership is not modified by access operations. Joining another project conveys no permission here. The Owner's ability to grant itself an operational role enables the fixed-single-actor grant → operation dependency; Service never switches authenticated users. Role lookup uses the project/user tuple, independent of access-record ID spelling. Public directory contains fictional user IDs/names only.

## Writes, preconditions and effects

| Write | Required conditions beyond permission | Changed fields and retry behavior |
|---|---|---|
| `create_instance` | Known project; new instance ID or identical stopped definition | Adds stopped instance with empty dependencies. Identical creation is a no-op; conflicting definition rejects. |
| `start_instance` | Active project; direct dependencies running; CPU/memory/count all fit quota | Sets only this instance running. Already-running request is a no-op. |
| `stop_instance` | No running instance directly depends on this resource | Sets only this instance stopped. Already-stopped request is a no-op. |
| `delete_instance` | Instance stopped; no incoming dependency edge, even from a stopped instance | Removes only this instance. Missing instance rejects; edges must be detached first. |
| `attach_dependency` | Both resources in requested project; dependent stopped; resulting graph acyclic | Adds one edge, preserving others. Existing edge is a no-op. |
| `detach_dependency` | Both resources exist in requested project; dependent stopped | Removes specified edge. Absent edge is a no-op. |
| `change_project_quota` | Nonnegative bounded CPU/memory/count; each new limit ≥ current running usage | Changes only requested project's quota. Same quota is a no-op. |
| `grant_project_access` | Known user; Admin ceiling; unique scoped grant | Adds or updates one grant. Same role is a no-op. Record-ID collision rejects. |
| `revoke_project_access` | Existing scoped grant; Admin ceiling | Removes one grant. Missing grant rejects. Organization owner identity remains fixed. |
| `pay_invoice` | Invoice belongs to requested project; immutable invoice-scoped key/parameters; no second successful charge | Approved card records paid; declined card records failed. Same-key/same-method returns original result without charging; changed method rejects; paid invoice with new key rejects. |
| `resume_project` | Supplied invoice is the project's current invoice and is paid | Sets only requested project active. Payment alone does not resume. Already-active request is a no-op if invoice is valid. |

Each operation preserves all unrelated entities/fields. Reference rejects unknown resources, wrong scopes, missing roles, invalid input, exhausted or mismatched single-use Customer authority and the listed business conditions. Declined payment is a successfully processed business operation with `outcome=failed`, not a successful payment. A fresh approved payment key can recover a failed invoice; retrying the declined key retains the original failure.

Reads are `get_project`, `list_instances`, `get_instance`, `get_invoice`, `get_project_members`, plus scoped `get_customer_context`. Query authorization is enforced in both execution modes. Viewer sees project topology and quota but not invoices; other tenants remain hidden. No tool returns full WorldState.

## Independent specification, actual execution and Oracle

`rules.decide` computes legality and an independently cloned expected transition. It never imports Engine or `transitions.apply`. The actual applier is a separate implementation. Reference checks trusted Customer authority and rules before actual mutation. Sandbox writes bypass those business/authority checks but still enforce typed schemas, resource existence and representability. Sandbox does not create imaginary resources or skip actual mutations.

Oracle recomputes expected legality/state/data and checks actual snapshots, request authority, hash chains, budget and final-state integrity. Invariants cover unique scoped access, local acyclic non-dangling dependencies, running dependency consistency, quota in all three dimensions, suspended resource starts, active-but-unpaid projects, invoice accounting, duplicate charges and immutable payment outcomes. Exact transition comparison detects changes to unrelated projects even when resulting global invariants still hold.

Operation classes are `legal_execution`, `rejected_invalid_attempt`, `successful_business_violation`, `authorization_only`, `false_rejection`, and `unscored`. An illegal call correctly denied by Reference is not a successful business violation. A legal business transition lacking Customer intent is authorization-only. Following an already-invalid Sandbox state, Reference is undefined (`INVALID_WORLD`); later operations are unscored for new business legality, while actual invariant failures remain recorded. Discovery findings use only actual successful business violations and deduplicate semantic decision signatures.

## Causal examples

Billing recovery: approved invoice payment → resume project → start database. Removing payment causes `INVOICE_NOT_PAID`, and removing resume causes `PROJECT_SUSPENDED`. Capacity: increase quota → start web; removing quota increase causes `QUOTA_EXCEEDED`. Topology: database → application → web startup; missing predecessor causes `DEPENDENCY_NOT_RUNNING`. Retirement: stop dependent, stop database and detach dependent's edge in permitted orders, then delete database; omitted predecessors cause running/reference violations. Scoped authorization: Owner grants itself Operator for staging → starts database; omission causes `PROJECT_ACCESS_REQUIRED` without actor switching.

These are host-side reachability/omission certificates, not instructions to Service. Goals include preservation frames and permit alternative terminal quotas and legal orderings. Successful detached-but-running replacement without its required edge fails the conjunctive Goal even when all executed operations are individually legal.
