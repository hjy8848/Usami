# First structural generation audit — retained failed run

This run attempted 100 worlds per existing domain. SaaS, CloudOps and Fulfillment produced 100 valid worlds each. StayOps produced 96: four seeds exposed a native `check_out` / future room-assignment invariant conflict. Exit code: 1. These results are not a passing release audit.

The four failing full Engine traces, trusted requests and original Oracle results are retained as `stayops-native-consistency-*.json.gz`. `source-snapshot.zip` and `source-pins.json` preserve the exact first-run implementation. No legacy rule, applier or Oracle was changed to suppress the inconsistency.

A separate corrected distribution audit records generator exclusions of Reference transitions whose own expected states violate native invariants. That exclusion belongs only to independent initial-state generation; it does not intercept or conceal Service operations. The simulator consistency issue remains an explicit limitation pending a versioned domain-rule correction.
