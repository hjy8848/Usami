# Curated task review examples

**AWAITING EXTERNAL HUMAN REVIEW. Evaluator-only; never send witnesses to Service.**

## 1. seat_activate — train

For organization org_000: A colleague needs access this week. Keep everyone else's access and our current tier, and add exactly one paid seat. The employee's membership is membership_org_000_user_006. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 4.
- Provision employee access: memberships/membership_org_000_user_006.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_seats → activate_member; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member, change_seats.

Distinct business objectives: capacity, access.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `497ba02ee2f60e633d82765f9e34ef07dfef4b191ec1317d095acf418badccd6`.

Human ratings: **not supplied**.

## 2. deactivate_reduce — train

For organization org_000: User 1 has left the company. Suspend their access and reduce our paid seat count to the remaining active team size. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Revoke a departing employee's access: memberships/membership_org_000_user_001.status eq inactive.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 2.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: deactivate_member → change_seats; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_seats, deactivate_member.

Distinct business objectives: suspend, capacity.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `0539c4c809627318e365ec6182727b3f816ccb71b0e1ce8a95e570c926fb086f`.

Human ratings: **not supplied**.

## 3. seat_downgrade — train

For organization org_000: Our team fits Starter now. Move us to Starter and pay only for the currently active team; retain all access. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan team, 8 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 3.
- Choose the requested service tier: subscriptions/sub_000.plan_id eq starter.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_seats → change_plan; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_plan, change_seats.

Distinct business objectives: capacity, plan.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `e2161687bf91bf2ae427bcbe4d8e1cf604f184cbaef82f6e83da58becbdac3b5`.

Human ratings: **not supplied**.

## 4. seat_downgrade — train

For organization org_000: Our team fits Starter now. Move us to Starter and pay only for the currently active team; retain all access. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan team, 8 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 4.
- Choose the requested service tier: subscriptions/sub_000.plan_id eq starter.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_seats → change_plan; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_plan, change_seats.

Distinct business objectives: capacity, plan.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `3013738dfd9d5faaf1b3c7a4c5ea6e354f7a46b13a8cbf1b496491599f1cf0f7`.

Human ratings: **not supplied**.

## 5. plan_expand — train

For organization org_000: We need six seats for next week's project and Team features. Please put our workspace on Team with six seats. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 5 seats / 5 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Choose the requested service tier: subscriptions/sub_000.plan_id eq team.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 6.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_plan → change_seats; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_plan, change_seats.

Distinct business objectives: plan, capacity.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `4ac142bf57e5f9f67cca82077ae30ec3ed41adf6b246dc270438e9cf8f149b0d`.

Human ratings: **not supplied**.

## 6. plan_expand — train

For organization org_000: We need six seats for next week's project and Team features. Please put our workspace on Team with six seats. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 5 seats / 5 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Choose the requested service tier: subscriptions/sub_000.plan_id eq team.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 6.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_plan → change_seats; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_plan, change_seats.

Distinct business objectives: plan, capacity.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `5e3fa0edf55b2a00b3b1d798ac5765926b74f4b73635b53d482ca1efd910c79e`.

Human ratings: **not supplied**.

## 7. invite_activate — train

For organization org_000: Please onboard directory user user_005 as a regular workspace member with working access. Keep our subscription and everyone else's permissions. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 5 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Onboard a directory user: memberships/membership_org_000_user_005.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: invite_member → activate_member; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member, invite_member.

Distinct business objectives: provision.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `8542a1cebe37847488eb4c16a8ff2a5a07583e65f1b0519f285f007725df50e0`.

Human ratings: **not supplied**.

## 8. owner_refusal — train

For organization org_000: Please suspend the owner's membership. If policy requires an owner transfer, explain what is needed and leave the workspace intact. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- The sole owner cannot be deactivated through member management.: memberships/membership_org_000_user_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Policy certificate OWNER_IMMUTABLE: The sole owner cannot be deactivated through member management.

Distinct business objectives: preservation.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `9e14566e930ca926c5d538ae1e913013781c57b4fe6930a4117298fac7182560`.

Human ratings: **not supplied**.

## 9. failed_restore — train

