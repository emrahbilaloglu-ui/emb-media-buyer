# Business-model playbooks

Use the platform metric only after mapping it to the business’s acquisition unit, source of truth, cash cycle, and capacity.

## Ecommerce and DTC

### Decision chain

delivery → qualified visit → cart/checkout → settled order → net revenue → contribution → retained/new customer value

### Required evidence

- commerce-platform orders and line items, cancellations, refunds/returns, taxes, discounts, shipping, and customer identity;
- product/variant margin, payment/marketplace fees, fulfillment and shipping subsidy;
- new versus returning logic and cohort horizon;
- product availability, price, promotion, landing/collection, checkout, and fulfillment capacity;
- platform conversion definition, value, content IDs, catalog/feed mapping, and deduplication;
- blended spend/revenue and channel-attributed views on matched windows.

### Decision metrics

Use contribution per order/customer, contribution after ads, new-customer CPA, new-customer revenue, payback, MER/blended efficiency, refund/return-adjusted value, and stock/capacity guardrails. ROAS without margin and customer mix is incomplete.

### Common traps

Returning buyers and brand demand can subsidize prospecting; platform value can precede refunds; one high-AOV order can dominate sparse cells; feed errors and stock-outs masquerade as ad issues; click-efficient promises can lower downstream conversion.

## Lead generation and local services

### Decision chain

lead → valid/contactable → qualified → appointment/demo → attended → opportunity → won → collected contribution

### Required evidence

- form/call/chat source, event identifiers, deduplication, consent, and spam/fraud status;
- CRM stages with immutable lead/opportunity IDs and timestamps;
- contact, qualification, show, close, cancellation, collection, and sales-cycle rates by source/cohort;
- capacity by location/team/service, routing, speed-to-lead, and sales follow-up;
- revenue/contribution per won outcome and variable sales/service cost.
- capture path and friction: native form, website form, direct message, call, or chat;
- real CRM/integration state, field mapping, deduplication, routing, response capacity, and deeper-outcome postback;
- lawful purpose, notice/consent, retention, access, minimization, and deletion for lead-level personal data.

### Decision metrics

Use cost per valid/qualified lead, appointment, opportunity, and won customer; expected contribution per lead; pipeline and collected contribution; stage conversion; sales lag; capacity and lead-quality guardrails.

### Common traps

Cheap forms can be spam or unreachable; CRM missingness can reward the source with worse integrations; short reporting windows punish long-cycle channels; sales-team speed and capacity confound media; platform lead counts are not customers.

Do not inherit a universal speed-to-lead, lead-retention, learning-volume, form-length, or bid-progression rule from a vendor playbook. Read current platform policy and integration behavior, then derive the operating target from comparable CRM cohorts and the sales team's actual capacity.

## SaaS and B2B

### Decision chain

visit/content → signup/lead → activation/MQL → SQL/opportunity → won → retained gross-margin value

### Required evidence

- product analytics, CRM, billing, contracts, churn/retention, expansion, and servicing cost;
- identity resolution from ad click/view to account/opportunity where lawful and feasible;
- account-level versus person-level attribution and buying-committee duplication;
- pipeline stage definitions, probabilities, sales cycle, source history, and offline conversion imports;
- market/segment/contract-size mix, capacity, and payback constraint.

### Decision metrics

Use cost per activated account, qualified opportunity and win; sourced/influenced pipeline with definitions; closed-won gross contribution; gross-margin LTV/CAC; payback; retention; and segment-level capacity.

### Common traps

One enterprise opportunity can dominate; pipeline is not cash; “influenced” can double count; person-level conversions misrepresent accounts; a small sample cannot support precise channel rankings; optimization to shallow leads can degrade win rate.

## Mobile apps and subscriptions

### Decision chain

impression → store view/tap → install → first open → activation → retained user → payer/subscriber → net cohort value

### Required evidence

- platform, MMP, SKAdNetwork/current privacy framework, app analytics, billing, refunds, and cohort tables;
- attribution/re-attribution settings and privacy thresholds;
- install, activation, retention, purchase, subscription, trial, renewal, and cancellation definitions;
- net proceeds after store fees, incentives, support, fraud, and refunds;
- country/device/OS/version and creative/store-listing binding.
- app ID/ownership, supported optimization and retargeting events, MMP/SAN/privacy state, postback configuration, and event availability lag.

### Decision metrics

Use cost per activated/retained/paying user, D1/D7/D30 or business-relevant retention, trial-to-paid, cohort contribution/LTV on a named horizon, payback, and incremental lift where measurable.

### Common traps

Install efficiency can hide low retention; privacy frameworks create delayed/aggregated data; MMP and platform attribution can disagree by design; organic/store effects and re-downloads can inflate; early LTV models require uncertainty and backtesting.

## Marketplaces and retail media

Map paid media to marketplace sales, retail readiness, fees, inventory, Buy Box/availability, promotion, organic rank/halo, new-to-brand, and total contribution. Separate ad-attributed sales from total account sales. Use incrementality designs for halo or organic-effect claims.

### TikTok Shop and GMV Max

Map Business Center and primary-ad-account ownership, store, catalog/feed and event-source binding, product eligibility, identity/video/live room, campaign/session, order, refund/cancellation, and settled contribution. Keep Product GMV Max and LIVE GMV Max separate.

Current GMV Max reporting can include paid and organic orders while a campaign is active. Treat reported GMV and ROI as product-specific attributed totals, not automatic paid-media incrementality. Reconcile paid, organic, affiliate, total-channel, product/market, price/promotion, stock, refund, and contribution views.

Before a first-order, Max-delivery, or live-session boost, verify eligible product/video pool, campaign and shop state, current date/time zone, existing sessions, independent versus regular budget, ROI mode, target/cap, schedule, incremental downside, and read-back. A default percentage or session count from a public skill is not a safe universal control.

## Selecting the optimization event

Choose the deepest event that is timely, accurately measured, economically aligned, and sufficiently frequent for the current platform/account—not merely the deepest available event or the highest-volume proxy.

Document:

- relationship to the true business outcome;
- delay, volume, missingness, fraud/quality, and manipulation risk;
- historical predictive validity by cohort;
- cost of optimizing the proxy incorrectly;
- plan to send deeper outcomes or recalibrate.

If a shallow event stops predicting qualified outcomes, repair the signal before increasing spend.
