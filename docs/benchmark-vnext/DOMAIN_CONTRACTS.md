# Eight-domain contracts and current implementation boundary

The common source contract is `WorldSpec → FrozenWorld → isolated runtime World`. Current generator bindings exist for the four Track A domains only. The four Track B business contracts below are implementation requirements, not claims of completed native modules.

## Shared task and evidence obligations

A task must select an existing registered world, an existing actor, permitted observable objects, an objective joint goal and a finite operation scope. The task composer must prove completion through actual native transitions, or verify a specific native policy refusal. A private witness is proof material and not a prescribed Service route.

Mixed tasks must carry independently evaluable completion/refusal subgoals and a joint frame. A failed allowed subgoal is not excused merely because a different subgoal was correctly refused. Illegal successful side effects, blocked attempts, invalid task proposals, query errors and uncertain attribution remain separate facts.

Every dialogue task also requires a frozen Customer profile and an independently proved information/consent dependency. The profile cannot authorize fabricated entities, retroactive objective fact changes, arbitrary preference drift or hidden reference-path disclosures. A necessary process fact changes the actual allowed action set; conversation length is descriptive only.

## Track A — existing native business contracts

| Domain | State/authority | Native constraints | New generator status |
| --- | --- | --- | --- |
| SaaS | Directory, organizations, memberships, subscriptions, invoices, payments/refunds | Owner protection, tenant isolation, active seat limits, funding cycles, refund accounting | Existing unconditioned v0.2 distribution registered; 100-world audit passed |
| CloudOps | Users, organizations, projects, role edges, instances, dependency DAG, invoices | Project-local compute role, quota, prerequisite instances, suspended project, payment/resume separation | New independent structural distribution; 100 valid audited worlds |
| Fulfillment | Organizations, warehouses/roles, SKU/lots, receipts, orders, allocations, handling, shipments, returns and ledger | Conserved stock, quality, capacity, warehouse scope, attested delivery/inspection, refund eligibility | New topology plus actual lifecycle distribution; 100 valid audited worlds |
| StayOps | Property/roles, guests, physical rooms, date capacity, rate plans, reservations, assignment, stays and payments | Half-open dates, capacity, cleanliness, maintenance, quote/deposit, identity, cancellation terms | New topology/calendar/lifecycle distribution; 100 valid audited worlds; native checkout consistency limitation retained |

Existing Service and Customer interactions remain available. Describing Track A as tool-centric does not mean these environments have no dialogue.

## Track B — required native rules to implement next

### After-sales

Different order lines may have distinct problem evidence, delivery dates, remaining refund balance and replacement inventory. Case evidence must bind to the selected order/line and independently simulated evidence result. Return, refund, replacement and reshipment must have different dependencies. Refund money must follow the original payment channel, remain bounded by actual eligible paid balance and be idempotent. Ineligibility or another person's order must cause an exact refusal. Irreversible settlement needs actual current consent; a stale resolution choice must not settle.

Required private dependencies include selecting which of multiple real orders/lines is meant, describing the issue, supplying evidence held by the customer, expressing time/option constraints and confirming the actual offer. Existing entity facts come from the independently generated world; no Service or Designer may invent verification success.

### Airline

A passenger booking refers to real legs, fare rights and original charges. Change quotes must respect seat capacity, travel dates, airport continuity and minimum connection time. Price difference and change fees are deterministic. Carrier disruption and voluntary cancellation are distinct branches. Ancillaries remain tied to the actual passenger/itinerary. Irreversible exchange/cancellation requires current explicit confirmation; ambiguous intent cannot cancel the ticket.

Missing itinerary/date/arrival-limit/budget and alternative itinerary preferences affect legal choices. New disruption or seat events must be pre-registered simulator events, not invented agent messages.

### Property

A unit has real occupants/owner/contract scope, equipment and maintenance responsibilities. Incidents have objective simulator facts, priority and required technician skills. Scheduling must fit agreed household windows, technician availability, skills and absence of existing conflicts. Structural/chargeable work may require independent owner approval. Completion requires real simulated technician evidence; a Service assertion cannot complete a job. Complaint escalation is separate from actual repair.

Customer disclosure selects location/fault facts; severity updates, accessible time windows, charge confirmation and owner approval alter the permissible action set. Another household's private information is never a valid query result.

### Education

Contracts bind paid enrollment, consumed lessons, validity, course rights and refund arithmetic. Transfers consume real class capacity and must respect teacher/time constraints. Deferral/extension rights are bounded by actual terms. Refunds must account for consumed service and prior refunds; arbitrary discounts or approvals are not allowed. Scheduling and progress adjustments need separate legal transitions rather than four renamed refund workflows.

The customer may initially describe dissatisfaction without disclosing the actual reason or intended resolution. Clarified schedule, objective progress, preferred alternatives and explicit current consent determine valid changes. Previously withdrawn or superseded choices cannot be executed later.

## Runtime boundaries still to connect

The implemented `usami_dialogue` reducer verifies private-value provenance, preferences and consent scope, but does not yet validate these four industries' quotes or execute native business actions. Native domain callbacks, Engine/Oracle traces, mixed task proofs, Customer/Service sessions and unified adapters are mandatory remaining work. No common CRUD facade is an acceptable substitute.

## Executable After-sales core

The After-sales implementation (`usami_aftersales/`) is an order-line dispute state machine, with merchant-scoped ownership, simulated evidence verification, refund approval limits, paid-value/original-channel accounting, replacement stock conservation, pickup and verified receipt. Its native operations implement open-case, evidence verification, approval request, actual quote, consent-bound settlement, return scheduling and refund release. Scoped read tools expose the actual order/case/options without private profile or simulator outcomes.

The Customer profile chooses a real buyer/order/line, immutable problem/evidence facts, deadline and acceptable resolution space before execution. A Customer declaration can itself supply exact facts; missing-information rules must not manufacture extra turns after those facts have been supplied. The production model chooses whether to clarify, compare, revise, confirm or finish. Manager/carrier events have pre-registered outcomes and independent expected/actual handlers.

The current domain task contract allows actual terminal line states and explicit duplicate-resolution refusal subgoals. Frames are supplied by the domain binding and cannot be broadened by a task proposal. Native Reference search is private certification; production execution remains autonomous. Current fixtures cover two different valid resolution paths, a legal extra-query path, a mixed completion/refusal goal, consent and preference boundaries, premature Sandbox settlement, and actual simulator receipt/approval dependencies.

This is not a claim of full After-sales coverage: historical initial case distributions, richer account choices, full cross-order/multi-entity task families and the final Reference decision matrix remain under development. The three other Dialogue-Centric domains remain unimplemented at this checkpoint.

## Explicit StayOps correction version

`stayops-structural-v2` binds `stayops-0.2.0` under `usami_benchmark/native/stayops_v2/`. A currently dirty unoccupied room can have an assignment for a future arrival; actual assignment/check-in cleanliness checks and the prohibition on a currently occupied dirty room remain. This resolves the legacy checkout-versus-future-assignment invariant conflict. Both historical native `stayops-0.1.0` and the first structural generator remain available under their original explicit registrations; old traces are not re-scored under the new invariant.
