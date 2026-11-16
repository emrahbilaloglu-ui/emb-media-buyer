# Operations and governance

High-quality media buying is a controlled operating system: defined ownership, traceable changes, reliable data, disciplined tests, and fast but reversible decisions.

## Roles and decision rights

Assign named owners for:

- business target and risk appetite;
- finance/unit economics;
- media strategy and account execution;
- measurement/analytics and data incidents;
- creative research, briefing, production, approvals, and rights;
- merchandising/offer/landing/product or sales operations;
- live-change approval and emergency rollback.

One person may hold several roles; the responsibilities must still be explicit. Tool access is not decision authority.

## Naming and identifiers

Use names for human scanning and immutable IDs for joins. A useful taxonomy can include market, objective, funnel role, product/offer, audience strategy, concept ID, experiment ID, owner, and launch cohort. Do not overload names with values that change.

Maintain registries for:

- platform account/campaign/ad-group/ad/creative IDs;
- product/feed/catalog and destination IDs;
- concept/master/derivative lineage;
- conversion and CRM outcome definitions;
- experiments and decision packets;
- approved changes, read-backs, rollbacks, and incidents.

## Launch readiness

Before launch verify:

- exact account, market, currency, time zone, objective, event, attribution, bid, budget, schedule, audience, placements, and exclusions;
- destination, offer, price, stock/capacity, form/checkout/app path, tracking parameters, and mobile behavior;
- creative copy, claims, product fidelity, rights, identity/authorization, format, safe areas, captions/accessibility, and destination match;
- pixel/tag/SDK/server events, value/currency/content IDs, deduplication, consent, offline/CRM mapping, and test-versus-production state;
- experiment assignment, forbidden edits, primary metric, guardrails, lag, decision rule, and owner;
- approval packet, financial exposure, monitoring, rollback, and communication plan.

Platform preview or validation is not customer-flow proof. Use an authorized end-to-end check at the appropriate environment and verify the downstream payload/record.

## Change log

Every material change records:

- request, approver, operator, and timestamps in account time zone plus UTC;
- account/entity IDs and experiment membership;
- field-level before and after values;
- reason, evidence, hypothesis, expected effect, and risk;
- financial exposure and scope;
- mutation receipt/change-event reference;
- independent read-back result;
- monitoring and rollback conditions;
- partial failures, follow-ups, and final outcome state.

Avoid multiple untracked edits in the same learning window. If emergency action requires a bundle, label the period non-diagnostic.

## Cadence

Cadence follows risk, spend, lag, and business cycle—not a universal calendar.

### Technical/delivery checks

Look for account/billing errors, disapprovals, zero or abnormal spend, budget/pacing deviation, broken destinations, feed/stock issues, tracking gaps, creative authorization, and data incidents. These may warrant immediate escalation without waiting for outcome lag.

### Performance/quality reviews

Use complete equivalent windows. Reconcile platform, business, and causal ledgers; inspect concentration and funnel breaks; review contribution and marginal response; evaluate experiments against preregistration; inspect creative concept coverage and production throughput; review capacity and calendar.

For a WBR, use the canonical contract in `references/account-review-and-optimization.md` and route the next action to its actual owner.

For a recurring review that decides on active paid ads, run the read-only gate in `references/paid-decision-sweep.md` before publishing a complete decision report. Archive its scoped sources, full ledger, and previous/open decisions; verify the paid packet against that artifact. A top-N message, successful process exit, or provider receipt alone does not close the review. This is a contract for the current cadence, not a request to create or alter a schedule.

### Strategic reviews

Revisit targets, customer/market mix, channel role, response curves, incrementality, MMM/experiments, creative/offer roadmap, measurement debt, platform dependency, and forecast scenarios.

## Incident response

Classify incidents such as uncontrolled spend, tracking outage, wrong destination/offer, policy/account suspension, feed/price/stock error, duplicate events, currency/time-zone error, or unauthorized change.

Sequence:

1. protect users and financial exposure within existing authority;
2. preserve evidence and exact current state;
3. identify scope, start time, owner, and affected decisions;
4. stop or revert only if authorized by the incident contract or user;
5. verify state independently;
6. repair data and reprocess where possible;
7. mark contaminated analysis/test windows;
8. document cause, detection gap, prevention, and remaining unknowns.

Do not erase or rewrite historical decision evidence to make the incident disappear.

## Executive reporting

Lead with business outcome, decision, risk, and owner. Keep platform metrics as explanatory drivers. Include source/window/currency/attribution beside every material number, distinguish fact/inference/unknown, and show what changed since the prior comparable read.

Report “no decision” when the evidence is not ready. Activity, number of optimizations, or number of creatives launched is not performance by itself.
