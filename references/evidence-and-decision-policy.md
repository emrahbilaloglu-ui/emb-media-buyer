# Evidence and decision policy

Use this policy for every conclusion that could move money, change delivery, or become a reusable learning.

## Truth labels

Label decision-relevant statements at the point of use.

- **verified_fact:** directly observed in an authoritative artifact, first-party system, current account read, or official source. Include source and retrieval time.
- **derived_metric:** arithmetic from named inputs. Include formula, units, and input provenance.
- **inference:** the best explanation supported by evidence but not directly observed. Include at least one rival explanation.
- **practitioner_heuristic:** a workflow or threshold proposed by a creator, operator, community, vendor, or open repository. It may seed a test; it cannot settle a decision.
- **assumption:** an input accepted for planning without present verification. Show the sensitivity to it.
- **unknown:** material information that is absent, inaccessible, incompatible, or not identifiable from the available design.

Do not present a model output as a verified fact. Name the model, training or calibration basis where known, input window, and uncertainty.

## Evidence hierarchy

Use the strongest source available for the claim.

1. Advertiser-owned financial and operational truth: settled orders, refunds, contribution, qualified pipeline, closed revenue, retained cohorts, capacity, stock.
2. First-party measurement and account state: raw event logs, analytics, MMP, CRM, commerce platform, ad-platform configuration and delivery reads.
3. Designed causal evidence: randomized experiments, holdouts, credible geo designs, calibrated causal models, with assumptions and diagnostics.
4. Current official platform documentation and release notes for platform behavior, eligibility, fields, or procedures.
5. Transparent academic or industry methods with inspectable assumptions and limitations.
6. Practitioner demonstrations, YouTube content, community posts, benchmarks, vendor case studies, and open-source agent workflows.

Higher rank does not mean infallible. A finance ledger can have delayed refunds; an experiment can be underpowered or contaminated; official documentation can lag a rollout. Record the specific limitation.

## Three ledgers that must not be merged

Maintain separate views of:

- **Attributed platform performance:** outcomes credited by a platform under a named attribution rule.
- **Business outcome truth:** advertiser-owned orders, contribution, pipeline, revenue, retention, or another agreed outcome.
- **Incremental evidence:** the estimated counterfactual effect of advertising from a credible design.

Use platform results to operate within a platform when appropriately qualified. Use business outcomes to judge economics. Use incremental evidence to claim causation. Agreement between ledgers raises confidence but does not make them identical.

## Comparability gate

Before ranking two rows, record whether they share:

- business outcome and conversion-event definition;
- objective, optimization goal, bid strategy, and budget structure;
- attribution setting and reporting freshness;
- overlapping calendar, purchase cycle, and promotion state;
- market, audience, placement, device, and new/returning mix;
- offer, destination, inventory/capacity, and measurement configuration;
- material delivery volume and concentration.

If a mismatch affects the conclusion, either normalize/design around it or label the comparison directional. Do not repair a structural confound with prose.

## Precision ceiling

The evidence determines the precision of the answer.

- Counts and descriptive arithmetic are permitted when inputs are verified.
- An observational association can generate hypotheses and scoped candidates; it cannot prove causality.
- Do not invent a probability, sample sufficiency, decisive date, fatigue point, or kill level from a snapshot.
- A rate without its count and denominator is incomplete.
- A recent outcome without its conversion lag and reporting revision state is incomplete.
- If multiple material gates remain open, use hold, monitor, or test. Do not issue a directional budget action merely because a platform KPI looks extreme.

## Threshold policy

Every actionable threshold must have one of four origins:

1. **Business-derived:** contribution, cash, capacity, payback, service-level, or risk appetite.
2. **Account-derived:** a documented distribution or response curve from comparable account history.
3. **Design-derived:** a preregistered power/sufficiency method and minimum detectable business effect.
4. **Runtime platform-derived:** current official eligibility, technical limit, or account-specific recommendation that has been independently verified.

Benchmarks and creator rules may be shown only as practitioner heuristics. Never silently use them as a default.

## Competing-hypothesis discipline

For a material anomaly, state:

- the observation;
- the leading mechanism;
- at least two plausible alternatives;
- evidence consistent and inconsistent with each;
- the cheapest reliable discriminator;
- what decision is safe before the discriminator arrives.

Common rivals include tracking changes, lag, mix shifts, budget/bid constraints, audience saturation, creative novelty, offer or price, destination behavior, stock/capacity, sales follow-up, calendar effects, auction conditions, and random variation.

## Decision state and confidence

Use act, test, hold, monitor, or revert. Confidence is high, medium, or low only after explaining:

- source quality and freshness;
- comparability and binding quality;
- sample and variance limitations;
- reconciliation state;
- causal rung;
- remaining unknowns.

Do not use high confidence for a causal claim supported only by observational platform rows. Do not state numerical confidence unless a named estimator produced it.

## What would change the conclusion

Close each material recommendation with the evidence or event that would reverse, strengthen, or invalidate it. This may be a finance reconciliation, clean event read, asset binding, complete lag window, CRM quality cohort, controlled test, geo diagnostic, or failed guardrail.