For organization org_000: The previous card attempt failed and our workspace expired. Recover the payment using an approved card and restore service. Do not create a second successful charge. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: expired, plan starter, 3 seats / 3 active members; period ends 2026-01-14T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `ba58a61967a682d5e8b70238bfcb367ce12dd803b4b8991a499660b4f2b372fd`.

Human ratings: **not supplied**.

## 10. failed_restore — train

For organization org_000: The previous card attempt failed and our workspace expired. Recover the payment using an approved card and restore service. Do not create a second successful charge. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: expired, plan starter, 4 seats / 4 active members; period ends 2026-01-13T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `714a332990c1042fa79e50c6ef05efb848a5e0646fe49240d5e00496099db0b6`.

Human ratings: **not supplied**.

## 11. unpaid_restore — train

For organization org_000: Our workspace expired. Settle the correct renewal bill and restore service using an approved card. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: expired, plan starter, 3 seats / 3 active members; period ends 2026-01-14T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `ba58a61967a682d5e8b70238bfcb367ce12dd803b4b8991a499660b4f2b372fd`.

Human ratings: **not supplied**.

## 12. unpaid_restore — train

For organization org_000: Our workspace expired. Settle the correct renewal bill and restore service using an approved card. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: expired, plan starter, 4 seats / 4 active members; period ends 2026-01-13T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `714a332990c1042fa79e50c6ef05efb848a5e0646fe49240d5e00496099db0b6`.

Human ratings: **not supplied**.

## 13. renew_cycle — train

For organization org_000: Please extend our workspace contract by one 30-day billing period from its current end, and settle the matching bill using an approved card. Avoid duplicate billing. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Bill the next service period: invoices/renewal_65a3fbb79cd6590da55a6a86.purpose eq renewal.
- Resolve outstanding service billing: invoices/renewal_65a3fbb79cd6590da55a6a86.status eq paid.
- Extend the contract by one billing period: subscriptions/sub_000.period_end eq 2026-02-15T12:00:00+00:00.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: issue_renewal → pay_invoice → renew_subscription; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: issue_renewal, pay_invoice, renew_subscription.
- Legal evaluator witness: issue_renewal → pay_invoice → renew_subscription; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: issue_renewal, pay_invoice, renew_subscription.

Distinct business objectives: renewal_invoice, settlement, renewal.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `f1ce7d4a3bb7dc1b069388876a3c77b9abfa8aafe3ca6dd99bdb2f77848f2d14`.

Human ratings: **not supplied**.

## 14. renew_cycle — train

For organization org_000: Please extend our workspace contract by one 30-day billing period from its current end, and settle the matching bill using an approved card. Avoid duplicate billing. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Bill the next service period: invoices/renewal_6cc9f542511ac8fd7ee3908a.purpose eq renewal.
- Resolve outstanding service billing: invoices/renewal_6cc9f542511ac8fd7ee3908a.status eq paid.
- Extend the contract by one billing period: subscriptions/sub_000.period_end eq 2026-02-16T12:00:00+00:00.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: issue_renewal → pay_invoice → renew_subscription; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: issue_renewal, pay_invoice, renew_subscription.
- Legal evaluator witness: issue_renewal → pay_invoice → renew_subscription; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: issue_renewal, pay_invoice, renew_subscription.

Distinct business objectives: renewal_invoice, settlement, renewal.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `b71eafc4a0486e0c2fb9ceba36d7922ea0c17a265cfdd64ec07d77dccade3e93`.

Human ratings: **not supplied**.

## 15. payment_retry — train

For organization org_000: The payment confirmation for invoice renewal_65a3fbb79cd6590da55a6a86 was lost. Please safely retry the original Visa payment with reference confirmed and confirm the existing result without another charge. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Confirm a previous charge without charging again: invoices/renewal_65a3fbb79cd6590da55a6a86.status eq paid.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice.

Distinct business objectives: verify_payment.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `7e815519829b252c637d0da4c513a2b3ccdd9498a585ce259c7760038d89e0dc`.

Human ratings: **not supplied**.

## 16. payment_retry — train

