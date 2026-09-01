# Platform API execution contracts

Read this file together with `live-execution-safety.md` for every API-assisted write. It defines execution mechanics, not authority. Write-capable credentials, a successful validation, or an accepted request never authorize a mutation or prove that the desired state is live.

Platform contracts, versions, limits, fields, and reversibility can change. Resolve them from the current method-level official documentation and the live account immediately before execution. If the contract cannot be verified, stop at a prepared change packet.

## Describe the mutation before sending it

For every operation, record:

- platform, API version, account/customer/advertiser ID, entity type and ID;
- endpoint or service, method, exact field mask or payload fields, and desired value;
- approved before-state and fresh resolved before-state;
- dependency order and whether operations must land together;
- atomicity mode, partial-failure behavior, validation/dry-run support, and response semantics;
- idempotency mechanism if documented, otherwise the duplicate-detection/read-before-retry method;
- reversibility class, exact compensating operation, and non-reversible side effects;
- expected response, independent read-back tool/query, a normalized expected-state projection, exact success predicate, and timeout state.

Do not put unrelated edits in one request. Do not split dependent edits merely to make partial success easier.

When a platform permits it, express value-setting mutations as an **absolute desired state** (`daily_budget = 120`) rather than a relative instruction (`increase daily budget by 20%`). Capture the fresh before-state and concurrency precondition. Absolute state makes an ambiguous retry easier to reconcile, but it is not automatically safe or idempotent: another operator may have changed the entity, and delivery or learning side effects can already have occurred.

## Classify reversibility

- **R0 — read only:** no mutation.
- **R1 — directly reversible configuration:** a field can be restored to its captured prior value, such as a simple status or budget field. Delivery, learning, and auction side effects can still persist.
- **R2 — compensatable:** there is no true undo, but a verified inverse operation can restore an equivalent configuration. Record expected residual effects.
- **R3 — replace/create:** restoration requires a new object or relaunch. Identity, review, history, learning, or experiment continuity may not transfer.
- **R4 — destructive or externally consequential:** delete, irreversible goal/tracking changes, audience/customer-data upload, billing/access changes, shared-resource mutations, or another action whose prior state cannot safely be reconstructed.

R3 and R4 require narrow human confirmation of the exact operation and consequences immediately before execution. Never describe a compensating operation as an undo unless equivalence has been verified.

## Google Ads API

Verify the current request message for the selected service; not every method exposes the same fields.

- Where supported, `validate_only` validates without executing and returns errors rather than a preview of created resources or final state. Treat it as `validated_only`, not accepted or applied.
- Where supported, `partial_failure=true` commits valid independent operations and returns indexed errors for invalid ones. It gives up request-level atomicity. Parse and reconcile every operation index.
- Do not use partial failure for interdependent operations that reference temporary resource names. Initial complex creations can require all-or-nothing treatment.
- Batch jobs execute with partial-failure semantics; successful operations are not rolled back because another operation fails. A batch is a throughput mechanism, not a safety mechanism.
- Construct update masks only from explicitly approved fields. A broad or generated mask can clear or overwrite configuration that the user did not approve.
- A mutable resource returned in the mutation response reduces ambiguity but is still not an independent read-back. Query the target and dependent resources freshly.
- Change events and change status are supplementary audit signals. Reconcile actual entity state against the recorded expected state; do not assume an audit surface is a complete change feed.

