# Output contracts

Use the smallest contract that makes the decision auditable. Lead with the answer. Keep metric qualifiers adjacent to the metric.

## Universal header

Every deliverable states:

- operating class: read_only, prepare, execute, or monitor;
- decision and scope;
- platform/account/entity identifiers;
- market, currency, account time zone, reporting and comparison windows;
- business outcome, optimization event, conversion definition, attribution, and lag;
- source retrieval times and data-quality/reconciliation state;
- live-mutation status.

## Decision packet

A decision packet contains:

1. **Decision:** act, test, hold, monitor, or revert; summary, owner, deadline, confidence, and evidence rung.
2. **Evidence:** claim-level truth labels, source, retrieval time, coverage, and limitations.
3. **Metrics:** name, value, unit, source, window, time zone, currency, attribution, conversion definition, count/denominator, and evidence label.
4. **Data quality:** pass/pass_with_limits/fail, binding state, reconciliation state, critical issues, and decision impact.
5. **Economics:** acquisition unit, revenue basis, formulas, input sources, downside/base/upside scenarios, target, marginal implication, capacity, and switch point.
6. **Diagnosis:** observed funnel break, leading mechanism, alternatives, supporting/contradicting evidence, confounds, and discriminator.
7. **Plan:** exact action or test, mechanism, owner, primary metric, guardrails, exposure/lag window, decision rule, monitoring, and reversal.
8. **Unknowns:** material unknown, consequence, cheapest evidence, and owner.
9. **Execution block:** required only for live execution; approval, before/after fields, financial exposure, preflight, receipt, fresh read-back, rollback, partial failures, and execution state.

Validate a JSON form with assets/schemas/decision-packet.schema.json and scripts/validate_decision_packet.py.

## Audit report

Use this order:

- executive outcome and what not to do;
- scope and evidence/data-quality rating;
- business economics and reconciliation;
- issue register ranked by business impact, confidence, reversibility, and evidence needed;
- funnel/system diagnosis with competing hypotheses;
- immediate repairs, controlled tests, and deferred questions;
- 30/60/90-day or user-specified roadmap with owners and success/reversal rules;
- unknowns and source appendix.

Do not turn every dashboard metric into an issue. Each issue must state business consequence and the evidence that supports it.

## Strategy and media plan

Include:

- business goal, acquisition unit, economics, constraints, and risk appetite;
- audience/demand/customer evidence and channel roles;
- campaign/portfolio architecture as a hypothesis, not platform dogma;
- budget scenarios and marginal allocation logic;
- creative concept coverage and production/testing system;
- offer/destination/feed/sales dependencies;
- instrumentation, attribution, experiments, incrementality, and reporting plan;
- launch gates, governance, owners, timing, and decision thresholds;
- forecast assumptions, uncertainty, and what would change the plan.

## Experiment plan

Include decision, falsifiable hypothesis/mechanism, causal rung, population/unit, assignment, arms, variable isolation, exclusions, primary metric, source and definition, practical effect, baseline/variance source, power method, guardrails, exposure and lag, stopping rule, analysis, contamination risks, action for each outcome, and learning-ledger scope.

If sample sufficiency is unknown, say so before launch and present the safest alternative design or proxy with its limitations.

## Creative testing brief

Include customer evidence, product/offer truths, approved claims, concept taxonomy, requested production-ready concepts, distinctness test, format/placement jobs, asset lineage/naming, platform/runtime export checks, hypothesis and primary/guardrail metrics, destination match, claims/rights/fidelity/accessibility QA, launch binding, and learning loop.

Keep blocked concepts outside the delivered production-ready count.

## Execution plan and report

Before execution show exact target IDs, field-level current → proposed values, financial exposure, approval, experiment/dependency impact, preflight, validation/dry run, mutation sequence, read-back, rollback, monitoring, and stop conditions.

After execution show accepted versus applied state, fresh live values, per-entity partial failures, timestamps, change IDs, exposure, next delivery/outcome read, and residual unknowns. Do not claim customer or commercial proof from a configuration read-back.

## Monitoring readout

Return only changed or decision-relevant state:

- current execution stage;
- technical/delivery anomalies;
- pace versus the selected curve;
- complete versus incomplete outcome window;
- business guardrails and reconciliation;
- decision trigger status;
- next scheduled read and owner.

No-change is a valid result. Do not optimize during monitoring unless separately authorized.

