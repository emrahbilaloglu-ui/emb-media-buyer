# TikTok MCP operations

Use this guide whenever TikTok Ads work uses TikTok for Business MCP. The MCP is a connectivity and capability layer, not evidence quality, business authority, or permission to spend.

The official server currently offers full-disclosure and progressive-disclosure modes. Tool counts, aliases, schemas, endpoints, defaults, permissions, limits, and product availability are volatile. Discover them in the current session; do not code a remembered inventory into a decision.

Loading mode is a runtime host decision. Read the current official setup guidance before connecting; the 2026-09-01 guidance recommends Full Disclosure for Claude and Progressive Disclosure for token-conscious or limited-context setups, but that recommendation can change. Record the host, selected mode, guidance retrieval time, initial/native tool count, discovered tool count, and group count in the capability snapshot.

## Connection and capability preflight

1. Confirm the operating class: read_only, prepare, execute, or monitor.
2. Use the host's authenticated MCP connection. Never ask the user to paste an access token into chat, a file, a command, or a report.
3. Resolve accessible advertisers with the current authorization tool. If more than one advertiser is available, bind the exact advertiser ID, account name, currency, and time zone before querying performance.
4. In progressive disclosure, call the current tool-list discovery surface, then fetch the full definition only for selected tools. In full disclosure, still inspect the current tool description before a consequential call.
5. Create a capability manifest with tool name, endpoint/path, HTTP method, required parameters, mutability class, permissions, pagination/row limits, latency, and retrieval time.
6. Treat dispatcher tools as the selected underlying operation. A generic `tool_execute` call is not read-only merely because the dispatcher name sounds neutral.
7. Use an explicit read allowlist for analysis. Tool names containing `create`, `update`, `status`, `delete`, `apply`, `bind`, `unbind`, `transfer`, `upload`, `submit`, `confirm`, `cancel`, `appeal`, `promote`, `subscribe`, or similar verbs are presumptively mutating until the current schema proves otherwise.

If authentication, account binding, scope, or tool semantics are ambiguous, stop at a capability gap. Do not probe with a write.

## Build the account evidence graph

Select only the surfaces relevant to the decision, but check for product families that report separately.

### Foundation

- authorized advertiser and Business Center scope;
- advertiser information, currency, time zone, balance/billing state when relevant;
- campaign → ad group → ad hierarchy for regular delivery;
- Smart+ campaign → ad group → ad hierarchy where applicable;
- review status, rejection reason, operation/primary/secondary status, schedule, and eligibility;
- identities, Spark authorization, destinations, pages/forms, apps, pixels, custom conversions, catalogs, stores, and product bindings;
- account and Business Center change logs, budget change history, active automated rules, and rule execution results.

### Reporting

- choose report type, service type, data level, dimensions, metrics, date range, attribution, and filters explicitly;
- preserve raw metric names and enumerate returned conversion/action aliases before mapping them;
- page through every result and report coverage checksums;
- use asynchronous reporting when synchronous row limits, Ads Manager parity, or large inventories require it;
- treat zero rows, zero-valued rows, unavailable dimensions, and truncated coverage as different states;
- use separate product-specific reporting when required. For example, current MCP metadata states that GMV Max does not appear in the integrated report and has a dedicated reporting route; verify this again at runtime.

### Diagnostic and benchmark inputs

- native tool diagnoses and the TikTok diagnosis agent can supply issue candidates and platform context;
- preserve the exact object, issue date, intent, session identifier, and tool limitations;
- keep a diagnosis session scoped and reuse its session ID only for follow-ups to the same diagnosis;
- platform benchmark results can have impression eligibility, latency, population, and supported-dimension constraints;

Independently verify material claims with configuration, reporting, change history, advertiser-owned outcomes, and current official documentation. Do not expose internal or sensitive benchmark fields that the tool does not return.

## Query plan by workstream

### Account audit or WBR

Read advertiser metadata, entity trees, integrated or product-specific reports, review status, diagnostics, change logs, measurement sources, active rules, and business-outcome bindings. Use `references/account-review-and-optimization.md` for objective routing and coverage.

### Budget, pacing, and optimization

Read budget mode and level, current values, schedule, spend, delivery status, bid/target, budget history, rule bindings, outcome lag, and business economics. Pace against the approved curve. A platform budget recommendation or utilization signal does not authorize a change.

### Catalog and commerce

Read Business Center and advertiser ownership, catalog, feed logs, event-source binding, catalog diagnostics, product eligibility, product sets, store, price/currency, availability, and campaign/product binding. For TikTok Shop and GMV Max, also inspect:

- primary ad-account and shop restrictions;
- Product versus LIVE promotion type;
- campaign and product/video/live identity binding;
- campaign/session conflicts and current UTC/account-time-zone schedule;
- dedicated GMV Max reporting and its attribution scope;
- paid, organic, affiliate, cross-shop, no-ad-engagement, and total-channel order treatment;
- conflicting Video, Product, and LIVE Shopping Ads across every ad account linked to the shop, plus their manual restart state;
- inventory, price/promotion, refund/cancellation, and settled contribution.

