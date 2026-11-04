# Account review, diagnosis, and optimization

Use this guide for account-specific audits, anomaly diagnosis, benchmarks, weekly business reviews, funnel analysis, portfolio recommendations, and monitoring. It converts broad optimization requests into traceable decisions; it does not create permission to mutate an account.

## Establish the review mode

Choose the narrowest mode that answers the decision:

- **cold start:** little or no comparable delivery history; assess readiness, market evidence, measurement, economics, and a bounded learning plan;
- **launch check:** configuration and dependencies are prepared but commercial evidence is incomplete;
- **mid-flight diagnosis:** a scoped symptom such as no spend, underdelivery, cost increase, quality decline, or pacing variance;
- **full account audit:** cover structure, delivery, measurement, business outcomes, concentration, automation, and governance;
- **benchmark:** describe an entity relative to a genuinely comparable peer distribution;
- **weekly business review:** current versus prior comparable period plus longer context and entity movers;
- **portfolio decision:** allocate, scale, hold, cut, test, or revert under business constraints;
- **monitor:** evaluate preregistered triggers without turning surveillance into autonomous optimization.

Do not infer advertiser maturity from account age, spend, or a platform label alone. Record what evidence is actually available: delivery history, lag-complete outcomes, stable definitions, comparable change episodes, experiments, advertiser-owned economics, and operational capacity.

## Prove coverage before diagnosis

Build an entity and evidence manifest before summarizing performance. Report:

- expected, observed, unique, missing, duplicate, deleted/archived, and inaccessible entities;
- regular, automated/Smart+, shop/GMV, app, lead, search, and reservation products in separate source paths where the platform requires them;
- reporting endpoint, report type, grain, dimensions, metrics, filters, pages or tasks, row limits, and retrieval time;
- account time zone, UTC translation, currency, attribution, conversion definition, reporting latency, and outcome lag;
- source rows that returned zero, calls that returned no rows, and fields that were unavailable or unsupported;
- configuration, review, change-log, delivery, business-outcome, and experiment coverage.

A successful request is transport evidence. It does not prove complete rows, the intended date range, canonical conversion mapping, or account coverage. Reconcile totals upward and downward where possible, and state why differences remain.

## Route metrics by objective and business outcome

First identify campaign objective, optimization event, business job, and material share of spend. Then choose the diagnostic chain.

| Objective/job | Delivery diagnostics | Business decision evidence |
|---|---|---|
| Reach/awareness/reservation | eligible reach, impressions, CPM, frequency distribution, inventory, share of voice, viewability or brand-safety evidence | brand lift, search/traffic lift, reach quality, incremental business outcome where feasible |
| Video views/engagement | view definitions, completion/retention at compatible durations, CPV, engagement, delivered placement and asset | downstream qualified behavior; attention is diagnostic, not commercial proof |
| Traffic | impressions, clicks, CTR, CPC, landing-page views, destination and UTM continuity | qualified sessions, downstream funnel, orders/leads and contribution |
| Web/app conversion | spend, conversion count, CPA, value, ROAS, delivery and event status | reconciled new/qualified outcomes, margin or cohort contribution, payback, incrementality |
| Lead generation | form/DM/site delivery, CPL, form completion, field and routing state | valid, contactable, qualified, attended, won and collected contribution by complete cohort |
| App promotion | install/activation events, CPI/CPA, OS/country/privacy and MMP state | retained/paying user, net cohort value, payback, incremental lift |
| Shop/GMV/live commerce | store/product eligibility, delivery, budget use, product/video/live binding, reported GMV/ROI | settled orders, paid/organic attribution scope, price/stock, refunds, contribution and credible incrementality |

Do not show CPA merely because a field exists. If conversion activity is immaterial to the reviewed spend or the event is invalid, use the objective-appropriate delivery evidence and name the missing business link.

## Detect what changed

For a performance shift, compare a non-overlapping, definition-consistent baseline and build a change map:

1. exact symptom, entity scope, first affected time, magnitude, count/denominator, and latency state;
2. configuration and status changes before and during the shift, with actor and timestamp when available;
3. mix changes across campaign, ad group, objective, market, placement, audience, product, identity, asset, device, and time;
4. tracking, attribution, consent, CRM, catalog/feed, destination, stock, price, offer, sales-capacity, and calendar changes;
5. platform diagnostics and recommendations, recorded as tool outputs rather than verified causes;
6. leading mechanism, at least two rivals, contradictory evidence, and the cheapest discriminator.

Temporal alignment is not causation. A new campaign can coincide with a legacy spend decline without proving cannibalization. An automated diagnosis can shorten triage but cannot replace source coverage, business reconciliation, or a counterfactual.

## Benchmark contract

Benchmark only when the pool is comparable on the dimensions that can materially change the metric. At minimum record:

- same advertiser or a lawful, governance-safe anonymized population;
- same objective, entity grain, metric definition and direction;
- market, product or business model, automation mode, bid strategy, optimization event, attribution, and window;
- delivery and outcome lag state;
- peer count, distinct values, missing or ineligible entities, distribution method, and retrieval latency.

Within-account empirical P25/P50/P75 and percentile rank can describe context. They do not establish profitability, a kill/scale rule, or a platform best practice. A P75 result can still lose money; a P25 result can still be strategically or incrementally valuable. Cross-account and vertical benchmarks have additional selection, privacy, survivorship, and definition risks.

Use `scripts/account_review.py benchmark` for reproducible empirical quantiles after the comparability contract is satisfied.

