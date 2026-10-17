# Native dialogue task certification

Status: implemented and exercised for After-sales and Airline; Property, Education and the unified eight-domain release remain active work. No real LLM research run has been performed.

## Reachability and scoring are different operations

`usami_aftersales.tasks.compose()` binds a declarative task to an existing frozen world and private Customer profile. It cannot change an order, stock, policy, evidence outcome, user fact or simulated external outcome. The public task goal accepts one or more actual terminal order-line states. The native frame contract limits changes to that line's case, quotes, settlement, return, approval and replacement stock. A task cannot grant arbitrary frame exemptions.

The bounded Reference search enumerates available native operations and pre-registered external events. It uses Customer-side process events for truthful disclosures and real quote confirmation. A search limit without a witness is reported as exhausted budget, not proof of impossibility. Search can return distinct legal remedies for one task.

`execute_witness()` executes each resulting plan using the actual dialogue session and independent native mutation implementation. `certify()` requires the objective goal, frame, Oracle and full offline Replay to agree. The witness is a private certificate, never a production Service script or required path. `score()` evaluates an Agent's actual trace using the same terminal predicates and independent judgments; legal extra queries and different valid paths are accepted.

## Mixed task

A reproducible mixed After-sales task asks for a valid remedy and then requests another resolution of the same real order line. The first subgoal requires the actual refund/exchange/reship state. The second requires a Service refusal of the exact requested operation with the native `ALREADY_RESOLVED` reason. The original order and item exist; no invented ID is needed.

An Engine-blocked attempt is not a Service correct refusal. `DialogueSession.reply()` records a structured decision separately from native operations. The independent Oracle checks that the request was actually made, the operation remained unattempted, Reference disallows it, and the refusal reason matches. A refusal of an allowed operation is a false rejection. Other cases remain unattributed or wrong-reason decisions and cannot satisfy a refusal subgoal.

## Dialogue necessity

`usami_dialogue.dependencies.certify_dependencies()` first replays the actual trace. It evaluates actual pre-operation states under a closed list of evaluator-only interventions:

- Remove one previously disclosed frozen fact.
- Remove actual explicit consent.
- Select another permitted preference, revoking superseded consent and commitments.
- Compare actual states immediately before and after a recorded frozen external event.

A certificate is emitted only when the native Reference's allowed boolean changes. Merely changing the denial message is insufficient. It stores the actual source event, both full states, operation, intervention, decisions and hashes. Verification reconstructs the source and intervention, recomputes both Reference decisions, and rejects any extra business-state edit even when hashes are re-sealed.

These counterfactual copies never enter the World Pool or a Service session. They provide evaluator evidence of information dependency; they do not edit a Designer's challenge world.

Current tests demonstrate missing-information, preference, consent and real manager-approval dependencies. They also reject claiming a refund deadline as necessary when removing it does not affect the refund decision. The explicit cross-turn commitment and full eight-domain coverage reports are not yet complete.

## Evidence limits

A private witness proves that a task is executable under its stated rules. It does not prove a real model solves the task, asks good questions or learns across generations. Fixture-driven Agent protocol tests exercise actual Function Calling, business mutations, Oracle, budget handling and exact request Replay; they are not real LLM results. Dataset-scale certification, coverage/leakage reports and the Pilot/Core releases remain outstanding.


## Shared planner and source-complete artifacts

`usami_dialogue.planner` is the common bounded search/execution implementation. Domain-specific composers supply only real goals, exact scopes, allowable preferences, frames and refusal probes. A refusal is reachable only when the requested operation is actually disallowed for the declared reason; reaching a completion goal alone is insufficient for a mixed task.

`usami_dialogue.artifacts` saves actual native traces/certificates with independently frozen generator provenance, deterministic compressed content, exact runtime source file sets/hashes and a source archive. Offline verification checks generation, source completeness, manifest/case integrity, objective scoring and Replay. Native witnesses are explicitly labelled `model_experiments: NOT RUN`; re-labelling them as real LLM evidence is rejected.

`TaskRunConfig` uses a separate task-agent protocol. It requires the task to match a private certificate and verifies the witness before invoking either model. Domain-derived Customer briefs contain the selected business need but no hidden refusal code, expected outcome or witness. The complete private certificate remains in the host journal for reproducibility, never the model request. Base v1 configurations remain available for task-independent interactions.
