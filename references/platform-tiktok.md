# TikTok Ads operating guide

Use current TikTok Ads Manager/Business API reads, advertiser-owned outcomes, Events Manager evidence, and official documentation. Smart+ workflows, learning guidance, attribution, creative tools, and reporting fields change frequently; verify them at runtime.

When TikTok for Business MCP is connected, read `references/tiktok-mcp-operations.md`. Discover the current tool surface and schema rather than assuming the connector exposes a remembered endpoint, default, limit, or permission.

## Account and structure

Record advertiser/account identifier, currency, time zone, billing, market, objective, campaign type and automation mode, optimization location/event, bid strategy/target, campaign/ad-group budget, schedule, attribution, audience controls, placements, identity, destination, catalog, and active test membership.

Resolve the exact current hierarchy and terminology. Older Standard and Smart+ instructions may not match the current unified flow. Never force a remembered setup onto the live account.

Inventory separate product families before concluding account coverage: regular campaigns, Upgraded Smart+, Search Ads, Shop/GMV Max, app promotion, lead generation, Reach & Frequency/reservation, and any active automated rules. A product family can require a separate configuration or reporting route. Missing rows in an integrated report are not evidence that the product did not deliver.

## Measurement

Verify:

- TikTok Pixel, Events API, SDK or MMP sources;
- event names, parameters, value/currency, content identifiers, timestamps, and source coverage;
- event-id based client/server deduplication and diagnostics;
- optimization event versus reporting event and advertiser-owned outcome;
- attribution window/model, click/view treatment, engaged-view treatment where applicable, modeled data, and conversion lag;
- consent and regional requirements;
- CRM/order/cohort reconciliation, lead quality, refunds/cancellations, and offline outcomes.

A received event is not automatically deduplicated, attributed, qualified, or settled. Verify each state when material.

For leads, bind the platform lead to valid/contactable/qualified/attended/won/collected CRM stages and inspect consent, routing, deduplication, sales capacity, and postback. For apps, bind platform/MMP events to activation, retention, payer/subscriber state, net cohort value, and privacy-framework limitations.

## Delivery and automation

Inspect:

- objective, optimization event, bidding/target, budget, schedule, and delivery/learning status;
- market, age/location controls, audiences, exclusions, placements, expansion, and automation settings;
- creative/asset groups, identities, Spark authorization, catalog/product binding, destination, and automated creative features;
- policy, account, asset, feed, landing, and billing constraints;
- spend/outcome concentration by campaign, ad group, ad, creative, placement, market, time, product, and audience where available;
- material edit/change history and active experiments.

Do not store a universal learning-phase event count, budget multiple, day count, or scale percentage. Read the current account and official guidance.

## TikTok Shop, catalog, and GMV Max

Treat catalog and commerce as a binding system:

Business Center/store ownership → catalog/feed → event source → product/SKU → product set or eligible pool → identity/video/live room → campaign/session → reported order → settled contribution

Verify feed logs and diagnostics, event-source binding, content IDs, country/currency, product eligibility, price, stock, promotion, store and primary-ad-account restrictions, active campaign/session conflicts, and campaign/product/video/live binding.

Keep Product and LIVE GMV Max separate and use their current dedicated configuration and reporting surfaces. Current official documentation says Product GMV Max can attribute all paid and organic orders for selected products while active, even without an ad view or click. LIVE GMV Max can attribute paid and organic conversions across all shops in the selected LIVE event, including shops outside campaign setup. Verify the current attribution window; reconcile organic, affiliate, paid, no-ad-engagement, cross-shop, total-channel, refund/cancellation, and contribution views before budget decisions.

Before activating GMV Max, inventory conflicting Video, Product, and LIVE Shopping Ads across every ad account linked to the shop. Current guidance says same-product or same-shop ads may be paused or partially suppressed regardless of the account that created them, and they do not restart automatically when GMV Max ends. Name all collateral effects, inaccessible accounts, manual restart owners, and rollback steps in the approval and read-back plan.

First-order or Max-delivery boosts are bounded tests, not universal playbooks. Verify the eligible pool, target date and time zone, existing sessions, campaign state, independent budget, ROI mode, cap, schedule end, expected downside, exact approval, and session read-back. Do not inherit a vendor's default percentage or boost count.

LIVE diagnosis must separate live infrastructure and schedule, initial traffic acquisition, stream reach/viewership, product/offer/price competitiveness, stock, host and operational capacity, budget utilization, and checkout/order quality. Creative production remains outside this skill.

## Lead, app, search, and reservation products

- **Lead generation:** choose Instant Form, website, or direct message from qualification needs, lawful data flow, friction, and retargeting requirements. Verify fields, form ownership, CRM mapping, dedupe, routing, deeper-signal postback, retention policy, and actual integration state at runtime.
- **App promotion:** verify app ID/ownership, app-promotion type, optimization and retargeting events, iOS/Android constraints, MMP/SAN/privacy state, attribution and postback behavior, retention, payer value, and cohort horizon.
- **Search Ads:** verify keyword/query reporting, negative keywords, landing continuity, search volume and recommendation definitions, and cannibalization/incrementality evidence. Suggestions are hypotheses, not guaranteed demand.
- **Reach & Frequency, TopView, and reservation:** combine business calendar and market relevance with current inventory, contract, delivery-time-zone, reach/frequency, cost and share-of-voice evidence. Estimates and lead times must be confirmed before booking or commitment.

## Creative and identity

TikTok-native execution is a practitioner hypothesis, not a license to optimize only view metrics. Track concept, angle, proof, hook, creator/identity, format, duration, sound, caption, CTA, product, destination, authorization, and master/derivative lineage separately.

Verify what actually delivered after automated combinations, edits, templates, enhancements, or catalog selection. Compare retention only across compatible durations/definitions. Use views, hold rates, clicks, and engagement to locate a break; use qualified advertiser-owned outcomes and contribution for commercial decisions.

Spark Ads and creator content require valid identity/authorization and rights. Public content is not automatically reusable. Generative assets may require labels or disclosures under current platform rules.

The media buyer diagnoses delivery, binding, objective fit, qualified outcome, economics, and the commercial test. Route concept development, hooks, scripts, storyboards, generation, editing, and asset-level creative QA to a dedicated creative skill.

## Tests and measurement products

TikTok offers split testing, attribution tools, lift products, and measurement integrations in eligible contexts. Verify availability, population, metric definitions, and methodology in the account. Preregister arms, practical effect, primary business metric, guardrails, sufficiency method, lag, and decision rule.

Do not generalize a vendor case study, creator-reported benchmark, or platform marketing claim to the account. Treat it as a hypothesis until account evidence or a design supports it.

## Common false conclusions

- High thumb-stop/view/engagement metrics do not prove qualified demand.
- A trending sound, hook, or creator is not a timeless rule.
- Smart+ or full automation is not universally superior.
- A campaign/ad-group/ad name does not prove the delivered creative or audience.
- Low delivery is not automatically solved by a higher budget or looser bid.
- API acceptance is not proof of visible state, delivery, or outcome.

Use references/runtime-source-registry.md for current official TikTok sources and retrieval rules.
