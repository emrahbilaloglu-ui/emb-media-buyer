# Google Ads operating guide

Use current Google Ads account reads, advertiser-owned outcomes, official help/developer documentation, and change history. Product behavior, experiment eligibility, consent requirements, and campaign controls are volatile; verify them at runtime.

## Account and conversion frame

Record customer and manager identifiers, currency, time zone, billing, market, campaign type/subtype, objective, bidding strategy, budget/shared budget, networks, schedule, locations, languages, devices, audience signals/segments, conversion goals, attribution, and experiment membership.

Audit conversion actions before bidding or performance:

- primary versus secondary status and account-default versus campaign-specific goals;
- event source, category, value, currency, count method, window, attribution model, and lag;
- enhanced conversions, consent mode, tag/server/offline imports, identifiers, deduplication, and diagnostics;
- inclusion of page views, micro-conversions, duplicates, calls, store visits, modeled outcomes, or CRM stages;
- advertiser-owned order/pipeline reconciliation and refund/cancellation adjustments where supported.

Do not combine rows that optimize to materially different goal sets.

Google states that modeled conversions can take up to five days to process and stabilize, and observed plus modeled conversions can be reported together. When modeled conversions are present, treat that recent window as potentially incomplete. Determine the account's complete-outcome window as the maximum of applicable model stabilization, observed conversion lag, and import/reporting latency; do not impose a universal D-6 rule on accounts or metrics that do not contain modeled conversions.

## Search

Inspect campaign/ad-group structure, match types, keywords, search terms, negative keywords/lists, brand/non-brand intent, location semantics, language, networks/partners, ads/assets, final URLs, tracking templates, landing pages, quality diagnostics, impression share constraints, bidding, and conversion goals.

Avoid these traps:

- branded demand or returning customers inflating apparent acquisition efficiency;
- search-term/query intent hidden inside aggregate keyword/campaign results;
- broad or automated matching judged without query, conversion quality, and negative controls;
- low impression share treated as a budget problem without checking rank, targets, eligibility, and marginal economics;
- paid-search association treated as incremental demand. Demand drives both searches and sales.

## Shopping and Performance Max

Verify Merchant Center/account/feed health, products, identifiers, prices, availability, policy, destination, shipping/tax, promotions, custom labels, product groups/listing groups, brand controls, URL expansion, asset groups, audience signals, search themes or current equivalents, final URLs, exclusions, and conversion goals.

Bind products and assets to actual asset groups/campaigns and inspect available channel, asset, product, query/category, audience, placement, and new-customer reporting. Do not assume a Performance Max total is incremental or that an asset-group label identifies delivered contribution.

When comparing PMax with Standard Shopping, Search, Demand Gen, YouTube, or another campaign, account for overlap, cannibalization, budget/bid changes, branded demand, feed changes, new/returning mix, and experiment design. Use the platform’s current experiment structure when eligible; do not infer uplift from before/after totals.

## Demand Gen, YouTube, Display, and Apps

Verify inventory/network scope, audience and expansion settings, placements/content controls, frequency controls, creative/asset combinations, formats, destination, bidding, conversion goals, view-through treatment, engaged-view definitions, app/MMP links, and brand-safety suitability.

Video views and view-through conversions can inform delivery and exposure; they are not advertiser-owned contribution. Bind videos, images, text assets, product feeds, and final URLs to delivered combinations where reporting permits.

## Bidding, budgets, and diagnostics

Inspect strategy status, target history, portfolio strategy, budget constraints, impression-share diagnostics, conversion lag, auction seasonality, policy, audience/geo size, and change events. A recommendation to loosen a target, raise a budget, or adopt automation is a hypothesis until tested against marginal business economics.

For reporting windows spanning 2026-08-17, check the account for Google’s global rollout of changed target-based bidding behavior in campaigns that are Limited by budget. Google states that eligible campaigns may move more consistently toward the stated target, including after budget changes; a campaign that historically outperformed a loose target may therefore show a level shift without an advertiser edit. Verify rollout state, strategy, target, limited-by-budget state, conversion cycles, and change history before diagnosing the movement. The official transition guidance does not prove that raising budget or accepting a looser target is profitable for this advertiser.

Use Change Events or the current equivalent to reconstruct current/previous state. A UI summary is insufficient when a material edit may explain the period.

## Experiments and lift

Google supports campaign experiments, Performance Max experiments, conversion lift, and geo-based lift in eligible contexts. For each, verify current eligibility and methodology, preregister the business effect and decision rule, inspect power/feasibility, include conversion lag, read uncertainty, and reconcile the outcome definition.

Do not treat platform-reported uplift as a universal expectation. A test result applies to its market, period, treatment, audience, products, and measurement system.

## Common false conclusions

- Search ROAS is not automatically incremental demand.
- PMax totals do not reveal which channel, query, product, or asset caused the outcome.
- More asset strength or a recommendation score does not equal more contribution.
- Highest conversion count can reflect the wrong conversion action.
- Budget limited does not mean budget should be raised.
- A successful experiment setup does not guarantee adequate power or clean execution.

Use references/runtime-source-registry.md for current official Google sources and retrieval rules.