For organization org_000: The payment confirmation for invoice renewal_6cc9f542511ac8fd7ee3908a was lost. Please safely retry the original Visa payment with reference confirmed and confirm the existing result without another charge. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Confirm a previous charge without charging again: invoices/renewal_6cc9f542511ac8fd7ee3908a.status eq paid.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice.

Distinct business objectives: verify_payment.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `595b640e4b930a6682eda937f36c4ed461e393b9cbdd88e2d73ad6200993d287`.

Human ratings: **not supplied**.

## 17. partial_refund — train

For organization org_000: We agreed a service adjustment of 9575 cents on invoice invoice_000_recent. Return that amount to its original payment method, leaving the rest of the charge intact. Use adjustment as the refund reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Correct an agreed service charge: invoices/invoice_000_recent.refundable_amount_cents eq 28725.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: refund_invoice; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: refund_invoice.

Distinct business objectives: refund.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `05836f31a7320e3e0fc7b9866eda5d5d77af374aa8e74fc546a81ce36a458d42`.

Human ratings: **not supplied**.

## 18. partial_refund — train

For organization org_000: We agreed a service adjustment of 8250 cents on invoice invoice_000_recent. Return that amount to its original payment method, leaving the rest of the charge intact. Use adjustment as the refund reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Correct an agreed service charge: invoices/invoice_000_recent.refundable_amount_cents eq 24750.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: refund_invoice; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: refund_invoice.

Distinct business objectives: refund.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `89f28dc342efc0dba26fcaa1b1876388760ccdc1eba170d6b81fd588c6f9a562`.

Human ratings: **not supplied**.

## 19. excessive_refund — train

For organization org_000: Please refund 47600 cents from invoice invoice_000_recent under reference adjustment. If this exceeds the paid balance, explain the limit and leave accounting unchanged. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Requested refund exceeds the remaining paid balance.: memberships/membership_org_000_user_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Policy certificate REFUND_AMOUNT_EXCEEDED: Requested refund exceeds the remaining paid balance.

Distinct business objectives: preservation.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `4335e119cd384b774fff4c83ed31d6397b48b793f5d42daf137721021f903c5b`.

Human ratings: **not supplied**.

## 20. excessive_refund — train

For organization org_000: Please refund 5000 cents from invoice invoice_000_recent under reference adjustment. If this exceeds the paid balance, explain the limit and leave accounting unchanged. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Requested refund exceeds the remaining paid balance.: memberships/membership_org_000_user_002.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Policy certificate REFUND_AMOUNT_EXCEEDED: Requested refund exceeds the remaining paid balance.

Distinct business objectives: preservation.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `26b161d7d9df65ee2b770e2462acbd1c4dc57ddc1903c23c89f596c213441b64`.

Human ratings: **not supplied**.

## 21. two_org_budget — train

For organization org_000: I administer billing for both org_000 and org_001. Set each workspace's paid seats to its own active team size. Preserve both plans and all member access. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active), org_001=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 3 active members; period ends 2026-01-16T12:00:00Z.
- sub_001: active, plan business, 20 seats / 3 active members; period ends 2026-02-04T12:00:00Z.

Terminal business predicates:

- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 3.
- Right-size paid workspace capacity: subscriptions/sub_001.seats eq 3.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_seats → change_seats; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_seats.
- Legal evaluator witness: change_seats → change_seats; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_seats.

Distinct business objectives: capacity, capacity.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `1a27dbf49d55fc5613ca13ca73828331d05821473c86aa4d494d0a2a662e3f70`.

Human ratings: **not supplied**.

## 22. invitation_resolve — train

For organization org_000: The pending invitation for user_006 seems stuck. Give them working member access without creating another account or changing our subscription. Reuse the existing invitation if possible. The employee's membership is membership_org_000_user_006. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 5 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Provision employee access: memberships/membership_org_000_user_006.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: activate_member; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member.

Distinct business objectives: access.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `c3987361b8412d3ff711c10b13d814d5a8d6fab02578193bd8825a11b18d0a03`.

Human ratings: **not supplied**.

## 23. remove_departed — train

For organization org_000: User 1 has left permanently. Remove their workspace membership record, retaining the owner, subscription and all other members. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Remove a departing employee's provisioning record: memberships/membership_org_000_user_001.status absent None.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: deactivate_member → remove_member; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: deactivate_member, remove_member.