Primary references: [partial failures](https://developers.google.com/google-ads/api/docs/best-practices/partial-failures), [mutating resources](https://developers.google.com/google-ads/api/docs/mutating/overview), [batch processing](https://developers.google.com/google-ads/api/docs/batch-processing/overview), and [change events](https://developers.google.com/google-ads/api/docs/change-event).

## Meta Marketing API

Meta Graph and Marketing API behavior varies by node, edge, version, access tier, and operation.

- Use `execution_options=validate_only` only when the current endpoint explicitly documents support. Do not infer a platform-wide dry run from one create/update surface.
- Treat Graph batch requests as a transport wrapper, not an atomic transaction. Inspect every subrequest result and re-read every target. Batching does not convert partial completion into rollback.
- Resolve whether a requested “edit” is a field update, a copy, or replacement. Creative replacement can create a new identity, review cycle, and discontinuous delivery/history.
- Treat deletion, archival, attribution/optimization-setting changes, custom conversion changes, audience uploads, and tracking mutations as high-risk until current reversibility and downstream effects are verified.
- Key error handling to current numeric codes/subcodes and structured field information when documented; message text is not a stable program contract.
- Read rate-limit headers and current access state at runtime. Do not freeze tier names, thresholds, or quota formulas into policy.

Primary references: [Marketing APIs](https://developers.facebook.com/docs/marketing-apis/), [Graph API batch requests](https://developers.facebook.com/docs/graph-api/batch-requests/), and [Graph API rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting/). If an endpoint page is inaccessible or inconsistent, preparation may continue but execution must pause until the exact contract is verified.

## TikTok Business API

Do not borrow Google or Meta semantics. For the exact current endpoint, verify mutation support, validation behavior, status transitions, partial failure, rate limits, auditability, and read-back fields in the official portal and live response schema.

With TikTok for Business MCP, inspect the selected native alias or dispatcher tool's current full definition before preparing a write. A progressive-disclosure dispatcher can reach both reads and destructive operations; classify the underlying endpoint and HTTP method. Re-run capability discovery because tool names, schemas, defaults, immutable fields, allowlist requirements, pagination, and product-specific reporting can change.

New campaign structures should be explicitly created in a paused/disabled state when the current endpoint supports it. Do not trust a status default. Creating even a paused object is a write and therefore execute-class: it requires exact approval, resolved write/read tools, preflight, read-back, and rollback or compensation. Verify the campaign, ad-group, and ad states separately, plus parent/child eligibility, identity, destination, catalog/store/app/form binding, and any auto-budget or automated-rule interaction. A paused draft is not activation authority.

If primary documentation cannot establish dry-run, atomicity, idempotency, or reversibility:

1. mark each property `unknown`;
2. prepare a packet for the smallest reversible or paused-draft operation without sending it;
3. require exact confirmation of the uncertainty and exposure;
4. stop if a reliable independent read-back cannot be defined.

Primary reference: [TikTok Business API portal](https://business-api.tiktok.com/portal/docs).

## Ambiguous response and retry protocol

A timeout, transport error, lost connection, or malformed response can occur after a server commits a write. Never assume “no response” means “no change.”

1. Freeze additional writes for the affected scope.
2. Query the exact target and dependent resources from a fresh session.
3. Compare live state with the captured before-state and desired state.
4. Classify it as not applied, applied, partial failure, read-back mismatch, or unknown.
5. Retry only if the operation is provably idempotent, a deterministic duplicate check proves no prior commit, or the user approves a bounded recovery.
6. If part of a set landed, present the applied/failed map and proposed compensation before making a new write.

Exponential backoff handles transient capacity errors; it does not solve duplicate or ambiguous mutations.

## Read-back matrix

Before mutation, define the smallest normalized projection that proves the approved fields and dependencies, for example `{"campaign_id": "123", "daily_budget": 120, "status": "PAUSED"}`. After mutation, fetch that projection through a resolved read-only tool in a fresh query. A mutation response, cached preflight value, echoed payload, missing timestamp, empty object, or merely non-null response is not proof. `applied` and later states require exact equality between expected and observed projections; a difference is `readback_mismatch`, and an unavailable read is `unknown`.

Verify at least these layers when relevant:

| Layer | Proof required |
|---|---|
| Configuration | Fresh entity read shows exact field values and normalized units |
| Dependency | Shared budget/strategy, parent/child status, experiment, asset, goal, and schedule remain as approved |
| Eligibility | Current status/policy shows the entity can enter delivery |
| Delivery | Later reporting shows eligible delivery in the intended market/window; zero delivery needs diagnosis |
| Outcome | Complete-lag advertiser-owned outcomes are available and reconciled |
| Commercial | Contribution, quality, cash/capacity, and approved guardrails satisfy the decision rule |

Configuration proof cannot stand in for delivery or business proof. Platform-attributed conversions cannot prove that a configuration write landed.

## Contract test before automation

Before wrapping a write path in an agent, script, or MCP tool, test it on a non-live or paused-draft target where available. Cover:

- stale target IDs and wrong-account protection;
- validation-only behavior and a deliberately invalid field;
- multi-operation all-success, total-failure, and partial-failure cases;
- timeout after possible commit and duplicate-safe recovery;
- exact field mask behavior and unit conversion;
- fresh read-back mismatch and platform normalization;
- rollback/compensation plus residual side effects;
- rate-limit and auth failures without runaway retry;
- prompt-injected or unapproved fields being rejected by the allowlist.

No test account result proves a live commercial outcome. It proves only the tested contract under that version and configuration.
