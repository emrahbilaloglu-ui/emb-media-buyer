# Measurement and experimentation

Choose a measurement method that can answer the actual decision. Do not ask attribution to answer causality or ask a model for precision its inputs cannot support.

## Measurement layers

- **Instrumentation:** whether actions are captured, deduplicated, consented, valued, and joined correctly.
- **Attribution:** how observed outcomes are credited across touchpoints under a named model and window.
- **Experiments:** how outcomes differ from a randomized or credible counterfactual.
- **Marketing mix modeling:** how aggregate outcomes vary with media and non-media drivers under explicit model assumptions.
- **Business reconciliation:** whether measured outcomes align with advertiser-owned finance, CRM, commerce, or cohort truth.

These layers complement one another. No single layer is a universal source of truth.

## Attribution and identity

For any attribution view, record the eligible touchpoints, identity key, lookback window, click/view/engaged-view treatment, cross-device logic, modeled or probabilistic components, conversion-time versus interaction-time reporting, deduplication, and credit rule. Last-click, data-driven, multi-touch, platform self-attribution, MMP, analytics, and CRM sourcing estimate different things.

Do not average incompatible attribution outputs. Use them to understand path/credit sensitivity and operate their intended systems. Validate decisions against advertiser-owned outcomes and causal evidence. Post-view credit is especially sensitive to exposure selection and identity; it is not an incrementality estimate.

## Causal ladder

Use the least costly rung that can support the claim:

1. Descriptive association and funnel diagnostics: useful for triage and hypotheses.
2. Adjusted observational comparison or matched cohort: sensitive to unmeasured confounding.
3. Randomized platform A/B test: supports a scoped arm comparison; inspect delivery divergence and platform optimization within arms.
4. User-level or audience holdout/conversion lift: estimates incremental outcomes for eligible, measured populations.
5. Randomized geo experiment or credible matched/synthetic-control geo design: useful when user-level randomization is unavailable; inspect pre-fit, spillover, interference, market shocks, and power.
6. Calibrated MMM or causal time-series model: useful for portfolio and long-horizon allocation; depends on variation, controls, priors, transformations, and validation. Calibrate with experiments when possible.

Never call an observational match randomized. Never call attributed conversions incremental.

## Method selection

Match the method to the decision and practical minimum effect, unit of intervention, eligible population, outcome frequency, sales cycle, conversion lag, contamination risk, market count, historical length, spend variation, control quality, cost of withholding media, and risk of an inconclusive result.

Verify current platform eligibility, structure, and limits at runtime. Do not store remembered cell counts, conversion thresholds, or test durations as policy.

## Preregistration contract

Before launch, record:

- falsifiable question and mechanism;
- decision owner and action for win, loss, no-difference, and guardrail failure;
- treatment unit, assignment method, arms, exclusions, and contamination plan;
- single primary metric with source, exact definition, attribution, currency, and horizon;
- guardrails for quality, contribution, refunds, complaints, brand, capacity, and tracking;
- minimum practically meaningful effect;
- baseline and variance source;
- power/sufficiency method, assumptions, and owner;
- exposure and post-exposure lag window;
- stopping rule and no-peeking commitment;
- planned analysis, multiple-comparison treatment, and missing-data handling;
- variables held constant and known threats to validity.

If sufficiency has not been estimated from account-relevant data and a named method, mark it unknown. Do not fill the gap with a generic platform or creator benchmark.

## Integrity checks during and after the test

Verify:

- planned arms, dates, assignment, budgets, and exclusions actually ran;
- no unplanned edit changed the treatment or reset delivery;
- spend, impressions, audience, placement, device, and product mix per arm;
- outcome capture, lag, consent, deduplication, and business reconciliation;
- contamination, crossover, spillover, concurrent promotions, site incidents, or supply changes;
- the primary result with count/denominator and uncertainty before secondary metrics;
- all guardrails and the preregistered decision rule;
- the possibility of no detectable or decision-relevant difference.

Do not rescue a failed primary outcome with an unplanned slice. Label exploratory findings and require confirmation.

## Brand and upper-funnel measurement

When the objective is awareness, consideration, or demand creation, define the business decision before choosing reach, views, recall, consideration, search, or site metrics.

- For brand-lift surveys, verify sampling, randomized exposure/holdout, question and population, response/nonresponse, minimum effect, power, multiple questions/markets, confidence interval, and platform eligibility.
- Treat ad recall, awareness, favorability, consideration, and intent as distinct self-reported constructs—not sales.
- Treat branded search, direct/organic traffic, social mentions, and category queries as triangulation unless a credible counterfactual isolates the media effect.
- Deduplicated reach and on-target reach depend on identity and population estimates; state the model and coverage.
- Connect upper-funnel measures to later business outcomes only with a preregistered validation or calibrated model. Do not optimize brand media on CTR merely because it is immediate.

## Geo experimentation

For geo tests, document market eligibility, exclusions, treatment mapping, pre-period, test period, spend shock, outcome source, lag, covariates, and method. Inspect:

- pre-period fit and stability;
- market similarity and interference/spillover;
- outliers, national shocks, and local events;
- treatment compliance and cross-border media leakage;
- confidence or credible intervals and whether they cross the business decision threshold;
- sensitivity to market selection and modeling choices.

Incremental ROAS equals estimated incremental outcome value divided by incremental spend only when both are on aligned definitions. Report the interval and material assumptions, not just a point estimate.

## MMM

MMM is a model, not a neutral readout. Record:

- outcome and revenue basis;
- media variables, prices/exposures/spend, and granularity;
- seasonality, trend, promotions, price, distribution, macro, competitor, weather, and other controls;
- adstock, saturation, interaction, prior, and regularization choices;
- identifiability and collinearity diagnostics;
- holdout/backtest and posterior predictive validation;
- calibration experiments and their transport assumptions;
- response curves, marginal returns, uncertainty, and extrapolation range.

Do not optimize on point estimates outside the historically observed spend range. Paid search requires special care because demand drives both searches and sales; experiment-based bias correction or strong controls may be needed.

Useful open implementations include Google Meridian, Meta Robyn, and PyMC-Marketing. Their presence does not make a model credible; the data, design, diagnostics, and decision fit do.

## Triangulation

When attribution, experiment, MMM, and business outcomes disagree:

1. align definitions, windows, markets, currencies, and lag;
2. inspect data quality and scope;
3. compare the estimands: credited conversions, incremental effect, or total portfolio response;
4. assess model/design assumptions and uncertainty;
5. avoid averaging incompatible numbers;
6. state which source is decision-primary and why;
7. design the cheapest evidence that would resolve the disagreement.

## Learning ledger

A reusable learning records question, hypothesis, design rung, scope, arms, immutable asset/entity lineage, delivery, primary outcome, denominators, guardrails, confounds, uncertainty, applicability, and supersession links.

An observational result is an observation. An incomplete test is an incomplete learning. Append a durable rule only with explicit user approval and in the user’s chosen project location, never inside this skill.