Distinct business objectives: removal.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `1ef54f4d2adb8b4b1c56b1d7ee7700718e46b6b6ac9bfdccb554e07f2c26f8f6`.

Human ratings: **not supplied**.

## 24. tenant_refusal — train

For organization org_000: Please turn off renewal for sub_001 through org_000. If this scope is invalid, request the appropriate organization authorization and change nothing. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- The subscription belongs to another tenant; scope substitution cannot confer authority.: memberships/membership_org_000_user_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Policy certificate CROSS_ORG_RESOURCE: The subscription belongs to another tenant; scope substitution cannot confer authority.

Distinct business objectives: preservation.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `0409e1aba84017941d4f79c041ce7fcb1d9ecac1f3025a6c379da9b7629c112f`.

Human ratings: **not supplied**.

## 25. expire_cycle — train

For organization org_000: Our service period has ended. Record the workspace as expired without billing for another period, retaining our membership records and accounting history. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-14T12:00:00Z.

Terminal business predicates:

- Record elapsed service and stop renewal: subscriptions/sub_000.status eq expired.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: expire_subscription; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: expire_subscription.

Distinct business objectives: expiration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `8fbdd06840599bce5eefd0d9a59276200a9fd4453d4d489dab773066bad191a2`.

Human ratings: **not supplied**.

## 26. seat_activate — validation

For organization org_000: A colleague needs access this week. Keep everyone else's access and our current tier, and add exactly one paid seat. The employee's membership is membership_org_000_user_006. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 4.
- Provision employee access: memberships/membership_org_000_user_006.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_seats → activate_member; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member, change_seats.

Distinct business objectives: capacity, access.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `497ba02ee2f60e633d82765f9e34ef07dfef4b191ec1317d095acf418badccd6`.

Human ratings: **not supplied**.

## 27. deactivate_reduce — validation

For organization org_000: User 1 has left the company. Suspend their access and reduce our paid seat count to the remaining active team size. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Revoke a departing employee's access: memberships/membership_org_000_user_001.status eq inactive.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 2.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: deactivate_member → change_seats; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_seats, deactivate_member.

Distinct business objectives: suspend, capacity.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `0539c4c809627318e365ec6182727b3f816ccb71b0e1ce8a95e570c926fb086f`.

Human ratings: **not supplied**.

## 28. seat_downgrade — validation

For organization org_000: Our team fits Starter now. Move us to Starter and pay only for the currently active team; retain all access. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan team, 8 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 3.
- Choose the requested service tier: subscriptions/sub_000.plan_id eq starter.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_seats → change_plan; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_plan, change_seats.

Distinct business objectives: capacity, plan.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `e2161687bf91bf2ae427bcbe4d8e1cf604f184cbaef82f6e83da58becbdac3b5`.

Human ratings: **not supplied**.

## 29. seat_downgrade — validation

For organization org_000: Our team fits Starter now. Move us to Starter and pay only for the currently active team; retain all access. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan team, 8 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 4.
- Choose the requested service tier: subscriptions/sub_000.plan_id eq starter.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_seats → change_plan; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_plan, change_seats.

Distinct business objectives: capacity, plan.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `3013738dfd9d5faaf1b3c7a4c5ea6e354f7a46b13a8cbf1b496491599f1cf0f7`.

Human ratings: **not supplied**.

## 30. plan_expand — validation

For organization org_000: We need six seats for next week's project and Team features. Please put our workspace on Team with six seats. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 5 seats / 5 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Choose the requested service tier: subscriptions/sub_000.plan_id eq team.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 6.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_plan → change_seats; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_plan, change_seats.

Distinct business objectives: plan, capacity.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `4ac142bf57e5f9f67cca82077ae30ec3ed41adf6b246dc270438e9cf8f149b0d`.

Human ratings: **not supplied**.

## 31. plan_expand — validation

For organization org_000: We need six seats for next week's project and Team features. Please put our workspace on Team with six seats. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 5 seats / 5 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Choose the requested service tier: subscriptions/sub_000.plan_id eq team.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 6.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_plan → change_seats; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_plan, change_seats.

