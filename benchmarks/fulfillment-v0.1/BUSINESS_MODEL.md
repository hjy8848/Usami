# FulfillmentOps v0.1 business model

This is a simulated enterprise inventory, fulfillment and returns platform. It
does not contact a carrier, merchant, bank or real warehouse.

Organizations own warehouses and products. Organization owners manage their
own warehouses. Manager, picker, receiver, finance and viewer grants are scoped
to one warehouse. A buyer can manage its own order and request a return; order
ownership grants no picking, receiving or warehouse inventory privileges.

Each lot has shelf `on_hand` (including `reserved`), `reserved`, picked staging
`picked` (including packed goods), and QA status. Available is released-quality
`on_hand - reserved`. Gross shipped quantity is independently derived from
dispatched/delivered shipments. Supplier receipts, transfers, reservations,
handling records, shipments and restocked returns independently reconcile
physical inventory. Incoming quarantined returns occupy warehouse volume.

Payment must cover current uncanceled goods plus shipping before confirmation.
Reservations allocate a confirmed order line without double allocation or
overcommitting stock. Picking physically moves goods from shelf to staging.
Packing creates a separate record. A shipping label may be prepared before or
after handling, but dispatch requires every linked allocation to be packed.
After dispatch, ordinary cancellation cannot reverse goods in transit. Partial
cancellation can release unshipped free or reserved quantities. Packed goods
require label cancellation, unpacking and unpicking before ordinary cancellation.

Transfers debit released source stock into transit; destination receipt credits
stock only once and checks scoped permissions, organization, receiving switch,
product category and physical capacity. Receiving supplier notices consumes a
unique notice and immutable key. Keys for charges/refunds, shipments, transfers
and supplier receipts cannot be reused with different business values.

Delivery, payments and inspections use deterministic host simulator notices.
No tool accepts a caller-selected external actor, raw attestation, payment
outcome or inspection grade. Payment tokens `card_approved` and `card_declined`
select known simulator scenarios. Product fixtures privately determine physical
inspection condition, independent of the customer's claimed return reason.
These notices are deterministic checksums and provenance bindings for simulation,
not production cryptographic signatures. The frozen clock is authoritative.

Returns require delivered quantity, returnable products and the product window.
Receipt moves goods into quarantine, inspection independently decides resalable,
scrapped and refundable units, and restocking moves accepted units back to the
original lot. Merchant fault can permit a refund without restocking; customer
damage permits neither. Refunds are bounded by successful payments and canceled
or independently inspected eligible goods. Dispatched shipping fees are retained.

Reference decisions construct complete expected snapshots without importing the
actual applier. The actual applier independently mutates buckets and records.
Oracle checks rules, whole expected snapshots, invariants, external notices and
independent single-use customer authority. Sandbox bypasses business checks for
writes, while scoped reads retain their authorization and business checks. A
rejected attempt, successful business violation, authority-only anomaly and
unscored operation on a previously invalid world are distinct evidence classes.

Limitations: instantaneous deterministic simulated external events; one currency;
no carrier delay, tax, backorder, purchasing contract or inventory costing model;
fixed product prices; no real identity or payment network. Realism ratings remain
**AWAITING HUMAN REVIEW**.