Current official guidance says Product GMV Max attributes all paid and organic orders for selected products while active, including orders with no ad view or click. LIVE GMV Max can attribute paid and organic conversions across all shops in the selected LIVE event, including shops not used to create the campaign. Verify the current attribution window and product behavior at runtime; GMV Max-attributed GMV is not by itself paid-media incrementality.

### Lead generation

Read the selected capture path: Instant Form, website, or direct message. Verify page/form fields, library ownership, consent language, lead source, CRM connection, field mapping, deduplication, routing, timestamps, and deeper outcome postbacks.

Do not retrieve, download, expose, or transfer lead-level personal data unless the user explicitly requested that operation and purpose, consent, minimization, retention, destination, and access controls are validated. Prefer schema and aggregate verification for media diagnosis. Never claim a CRM sync or postback is complete from a plan.

### App promotion

Read app identity and ownership, objective and app-promotion type, supported optimization and retargeting events, OS/country, MMP/SAN/privacy state, attribution/re-attribution, postback settings, event volume/lag, and downstream activation, retention, payer, and cohort value. Campaign creation fields can be immutable or eligibility-gated; verify current schemas before preparation or execution.

### Reach and Frequency, TopView, and reservation planning

Use current inventory-estimate and contract/time-zone surfaces where eligible. Record audience, market, schedule, frequency, purchased unit, estimate time, and uncertainty. Calendar relevance, CPM, reach, share of voice, inventory, price, and booking lead time remain estimates until confirmed by current inventory or the responsible TikTok team.

### Search and audience research

Use current location, keyword, interest, behavior, hashtag, contextual, audience-size, overlap, and brand-safety surfaces as hypothesis inputs. Do not turn recommended categories or predicted searches into guaranteed demand. Customer-file audiences and audience sharing/upload are sensitive mutations and require separate approval and privacy checks.

## Diagnosis sequence

For no spend, low spend, cost spike, revenue decline, or scaling questions:

1. bind the exact advertiser and no more than the necessary entities;
2. confirm account time zone, issue date, objective, event, and complete comparison window;
3. verify reporting and business-outcome quality;
4. inspect operation/review/billing/eligibility and parent-child status;
5. inspect budget, bid/target, schedule, audience, placement, identity, asset, catalog/feed, destination, and event constraints;
6. compare non-overlapping history, peer context, concentration, mix, and recent changes;
7. query native diagnoses as one evidence input;
8. reconcile qualified advertiser-owned outcomes and economics;
9. state one leading mechanism, at least two alternatives, confounds, and a discriminator;
10. return act, test, hold, monitor, or revert with threshold provenance.

For fatigue questions, diagnose delivered-asset response and competing delivery/business explanations, then route creative replacement strategy and production to the creative skill.

## Preparation and execution

Read `references/live-execution-safety.md` and `references/platform-api-execution.md` before any TikTok write.

- Discover the exact method and schema immediately before use. Do not borrow defaults or retry semantics from Meta or Google.
- Creating a paused or disabled draft is an **execute-class mutation**. Use it only with exact creation approval, explicitly set and read back status, and never rely on an assumed default.
- Build the dependency chain and resolve immutable fields, allowlist features, cross-API prerequisites, shared resources, and conflicts before creating anything.
- Separate campaign, ad-group, ad, catalog, audience, pixel/event, CRM, shop/GMV session, identity, and automated-rule authority. Approval for one does not authorize the others.
- Present exact advertiser/entity IDs, current → proposed fields, absolute and percentage budget change, daily/flight exposure, time zone, schedule, and rollback or compensation.
- Check active rules and platform auto-budget features so a manual change is not immediately overridden.
- Before GMV Max activation, enumerate every same-shop cross-account Shopping Ad that the platform may pause or partially suppress. Approval and rollback must name those collateral effects and the manual restart plan; ending GMV Max does not automatically restart them.
- For a create/update chain, follow the current integration's ordering and rate rules. Do not run parallel mutations merely for speed.
- After every accepted mutation, perform a fresh independent read-back at configuration and dependency layers. Later verify eligibility, delivery, outcome, and commercial state separately.
- A paused draft is preparation of delivery, not a launch. Its creation remains execute-class; activation requires a new exact approval and top-to-bottom state verification.

If a response is missing or ambiguous, freeze writes, re-read the exact target and dependencies, classify the state, and retry only under the idempotency and duplicate-detection contract in `references/platform-api-execution.md`.

## Monitoring and automated rules

Monitoring remains read-only unless the user separately approves an action. A monitor should read only changed or decision-relevant state, respect outcome lag, and show the next read.

Before proposing an automated rule, inspect all existing rules, bindings, time zone, lookback, metric definition, action, frequency, cooldown, and execution history. Simulate against historical windows when possible. Never create rules from a vendor's fixed ROAS, CPA, quartile, day-count, or pacing threshold. Automated rules are live money/delivery controls and require exact approval, bounded exposure, logging, kill switch, and rollback.

## Capability snapshot used in this revision

On 2026-09-01, the connected progressive-disclosure server exposed 40 native aliases and a dispatcher whose discovery result contained 379 tools across 48 groups. This is evidence that broad coverage is available, not a stable interface guarantee. The operational rule is to rediscover and inspect the selected schemas every session.

The official Agentic Hub catalogue snapshot and 55-skill scope decisions are recorded in `assets/research/tiktok-agentic-hub-55.json`.