Distinct business objectives: plan, capacity.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `5e3fa0edf55b2a00b3b1d798ac5765926b74f4b73635b53d482ca1efd910c79e`.

Human ratings: **not supplied**.

## 32. invite_activate — validation

For organization org_000: Please onboard directory user user_005 as a regular workspace member with working access. Keep our subscription and everyone else's permissions. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 5 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Onboard a directory user: memberships/membership_org_000_user_005.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: invite_member → activate_member; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member, invite_member.

Distinct business objectives: provision.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `8542a1cebe37847488eb4c16a8ff2a5a07583e65f1b0519f285f007725df50e0`.

Human ratings: **not supplied**.

## 33. owner_refusal — validation

For organization org_000: Please suspend the owner's membership. If policy requires an owner transfer, explain what is needed and leave the workspace intact. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- The sole owner cannot be deactivated through member management.: memberships/membership_org_000_user_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Policy certificate OWNER_IMMUTABLE: The sole owner cannot be deactivated through member management.

Distinct business objectives: preservation.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `9e14566e930ca926c5d538ae1e913013781c57b4fe6930a4117298fac7182560`.

Human ratings: **not supplied**.

## 34. failed_restore — validation

For organization org_000: The previous card attempt failed and our workspace expired. Recover the payment using an approved card and restore service. Do not create a second successful charge. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: expired, plan starter, 3 seats / 3 active members; period ends 2026-01-14T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `ba58a61967a682d5e8b70238bfcb367ce12dd803b4b8991a499660b4f2b372fd`.

Human ratings: **not supplied**.

## 35. failed_restore — validation

For organization org_000: The previous card attempt failed and our workspace expired. Recover the payment using an approved card and restore service. Do not create a second successful charge. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: expired, plan starter, 4 seats / 4 active members; period ends 2026-01-13T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `714a332990c1042fa79e50c6ef05efb848a5e0646fe49240d5e00496099db0b6`.

Human ratings: **not supplied**.

## 36. unpaid_restore — validation

For organization org_000: Our workspace expired. Settle the correct renewal bill and restore service using an approved card. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: expired, plan starter, 3 seats / 3 active members; period ends 2026-01-14T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `ba58a61967a682d5e8b70238bfcb367ce12dd803b4b8991a499660b4f2b372fd`.

Human ratings: **not supplied**.

## 37. unpaid_restore — validation

For organization org_000: Our workspace expired. Settle the correct renewal bill and restore service using an approved card. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: expired, plan starter, 4 seats / 4 active members; period ends 2026-01-13T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `714a332990c1042fa79e50c6ef05efb848a5e0646fe49240d5e00496099db0b6`.

Human ratings: **not supplied**.

## 38. renew_cycle — validation

For organization org_000: Please extend our workspace contract by one 30-day billing period from its current end, and settle the matching bill using an approved card. Avoid duplicate billing. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Bill the next service period: invoices/renewal_65a3fbb79cd6590da55a6a86.purpose eq renewal.
- Resolve outstanding service billing: invoices/renewal_65a3fbb79cd6590da55a6a86.status eq paid.
- Extend the contract by one billing period: subscriptions/sub_000.period_end eq 2026-02-15T12:00:00+00:00.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: issue_renewal → pay_invoice → renew_subscription; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: issue_renewal, pay_invoice, renew_subscription.
- Legal evaluator witness: issue_renewal → pay_invoice → renew_subscription; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: issue_renewal, pay_invoice, renew_subscription.

Distinct business objectives: renewal_invoice, settlement, renewal.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `f1ce7d4a3bb7dc1b069388876a3c77b9abfa8aafe3ca6dd99bdb2f77848f2d14`.

Human ratings: **not supplied**.

## 39. renew_cycle — validation

For organization org_000: Please extend our workspace contract by one 30-day billing period from its current end, and settle the matching bill using an approved card. Avoid duplicate billing. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Bill the next service period: invoices/renewal_6cc9f542511ac8fd7ee3908a.purpose eq renewal.
- Resolve outstanding service billing: invoices/renewal_6cc9f542511ac8fd7ee3908a.status eq paid.
- Extend the contract by one billing period: subscriptions/sub_000.period_end eq 2026-02-16T12:00:00+00:00.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: issue_renewal → pay_invoice → renew_subscription; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: issue_renewal, pay_invoice, renew_subscription.
- Legal evaluator witness: issue_renewal → pay_invoice → renew_subscription; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: issue_renewal, pay_invoice, renew_subscription.

