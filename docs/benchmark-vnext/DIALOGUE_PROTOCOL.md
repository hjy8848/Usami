# Genuine multi-turn information protocol — foundation checkpoint

This document describes implemented shared protocol primitives. It does not claim the four dialogue domains or complete agent sessions are delivered yet.

## Private Customer data

`CustomerPrivateState` freezes identity, opening need, objective facts, allowed preference values, initial private preferences, confirmable operation families and protected business objects. Its hash detects even nested-dictionary changes. These fields do not automatically enter Service state.

`initialize()` creates only authenticated identity. Neither private facts nor private initial preferences are silently disclosed. `public_context()` exposes only actual Customer-provided facts, stated preferences, current revision and established commitments.

`CustomerIntent` is a structured natural response, not a fixed line in a scripted conversation. An intent can disclose selected facts, state a permitted preference, reject an offer, confirm one exact actual offer or finish. The future Customer model remains fixed and must choose these responses from the actual Service context; no forced turn count is part of these primitives.

## Trusted event reduction

`customer_event()` independently checks disclosed values against the immutable private profile. It refuses invented objects/facts, unsupported preferences, actor switching and unauthorized confirmation scope.

A preference revision or offer rejection increments the revision and invalidates old consents/commitments. Confirmation must bind an actual offered operation, quote hash, world hash and current revision. A domain-native consent callback must verify quote/object/constraint semantics; absence of that callback is rejected. Service tool arguments alone cannot create consent.

`information_code()` and `consent_code()` are deterministic process checks. Domain References must use them as real business preconditions. Those References, dialogue trace replay and per-industry consent callbacks remain subsequent work; primitive tests alone do not prove a real industry's multi-turn necessity.

## Necessity evidence

`DependencyProof` separates missing information, preference choice, explicit consent, external state update, cross-turn commitment and partial completion. A proof is invalid unless a replayable control change actually changes whether the chosen operation is Reference-allowed. Different denial text with the same allowed action set is not accepted as necessity evidence.

The final implementation must produce these proofs from actual native domain References and execution, rather than manually filling booleans. Per-task certificates and counterfactual replay are still pending.

## Actual tests

Ten primitive tests passed: selective disclosure/private separation, fabricated facts, exact current consent, preference revision/revocation, wrong world/scope, missing native consent check, nested private-state mutation and rejection of error-label-only necessity claims. These tests contain no paid model calls and do not demonstrate Agent learning.
