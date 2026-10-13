# FulfillmentOps v0.1 measured report

Engineering gate: implemented and verified. Human business-realism review:
**AWAITING HUMAN REVIEW**. This does not claim τ-bench-equivalent realism or full
model competence. Final four-domain project evidence is reported separately.

| Measure | Actual | Target |
|---|---:|---:|
| Frozen Service instances | 338 | 278 |
| Base business goal/decision cases | 67 | — |
| Business workflow families | 31 | 21 |
| Base anonymous structures | 49 | 28 |
| Base semantic decision signatures | 65 | 47 |
| Instances with at least three linked transitions | 173 | 46 |
| Instances with multiple certified legal routes | 162 | 80 |
| Maximum first-failure causal depth | 10 | 4 |
| Actual certified witnesses | 665 | — |
| Correct-refusal certificates | 26 | required |
| Stratified human-review sample | 55 | 55 |

Train/Validation/Public Test Demo are 265/27/46. Train–Test structure overlap is
zero; every Test operation ability occurs in Train. Progress states are actual
Reference-executed world states and are counted as instances, not new families.
Headline diversity uses base cases only. See `coverage.json` and `QUALITY_AUDIT.md`.

New tests: 73 passed. Gate A repository: 550 passed; final four-domain repository: 605 passed. Every frozen initial state,
witness and refusal certificate was independently regenerated, executed,
Oracle-checked and replayed. Two independent rebuilds agree in parsed values and
canonical hashes. Raw dictionary presentation ordering is explicitly reported as
non-byte-stable. Existing SaaS/CloudOps runtime and historical releases are unchanged.

Actual provider: `dashscope/qwen3.6-plus`, OpenAI-compatible LiteLLM gateway.
Authentication was loaded from local Keychain at runtime, and was not saved.
Public model settings, requests, replies, tool arguments/results, independent
authority, whole world events, Oracle outcomes and replay evidence are under
`pilot-v1/`. Exact source and Python/Pydantic/httpx versions are archived there.
Both actual model profiles were preregistered before the first completion.

Six distinct Service families were preregistered. Five passed (5/6); packed
cancellation exhausted the frozen 24-call Service budget and failed the task.
All six attempts, including that failure, remain in the report. This is a small
selected pilot, not a complete benchmark score. There were no confirmed business
violations in Reference execution; rejected attempts and authorization anomalies
are reported separately.

Open Discovery used one unconditioned world with the same fixed identity,
victim Service, tools and budgets across three preregistered trials. All three
Customer episodes ran eight turns and ended at the Customer turn budget. The
Customer made 8/8/8 actual native-tool model calls; Service made 19/23/19 calls.
There were zero Customer schema failures and zero format recoveries. Each
episode recorded three authority-only anomalies; Oracle therefore reports fail
for authorization even though it confirms zero successful business violations.
The business-discovery result is zero findings in all three trials. These are
simulated evidence classes, not claims about a real merchant or gateway.

The earlier `pilot/` directory is a retained preflight source-pin invalidation
with zero model completions. Its registration/failure records are not silently
reused or counted as a live trial. `pilot-report.json` includes this condition.

Reusable research interfaces: explicit `adapter`, scoped `observation`, native
`intend_<operation>`/`ask_service`/`stop_exploration` Customer tools, persistent
`ServiceSession`/`CustomerSession`, frozen `Manifest`, complete `Execution` and
`Interaction`, independent `Oracle`, and exact `replay_run`. Customer strategies
can change only Customer model/method while `assert_comparable` freezes the
world, identity, victim model/settings, tools, source, budgets and trial list.
No Evolver, training or Service repair is implemented.

Remaining quality limits: synthetic instantaneous external events, frozen-time
simulation, authored workflow families, finite search/certified routes and pending
human realism review. These do not prevent running the independent Discovery
protocol, but do limit generalization of this small pilot.
