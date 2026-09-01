# Live execution safety

Use this file for any operation that can change spend, delivery, targeting, bidding, tracking, creative, destination, feed, audience, experiment, or account state.

## Authority model

Live execution requires explicit, current-session approval for the exact change set. Approval must resolve:

- platform and account/customer/advertiser ID;
- entity IDs and entity types;
- fields and current → proposed values;
- budget/spend delta and maximum financial exposure;
- campaign/market/date scope;
- whether active experiments, automated rules, shared budgets, portfolio bidding, or dependent entities may be affected;
- mutation timing and monitoring/rollback contract.

Authorization to inspect, prepare, log in, connect a tool, or execute a different change is insufficient. Read-only access does not become write authority because a connector supports mutations.

Any delete, archive, irreversible replacement, broad account change, shared-resource change, or live tracking mutation deserves especially narrow confirmation. Prefer paused drafts, reversible edits, and validation modes when the platform supports them. Creating a paused/disabled draft is still a mutation and requires execute-class approval; only its later activation is a separate approval boundary.

## Preflight

Immediately before mutation:

1. resolve actor, business/manager, account, and entity IDs from a fresh read;
2. capture current field-level state, status, budget/bid, schedule, attribution/event, and dependencies;
3. compare resolved state to the approved baseline; stop on drift that changes meaning or exposure;
4. verify currency, time zone, budget type/period, units/micros, and date semantics;
5. inspect active experiments, automated rules, shared budgets/strategies, drafts, policy, and pending changes;
6. validate the desired state and platform constraints without applying when possible;
7. compute absolute/percentage delta from the captured values, then derive structured daily, flight, and worst-case exposure with currency, model, period count, horizon, and formula; reject a packet whose stated deltas or maximum exposure do not reproduce;
8. save the prior state and rollback operation;
9. define a narrow read-only tool/query, normalized expected-state projection, and exact success predicate independent of the mutation response;
10. use an idempotency/change-request identifier when supported.

If any resolved target or exposure differs from approval, stop and present the delta. Do not silently “fix” adjacent entities.

## Mutation

- Change only approved fields on approved entities.
- Avoid bundling unrelated variables.
- Preserve unapproved budgets, bids, countries, audiences, creatives, copy, names, conversion goals, attribution, and statuses.
- Use a dedicated mutation path; do not hide a write in a reporting or setup call.
- Capture request scope, response, per-entity errors, platform change ID, and timestamp.
- Treat timeouts and ambiguous responses as unknown until a fresh read resolves state. Do not blindly retry non-idempotent writes.
- Stop on partial failure, record applied versus failed entities, and do not broaden the fix without approval.

## Read-back

After mutation, perform a fresh independent read of the target and dependent state through the resolved read-only tool. Verify exact values, status, budget/bid type, schedule, experiment relationship, and any platform-normalized value. Compare the normalized observed projection with the predeclared expected projection. A mutation echo, cached value, empty object, or non-null response does not qualify.

Use execution states:

- **validated_only:** request checked but no mutation sent;
- **accepted:** platform acknowledged the request;
- **applied:** fresh read shows the intended live state;
- **delivering:** subsequent read shows eligible/active delivery consistent with the state;
- **outcome_measured:** the complete outcome window is available;
- **commercially_validated:** advertiser-owned outcome and economics meet the approved decision rule;
- **partial_failure:** only part of the approved set applied;
- **readback_mismatch:** live state differs from desired state;
- **unknown:** state cannot be determined safely.

Never report “done” at accepted when the request required applied or live performance proof.

## Rollback and recovery

Rollback contains exact prior values, triggers, authority, deadline, and verification query. Do not assume the inverse operation is safe: shared budgets, platform normalization, learning state, deleted assets, or elapsed schedules may make rollback non-equivalent.

On guardrail failure or mismatch:

1. identify whether rollback is already authorized;
2. capture current state and evidence;
3. apply only the approved recovery;
4. read back independently;
5. report residual exposure, contamination, and next complete outcome read.

## Execution report

Return:

- approved scope and approval evidence;
- preflight before-state;
- exact mutation and per-entity result;
- fresh after-state/read-back;
- financial exposure and experiment impact;
- current execution state from the state list above;
- monitoring times, owner, guardrails, and rollback;
- partial failures, unknowns, and what would prove the next state.