Distinct business objectives: renewal_invoice, settlement, renewal.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `b71eafc4a0486e0c2fb9ceba36d7922ea0c17a265cfdd64ec07d77dccade3e93`.

Human ratings: **not supplied**.

## 40. payment_retry — validation

For organization org_000: The payment confirmation for invoice renewal_65a3fbb79cd6590da55a6a86 was lost. Please safely retry the original Visa payment with reference confirmed and confirm the existing result without another charge. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Confirm a previous charge without charging again: invoices/renewal_65a3fbb79cd6590da55a6a86.status eq paid.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice.

Distinct business objectives: verify_payment.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `7e815519829b252c637d0da4c513a2b3ccdd9498a585ce259c7760038d89e0dc`.

Human ratings: **not supplied**.

## 41. payment_retry — validation

For organization org_000: The payment confirmation for invoice renewal_6cc9f542511ac8fd7ee3908a was lost. Please safely retry the original Visa payment with reference confirmed and confirm the existing result without another charge. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Confirm a previous charge without charging again: invoices/renewal_6cc9f542511ac8fd7ee3908a.status eq paid.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: pay_invoice.

Distinct business objectives: verify_payment.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `595b640e4b930a6682eda937f36c4ed461e393b9cbdd88e2d73ad6200993d287`.

Human ratings: **not supplied**.

## 42. partial_refund — validation

For organization org_000: We agreed a service adjustment of 7600 cents on invoice invoice_000_recent. Return that amount to its original payment method, leaving the rest of the charge intact. Use adjustment as the refund reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Correct an agreed service charge: invoices/invoice_000_recent.refundable_amount_cents eq 22800.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: refund_invoice; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: refund_invoice.

Distinct business objectives: refund.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `05836f31a7320e3e0fc7b9866eda5d5d77af374aa8e74fc546a81ce36a458d42`.

Human ratings: **not supplied**.

## 43. partial_refund — validation

For organization org_000: We agreed a service adjustment of 12300 cents on invoice invoice_000_recent. Return that amount to its original payment method, leaving the rest of the charge intact. Use adjustment as the refund reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Correct an agreed service charge: invoices/invoice_000_recent.refundable_amount_cents eq 27060.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: refund_invoice; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: refund_invoice.

Distinct business objectives: refund.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `89f28dc342efc0dba26fcaa1b1876388760ccdc1eba170d6b81fd588c6f9a562`.

Human ratings: **not supplied**.

## 44. excessive_refund — validation

For organization org_000: Please refund 40500 cents from invoice invoice_000_recent under reference adjustment. If this exceeds the paid balance, explain the limit and leave accounting unchanged. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Requested refund exceeds the remaining paid balance.: memberships/membership_org_000_user_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Policy certificate REFUND_AMOUNT_EXCEEDED: Requested refund exceeds the remaining paid balance.

Distinct business objectives: preservation.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `4335e119cd384b774fff4c83ed31d6397b48b793f5d42daf137721021f903c5b`.

Human ratings: **not supplied**.

## 45. excessive_refund — validation

