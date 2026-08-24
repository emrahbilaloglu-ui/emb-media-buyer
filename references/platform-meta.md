# Meta Ads operating guide

Use current account state, Meta documentation, and the Marketing API as primary evidence. Meta’s automation and ranking systems change; verify every eligibility rule, field, limit, and product name at runtime.

## Account and decision frame

Record business/account identifiers, currency, time zone, billing state, market, buying type, objective, optimization event, attribution setting, budget type, bid strategy, schedule, conversion location, destination, and active experiment membership.

Inspect the exact current configuration at campaign, ad-set, ad, creative, pixel/dataset, catalog, product-set, and landing level. Names are labels, not bindings.

## Measurement

Verify:

- Pixel and Conversions API sources, event names, parameters, value/currency, content identifiers, and event-id deduplication;
- domain/source ownership, consent handling, advanced matching where applicable, diagnostics, test versus production events, and event quality limitations;
- optimization event versus reporting event and primary business outcome;
- attribution window/model, click/view treatment, modeled data, reporting lag, and breakdown availability;
- advertiser-owned orders/CRM and refunds/returns on matched definitions;
- offline events and lead-stage mapping where used.

Do not interpret an Events Manager green state as proof that real events deduplicate, attribute, and reconcile. Verify an authorized end-to-end path and downstream record when the decision depends on it.

## Delivery and structure audit

Inspect:

- campaign objective, special category, auction/reservation or current buying mode;
- campaign versus ad-set budget, shared allocation, schedules, spend limits, and billing constraints;
- bid strategy, cost/value target, optimization goal, conversion location, and delivery status;
- market, age/location controls, audiences, exclusions, overlap, expansion/automation settings, placements, devices, and brand-safety controls;
- learning/delivery status and material edit history;
- spend/outcome concentration by campaign, ad set, ad, placement, device, market, audience, time, and product;
- policy, destination, feed/catalog, stock, asset, or account errors.

Do not store a universal “learning phase” conversion count or edit percentage. Read current official guidance and the account’s own delivery state.

## Automation and ranking

Meta’s engineering publications describe increasingly large retrieval/ranking systems and automated campaign/creative products. This supports two operational facts: the platform can evaluate far more candidate combinations, and actual delivery may diverge from the advertiser’s simple labels.

It does **not** prove that audience strategy is irrelevant, that broad targeting always wins, that every account should consolidate, or that creative alone determines performance. Verify the account’s constraints, candidate assets, product feed, event quality, delivered mix, and marginal business outcomes.

Record current states for Advantage+ or equivalent automated audience, placement, budget, campaign, catalog, and creative features. Verify which controls are suggestions versus hard constraints and whether the platform generated, cropped, translated, or combined assets.

## Creative diagnosis

Bind master/derivative assets to creative IDs, ads, ad sets, campaigns, placements, products, copy variants, destinations, and automated transformations. When breakdowns cannot isolate an asset, scope the finding to the entity level.

Read the funnel: delivery cost → outbound intent → landing continuity → advertiser-owned outcome → contribution. All-click CTR and engagement can be diagnostic context; they are not commercial success metrics.

Treat frequency, age, and declining CTR as fatigue evidence only after checking reach growth, newly reached share where available, placement/audience mix, auction cost, offer/page/stock, tracking, calendar, and comparable account history.

## Experiments and lift

For A/B tests or Conversion Lift:

- verify current eligibility and setup in the account;
- preregister arms, assignment, primary metric, business effect, guardrails, sufficiency source, exposure/lag, and decision rule;
- report delivery divergence, conversion definitions, attribution, and reconciliation;
- distinguish a randomized arm comparison from incremental lift;
- do not reuse the platform confidence display as the entire decision rule.

## Common false conclusions

- Highest spend is not an independent winner; allocation is endogenous.
- Highest platform ROAS is not profit and may reflect retargeting, returning buyers, brand demand, or attribution.
- Broad, automated, or consolidated is not a universal answer.
- More creative volume is not diversification when concepts are duplicates.
- A campaign/ad-set/ad name does not prove targeting, asset, or destination.
- API acceptance or Ads Manager visibility does not prove delivery or outcome.

Use references/runtime-source-registry.md for current official Meta sources and retrieval rules.