## Funnel contract

Define each stage, identity unit, event semantics, source, deduplication, window, and lag before calculating a rate. For a true user funnel, stage populations should usually be nested; event counts may not be. Do not label an event ratio a user conversion rate.

For each transition report:

- upstream and downstream counts;
- rate and denominator;
- current versus comparable baseline when available;
- segment mix across device, placement, market, audience, product, destination, and delivered asset only when bindings are verified;
- suspected leak mechanism, alternatives, confounds, and evidence needed;
- scenario impact as arithmetic, not a promised causal lift.

Do not import fixed “critical” drop-off percentages. Severity comes from expected business contribution at risk, data reliability, reversibility, and the cost of waiting. Use `scripts/account_review.py funnel` for stage arithmetic; it deliberately emits no severity or root cause.

## Health and money at risk

A health review covers:

- account/billing/access and policy/review status;
- objective, event, bid, budget, schedule, audience, placement, identity and destination binding;
- tracking, reconciliation and business-outcome availability;
- delivery, pacing, concentration, anomaly, and active automation conflicts;
- feed/catalog/product/store and app/lead dependencies where applicable;
- experiment integrity, change history, approval, and rollback readiness.

Prioritize findings by expected business consequence, evidence quality, financial exposure, reversibility, time sensitivity, and cheapest evidence. If a score or letter grade is useful for navigation, show its formula and components, and never let it authorize an action. “Spend at risk” must state the window, definition, counterfactual or threshold source, and uncertainty; historical spend on a weak cell is not automatically recoverable waste.

## Weekly business review

Use complete, equivalent periods in account time zone and state report freshness. A WBR should contain:

1. one scoped verdict: act, test, hold, monitor, or revert;
2. objective-aware current versus prior KPI using summed numerators and denominators, never an average of row-level ratios;
3. spend and business-outcome movement with absolute and relative changes;
4. at least four comparable periods when available, labeled as descriptive context rather than proof of persistence;
5. campaign/entity movers for spend and outcomes; do not call a ratio decomposition causal;
6. measurement, concentration, quality, capacity, and automation risks;
7. a prioritized do-next list routed to read-only evidence repair, a controlled media intervention, or a creative/commerce/CRM owner.

Sparse movement remains sparse. Do not dramatize a small absolute lead/order change because its percentage is large. Use `scripts/account_review.py review` for reproducible ratio aggregation and entity movement descriptors.

## Recommendation and optimization contract

For every material optimization or paid KEEP/WATCH recommendation, record:

- symptom and verified scope;
- intended business outcome and acquisition unit;
- mechanism and evidence chain;
- competing explanations and open gates;
- exact current and proposed state;
- threshold provenance and whether it is approved;
- expected downside/base/upside as scenarios;
- financial exposure, capacity, lag, experiment impact, cooldown, monitoring, and reversal;
- whether the result is read-only advice, a paused draft, or an approved live operation.

For active paid continuation use the compact contract in references/budget-pacing-and-scaling.md: change since the previous review, separate last-outcome dates/spend, waiting/stopping costs, current authorized context, expected information, next existing read, and trigger response. Reassess a met trigger; no purchase-present KEEP or generic WATCH fallback. Use the same source evidence standards for stopping and continuing. Narrative counts must match the numeric ledger; do not narrate two platform attributions as two verified store orders.

Classify a proposed pause as operational risk choice or inferiority claim. A qualitative risk stop/rotation needs a sourced rationale and counterevidence, not a fabricated numeric threshold or proof that a low-spend sibling is superior. Fresh purchases and low spend affect the judgment without granting automatic immunity or proving failure. Check real promoted-source bindings before applying an owner MAIN-retention rule. Pausing a shared-budget ad is not guaranteed cash saving; a last-child pause needs a separate parent/slot consequence and an authority check for any parent or replacement change.

Platform bid suggestions, automated-rule outputs, diagnostic agents, health scores, benchmark quartiles, and vendor forecasts are advisory inputs. They do not override economics or user authority. Never automatically:

- pause after a fixed ROAS, CPA multiple, day count, or grade;
- reallocate from bottom to top quartile;
- increase by a fixed percentage because a cell is budget constrained;
- claim the learning phase will be preserved or reset without current account evidence;
- infer incremental halo from attributed or omnichannel totals;
- turn a pacing category into a budget mutation.

## External business KPI loop

When the true outcome is outside the ad platform, define a governed binding:

platform entity and click/view evidence → lawful identity or cohort key → advertiser-owned event → quality/state → value or contribution → availability lag → platform feedback signal, if approved

For predicted LTV, margin-adjusted ROAS, retention, lead score, or custom outcomes, record model version, training and validation population, horizon, backtest error, calibration, missingness, drift, uncertainty, and fallback. Keep predicted and realized outcomes separate. A feedback or CRM connection is not complete until the real integration, field mapping, consent, delivery, and read-back are proven.

## Routing boundary

The media buyer owns business framing, evidence quality, account configuration, delivery context, objective-aware diagnosis, test design, budget decision, and outcome read. Route hooks, scripts, storyboards, creative concepts, asset generation/editing, and asset-level creative QA to a dedicated creative skill. Supply that workflow with product truth, approved claims, delivered-asset evidence, audience/job, placement needs, destination match, and the media test contract.

The 2026-09-01 TikTok Agentic Hub reconciliation is machine-readable at `assets/research/tiktok-agentic-hub-55.json`.