For organization org_000: Please refund 39100 cents from invoice invoice_000_recent under reference adjustment. If this exceeds the paid balance, explain the limit and leave accounting unchanged. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_002`. Roles: org_000=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 4 active members; period ends 2026-01-17T12:00:00Z.

Terminal business predicates:

- Requested refund exceeds the remaining paid balance.: memberships/membership_org_000_user_002.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Policy certificate REFUND_AMOUNT_EXCEEDED: Requested refund exceeds the remaining paid balance.

Distinct business objectives: preservation.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `26b161d7d9df65ee2b770e2462acbd1c4dc57ddc1903c23c89f596c213441b64`.

Human ratings: **not supplied**.

## 46. two_org_budget — validation

For organization org_000: I administer billing for both org_000 and org_001. Set each workspace's paid seats to its own active team size. Preserve both plans and all member access. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active), org_001=billing_admin (active).

Relevant initial facts:

- sub_000: active, plan starter, 4 seats / 3 active members; period ends 2026-01-16T12:00:00Z.
- sub_001: active, plan business, 20 seats / 6 active members; period ends 2026-02-04T12:00:00Z.

Terminal business predicates:

- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 3.
- Right-size paid workspace capacity: subscriptions/sub_001.seats eq 6.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_seats → change_seats; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_seats.
- Legal evaluator witness: change_seats → change_seats; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_seats.

Distinct business objectives: capacity, capacity.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `1a27dbf49d55fc5613ca13ca73828331d05821473c86aa4d494d0a2a662e3f70`.

Human ratings: **not supplied**.

## 47. invitation_resolve — validation

For organization org_000: The pending invitation for user_006 seems stuck. Give them working member access without creating another account or changing our subscription. Reuse the existing invitation if possible. The employee's membership is membership_org_000_user_006. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 5 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Provision employee access: memberships/membership_org_000_user_006.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: activate_member; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member.

Distinct business objectives: access.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `c3987361b8412d3ff711c10b13d814d5a8d6fab02578193bd8825a11b18d0a03`.

Human ratings: **not supplied**.

## 48. remove_departed — validation

For organization org_000: User 1 has left permanently. Remove their workspace membership record, retaining the owner, subscription and all other members. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Remove a departing employee's provisioning record: memberships/membership_org_000_user_001.status absent None.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: deactivate_member → remove_member; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: deactivate_member, remove_member.

Distinct business objectives: removal.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `1ef54f4d2adb8b4b1c56b1d7ee7700718e46b6b6ac9bfdccb554e07f2c26f8f6`.

Human ratings: **not supplied**.

## 49. tenant_refusal — validation

For organization org_000: Please turn off renewal for sub_001 through org_000. If this scope is invalid, request the appropriate organization authorization and change nothing. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- The subscription belongs to another tenant; scope substitution cannot confer authority.: memberships/membership_org_000_user_000.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Policy certificate CROSS_ORG_RESOURCE: The subscription belongs to another tenant; scope substitution cannot confer authority.

Distinct business objectives: preservation.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `0409e1aba84017941d4f79c041ce7fcb1d9ecac1f3025a6c379da9b7629c112f`.

Human ratings: **not supplied**.

## 50. expire_cycle — validation

For organization org_000: Our service period has ended. Record the workspace as expired without billing for another period, retaining our membership records and accounting history. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 3 seats / 3 active members; period ends 2026-01-14T12:00:00Z.

Terminal business predicates:

- Record elapsed service and stop renewal: subscriptions/sub_000.status eq expired.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: expire_subscription; dependency depth 0; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: expire_subscription.

Distinct business objectives: expiration.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `8fbdd06840599bce5eefd0d9a59276200a9fd4453d4d489dab773066bad191a2`.

Human ratings: **not supplied**.

## 51. restore_onboard — test

For organization org_000: Our workspace expired. Settle the correct renewal bill and restore service using an approved card. Also enable the pending new hire, adding exactly one seat while keeping the existing team active. The employee's membership is membership_org_000_user_006. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: expired, plan starter, 3 seats / 3 active members; period ends 2026-01-14T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 4.
- Provision employee access: memberships/membership_org_000_user_006.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription → change_seats → activate_member; dependency depth 3; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member, change_seats, pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription → change_seats → activate_member; dependency depth 3; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member, change_seats, pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration, capacity, access.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `907f2d6ab705a1fa8c780420147e737c984d27a63e2389b193ca5219c9d86350`.

Human ratings: **not supplied**.

## 52. offboard_downgrade — test

For organization org_000: After User 1 leaves, the remaining team fits Starter. Suspend their access and move to Starter, paying only for the remaining active members. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan team, 8 seats / 6 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Revoke a departing employee's access: memberships/membership_org_000_user_001.status eq inactive.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 5.
- Choose the requested service tier: subscriptions/sub_000.plan_id eq starter.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: deactivate_member → change_seats → change_plan; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_plan, change_seats, deactivate_member.

Distinct business objectives: suspend, capacity, plan.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `c1c7fceb7916dfa8c00274986a3278a60d0c37cd142f6d9e7555b3b2d2b4bee3`.

Human ratings: **not supplied**.

## 53. upgrade_onboard — test

For organization org_000: Our Starter workspace is full and we need Team features. Enable the pending new hire and put us on Team with exactly one additional seat, retaining existing access. The employee's membership is membership_org_000_user_006. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan starter, 5 seats / 5 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Choose the requested service tier: subscriptions/sub_000.plan_id eq team.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 6.
- Provision employee access: memberships/membership_org_000_user_006.status eq active.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: change_plan → change_seats → activate_member; dependency depth 2; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member, change_plan, change_seats.

Distinct business objectives: plan, capacity, access.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `24f1a3484f7947f0ad0212da371aa6f6bd3f41a10aa39b32678580a06c3eb9c2`.

Human ratings: **not supplied**.

## 54. restore_upgrade_onboard — test

For organization org_000: Our workspace expired. Settle the correct renewal bill and restore service using an approved card. Also enable the pending new hire, adding exactly one seat while keeping the existing team active. We now need Team features. The employee's membership is membership_org_000_user_006. Use settlement as the payment reference. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: expired, plan starter, 5 seats / 5 active members; period ends 2026-01-14T12:00:00Z.

Terminal business predicates:

- Resolve outstanding service billing: invoices/renewal_22c6836c894463d387c295b2.status eq paid.
- Restore paid service access: subscriptions/sub_000.status eq active.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 6.
- Provision employee access: memberships/membership_org_000_user_006.status eq active.
- Choose the requested service tier: subscriptions/sub_000.plan_id eq team.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: pay_invoice → reactivate_subscription → change_plan → change_seats → activate_member; dependency depth 4; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member, change_plan, change_seats, pay_invoice, reactivate_subscription.
- Legal evaluator witness: pay_invoice → reactivate_subscription → change_plan → change_seats → activate_member; dependency depth 4; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: activate_member, change_plan, change_seats, pay_invoice, reactivate_subscription.

Distinct business objectives: settlement, restoration, capacity, access, plan.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `3cb9bb447415c68dd5628e1ae7096427891b66450aed4181a0c6e2b5fdcd29b9`.

Human ratings: **not supplied**.

## 55. offboard_refund — test

For organization org_000: We agreed a service adjustment of 7175 cents on invoice invoice_000_recent. Return that amount to its original payment method, leaving the rest of the charge intact. Use adjustment as the refund reference. User 1 has departed; suspend their access and reduce paid seats to the remaining team. Leave unrelated organizations, users, member roles and billing records unchanged.

Authenticated identity: `user_000`. Roles: org_000=owner (active).

Relevant initial facts:

- sub_000: active, plan team, 8 seats / 6 active members; period ends 2026-01-16T12:00:00Z.

Terminal business predicates:

- Correct an agreed service charge: invoices/invoice_000_recent.refundable_amount_cents eq 15785.
- Revoke a departing employee's access: memberships/membership_org_000_user_001.status eq inactive.
- Right-size paid workspace capacity: subscriptions/sub_000.seats eq 5.

Forbidden side effects: Any difference outside the atom allowed_changes union; owner identity/role, other users and unrelated tenants are protected.

Validity / causal certificates:

- Legal evaluator witness: deactivate_member → change_seats → refund_invoice; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_seats, deactivate_member, refund_invoice.
- Legal evaluator witness: deactivate_member → refund_invoice → change_seats; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_seats, deactivate_member, refund_invoice.
- Legal evaluator witness: refund_invoice → deactivate_member → change_seats; dependency depth 1; Oracle pass; replay True.
  Necessary operation types inside the frozen search domain: change_seats, deactivate_member, refund_invoice.

Distinct business objectives: refund, suspend, capacity.

Scoring: Actual terminal predicates + frame + independent Oracle + completed budget, or explicit certified refusal declaration.

Canonical structure: `83c577c5d709eee3886234545c82646581f4ac47f850f03a5b247326203957dc`.

Human ratings: **not supplied**.
