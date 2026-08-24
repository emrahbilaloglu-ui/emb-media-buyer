# Data quality and diagnosis

Resolve whether the evidence is fit for the decision before interpreting performance.

## Source manifest

For every source, record:

- system, owner, account or property identifier, and retrieval time;
- reporting window, comparison window, time zone, currency, and grain;
- conversion and value definitions;
- attribution window/model and click/view treatment;
- ingestion, reporting, sales, refund, and conversion lag;
- filters, exclusions, deduplication keys, consent mode, and modeled-data status;
- coverage, missingness, revision behavior, and known incidents;
- join keys to campaign, ad group/set, ad, creative, product, landing page, customer, or opportunity.

Never coerce an absent metric to zero. Never merge currencies, time zones, attribution settings, or conversion definitions without an explicit transformation.

## Data-quality gate

Assess these dimensions:

1. **Identity:** correct platform, account, entity, market, and date scope.
2. **Completeness:** all expected entities, days, spend, and outcomes are represented.
3. **Validity:** types, signs, ranges, and category values are plausible.
4. **Consistency:** totals reconcile across grains and equivalent sources within explained tolerance.
5. **Uniqueness:** duplicate rows/events are understood and removed or intentionally retained.
6. **Timeliness:** conversion, refund, CRM, and reporting lag are compatible with the decision.
7. **Binding:** delivered creative, destination, event, product, query, audience, and placement are actually traceable.
8. **Comparability:** compared cells share the relevant operating conditions.
9. **Business reconciliation:** platform-attributed outcomes are compared with advertiser-owned truth on matched definitions.

Classify the gate as pass, pass_with_limits, or fail. A fail on a field essential to the requested decision forces hold or measurement repair; it does not forbid unrelated descriptive work.

## Tracking and event checks

Inspect the complete path from user action to reported outcome:

- tag/pixel/SDK firing and consent state;
- server/client event matching and event-id deduplication;
- event name, value, currency, content/product identifiers, and timestamp;
- primary versus secondary optimization status;
- domain/app/source ownership and destination consistency;
- offline conversion imports and CRM stage mapping;
- test events versus production events;
- duplicate, missing, delayed, out-of-order, or modeled events;
- platform diagnostics and advertiser-owned raw-event evidence.

A green dashboard badge is not end-to-end proof. Use a real or controlled journey when authorized, verify the downstream record, and distinguish browser receipt, platform receipt, deduplicated processing, attribution, and business settlement.

## Funnel diagnosis

Walk the observable chain rather than reading one headline:

1. eligibility and delivery;
2. reach, impressions, frequency, and auction cost;
3. attention and outbound intent appropriate to the format;
4. click-to-landing or app-open continuity;
5. page, feed, store, or in-app engagement;
6. qualified intermediate action;
7. conversion and conversion quality;
8. settled revenue, contribution, pipeline, retention, or another business outcome.

Compute step-to-step rates with counts. The break location changes the remedy:

- no eligibility or delivery: policy, bid, budget, audience, schedule, feed, asset, or account constraint;
- expensive delivery with stable downstream rates: auction/mix/quality hypothesis;
- weak outbound intent with healthy downstream rates: proposition/creative/audience fit hypothesis;
- clicks without landings: speed, redirects, destination, accidental clicks, or measurement;
- landings without qualified action: message match, offer, UX, price, trust, stock, or lead friction;
- platform conversions without business outcomes: definition, dedup, attribution, fraud/quality, CRM, refund, or lag;
- healthy conversion but weak contribution: economics, mix, costs, or capacity rather than ad appeal.

## Concentration and mix

Report spend and outcomes by entity, time, placement, device, geography, audience, product, query, creative, and new/returning status where available. A total can improve because the system shifted mix, even if no component improved.

Flag one entity carrying most spend/outcomes; averages dominated by a promotion, outlier, repeat customer, brand query, or retargeting cell; Simpson’s paradox; sparse cells; and mid-period changes to budget, bid, event, destination, creative, feed, attribution, or consent.

## Creative and entity binding

Names are not proof. Verify immutable IDs and lineage:

generation/source asset → master → derivative/variant → ad creative → ad → ad group/set → campaign → delivered placement/destination

Account for automated combinations, dynamic creative, cropping, text variation, generated assets, catalog selection, final URLs, tracking templates, and asset replacement. If the platform only reports entity-level outcomes, do not attribute them to an individual asset.

## Diagnostic hypotheses

For each break, inspect at least:

- demand/calendar and competitive conditions;
- bid, budget, pacing, learning, eligibility, and policy;
- audience/query/product/placement/device mix;
- creative concept, proof, novelty, format, and message-to-destination match;
- offer, price, promotion, feed, merchandising, stock, page/app, and checkout/form;
- lead handling, sales capacity, qualification, and close lag;
- tracking, consent, deduplication, attribution, modeled data, and source outages;
- random variation and regression to the mean.

State what evidence would separate the leading explanations. Auction pressure or platform automation usually cannot be observed directly; label them inference unless supported by a relevant diagnostic.

## Reconciliation states

Use one state:

- reconciled: matched definitions and explained gap;
- partially_reconciled: known mismatch with quantified coverage or gap;
- unreconciled: comparable sources exist but have not been aligned;
- unavailable: advertiser-owned outcome cannot be accessed;
- not_applicable: no outcome reconciliation is required for this specific descriptive question.

Profitability or scaling requires reconciled or explicitly bounded partially_reconciled evidence plus unit economics. Otherwise use hold, test, or monitor.

