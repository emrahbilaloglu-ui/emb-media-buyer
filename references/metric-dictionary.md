# Metric dictionary and interpretation

Use exact source definitions. The same label can mean different things across platforms, objectives, formats, attribution models, and APIs.

## Qualifier contract

Every decision-critical metric carries source, account/entity grain, numerator, denominator, unit, currency, time zone, window, attribution, conversion definition, click/view treatment, freshness/lag, filters, and evidence label. Show underlying counts for rates.

## Delivery and auction

- **Spend:** platform-billed or reported media cost. State whether fees, taxes, credits, agency, data, production, and verification costs are included.
- **Impressions:** served opportunities under the platform definition; not necessarily viewable or human.
- **Reach:** estimated unique people/accounts/devices/households under a platform identity model; definitions are not portable.
- **Frequency:** impressions divided by modeled reach for the same scope. Diagnostic, not a fatigue threshold.
- **CPM:** spend / impressions × 1,000. Cheap CPM does not establish quality, viewability, safety, or contribution.
- **Impression share/lost share:** platform-specific estimate of eligible opportunity and loss reason; verify exact network and definition.
- **Pacing:** actual cumulative spend relative to an approved cumulative curve. It says nothing about outcome quality by itself.

## Attention and traffic

- **CTR:** clicks / impressions. Specify all clicks, link/outbound clicks, unique clicks, or another definition.
- **CPC:** spend / the named click count.
- **Landing-page-view rate:** verified landing views / outbound clicks; sensitive to page speed, redirects, consent, and accidental clicks.
- **Video view/hold/completion:** verify view duration, autoplay, audibility, denominator, and format. Compare retention only across compatible durations and definitions.
- **Engagement:** platform-specific interactions; not commercial intent unless validated downstream.

## Conversion and value

- **CVR:** named conversions / named denominator. State whether denominator is impressions, clicks, landings, sessions, leads, or users.
- **CPA/CPL/CAC:** spend / named acquired units. Platform CPA, qualified-lead cost, and finance CAC are different metrics.
- **ROAS:** named conversion value / spend. State platform-attributed versus advertiser-owned, gross/net value, attribution, and refund treatment.
- **MER/blended efficiency:** advertiser-owned total revenue / total marketing spend on aligned scope. Descriptive portfolio efficiency, not causal return.
- **AOV:** named revenue / orders. State gross/net and cancellation/refund treatment.
- **Contribution after ads:** pre-ad contribution attributable to the scoped business outcomes − media and included variable acquisition costs. Do not call gross margin or platform value profit.
- **LTV/CAC:** defined cohort gross-margin value / acquisition cost. State cohort, horizon, churn/retention method, discounting, servicing costs, and prediction/backtest uncertainty.
- **Payback:** time for cumulative cohort contribution to recover CAC. State cash versus recognized contribution.

## Lead and pipeline

- **Valid/contactable rate:** valid reachable leads / submitted leads.
- **Qualification/show/opportunity/win rate:** each named stage / preceding or original cohort denominator; state which.
- **Cost per qualified lead/opportunity/win:** spend / same-source cohort outcomes after appropriate lag.
- **Pipeline:** open or probability-weighted opportunity value; state gross/net, stage method, duplicates, and age. Pipeline is not revenue.
- **Sourced/influenced revenue:** organization-specific attribution; publish the rule and avoid double counting.

## App and subscription

- **CPI:** spend / installs under the named attribution system.
- **Activation/retention rate:** activated or retained users / defined install or cohort base at a named horizon.
- **Trial-to-paid/renewal/churn:** define cohort, eligible denominator, timing, grace/refund status, and revenue basis.
- **Cohort ROAS/value:** net cohort value on a named horizon / spend; predictions require uncertainty and backtesting.

## Incrementality and experiments

- **Lift:** treatment outcome minus estimated counterfactual, absolute or relative. State design, population, period, estimator, interval, and assumptions.
- **Incremental outcome:** estimated outcomes caused by treatment under the design; not platform-attributed conversions.
- **iROAS:** estimated incremental outcome value / incremental spend on aligned definitions. Always show uncertainty and business threshold.
- **Minimum detectable effect:** the effect a design is powered to detect under named baseline, variance, sample, alpha/power or Bayesian decision assumptions. It is not the expected effect.

## Portfolio/model metrics

- **Average return:** total outcome / total spend for observed mix.
- **Marginal return:** change in outcome for a change in spend. Requires a credible response estimate; a descriptive slope is not automatically causal.
- **Response curve:** estimated spend-to-outcome relationship with saturation/uncertainty and observed range.
- **Model fit/validation:** use method-appropriate diagnostics, holdout/backtest, residuals/posterior predictive checks, calibration, sensitivity, and uncertainty. Fit alone does not establish causal validity.

## Benchmark policy

Benchmarks must match market, category, objective, placement, format, outcome, attribution, season, spend scale, and data source to be more than context. Show the distribution and sample, not only the mean. A benchmark never overrides the advertiser’s economics or clean account history.

