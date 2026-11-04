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

1. **Decision:** act, test, hold, monitor, or revert; summary, owner, deadline, confidence, and evidence rung (the causal ladder in references/measurement-and-experimentation.md, separate from source rank).
2. **Evidence:** claim-level truth labels, source, retrieval time, coverage, and limitations.
3. **Metrics:** name, value, unit, source, window, time zone, currency, attribution, conversion definition, count/denominator, and evidence label.
4. **Data quality:** pass/pass_with_limits/fail, binding state, reconciliation state, critical issues, and decision impact.
5. **Economics:** when required by the claim or exposure increase, acquisition unit, revenue basis, formulas, input sources, downside/base/upside scenarios, target, marginal implication, capacity, and switch point. Unknown margin alone does not block a sourced operational risk stop/rotation.
6. **Diagnosis:** observed funnel break, leading mechanism, alternatives, supporting/contradicting evidence, confounds, and discriminator.
7. **Plan:** exact action or test, exposure direction, sourced decision basis and counterevidence, owner, primary metric, guardrails, exposure/lag window, decision rule, monitoring, reversal, scoped unresolved gates, and actual threshold records. A qualitative decision does not need an invented threshold. Every exact threshold record includes rule/value, origin, source, derivation, scope, approval state, and approver; proposed governance cannot authorize a live money or delivery move without owner approval.
8. **Unknowns:** material unknown, consequence, cheapest evidence, and owner.
9. **Execution block:** required only for live execution; approval, before/after fields, recomputed deltas, structured financial exposure with currency/model/period/horizon/derivation and amount semantics, preflight, receipt, fresh read-back, rollback, partial failures, and execution state. Distinguish a nominal budget reference from a verified bound and actual spend.

When applicable, add the schema blocks `account_review`, `benchmark`, `funnel`, and `external_outcome_binding`. Add `capability_manifest` whenever tool semantics are decision-relevant; it is mandatory for `execute` and must contain the current resolved write tool plus an independent read tool. Use `capability_snapshot` for host/loading-mode provenance and discovery counts. Execute read-back declares the independent read tool and a normalized expected-state projection; `applied` or later requires a fresh observed projection that matches exactly. These blocks preserve current MCP/tool semantics, account coverage, descriptive peer context, stage definitions, and advertiser-owned outcome provenance without making every read-only packet carry irrelevant fields.

Validate a requested or execution-bound JSON form with assets/schemas/decision-packet.schema.json and scripts/validate_decision_packet.py. Do not duplicate a Markdown audit as JSON unless the user or workflow needs a machine-readable companion. If both exist, generate the summary from, or cross-check it against, the validated packet.

### Directional packet version 1.3

Use `schema_version: "1.3"` for new packets. Version 1.2 remains accepted under its legacy conservative rules; do not alter dated evidence to masquerade as a new packet. Keep `money_moving` for compatibility, and use these fields to express the actual decision:

- `decision.claim_type`: `operational`, `descriptive`, `profitability`, `superiority`, `inferiority`, or `causal`. Superiority/inferiority requires sourced `claim_sufficiency` with `method`, `result`, and `source_ids`; an operational pause does not assert either claim.
- `plan.exposure_direction`: `increase`, `reduce`, `rotate`, `continue`, or `none`. Reduce/rotate cannot contain hidden activation or budget increase. Shared-budget pause consequences belong in the rationale, not a savings promise.
- `plan.decision_basis`: `kind` (`qualitative_risk`, `economics`, `experiment`, or `diagnostic`), `rationale`, evidence `source_ids`, and `counterevidence`. `threshold_records` may be empty when no actual threshold is used.
- `plan.unresolved_gates`: records of `reason`, `scope`, `blocked_directions`, and `blocked_claims`. Attach only gates relevant to this scoped packet; split unrelated decisions rather than using a broad hold or a fabricated safety exception.
- `plan.continuation`: required for a material paid continuation decision, not a connection or status lookup. Include `since_previous_review`, `last_outcomes` (dates/spend by separate ledger, or explicit unknowns), `exposure_context`, `cost_of_waiting`, `cost_of_stopping`, `next_information`, `continuation_rationale`, `next_review`, `decision_trigger`, and `trigger_response`. Use the existing cadence; a met trigger needs an explicit fresh decision, not automatic cut or repeated WATCH.
- Execute exposure adds `amount_semantics`: `nominal_reference` or `verified_bound`. The legacy key `maximum_incremental_amount` is not a hard cash maximum when nominal; a verified bound needs `bound_evidence`. Budget × period alone does not verify a bound.

Business reconciliation describes outcomes, not validated target configuration. Do not claim stronger reconciliation to pass validation. Structural PASS verifies the packet contract and arithmetic, not the truth of its evidence, wisdom of KEEP/CUT, profit, or an applied live outcome. Use behavioral evaluations as an additional check on decision quality.

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

Keep the main report decision-dense. Put exhaustive entity matrices, field inventories, formulas, hashes, and visual-coverage logs in an evidence appendix. Recompute executive totals and decision-state counts from the final underlying rows, and include a coverage checksum: expected, observed, unique, missing, and duplicate rows. Repetition does not satisfy a missing decision, owner, binding, or source requirement.

For a platform account audit, also show product-family coverage: regular, automated/Smart+, shop or GMV, app, lead, search, reservation, and active automated-rule surfaces as applicable. Distinguish zero, empty, unavailable, unsupported, excluded, and unqueried states.

## Account diagnosis

Include:

- exact symptom, entity, issue time, objective, event, window, time zone, and lag state;
- configuration/status/automation and mix changes aligned to the symptom;
- native diagnostic or recommendation output with its scope and limitations;
- verified leading mechanism, at least two rivals, contradictory evidence, and cheapest discriminator;
- business consequence and money at risk with definition and uncertainty;
- immediate technical repair, controlled media intervention, or routed owner;
- decision state, threshold provenance, and execution authority.

Do not present a native agent answer, health score, benchmark quartile, or temporal coincidence as root-cause proof.

## Benchmark readout

State peer definition, advertiser/population, objective, grain, metric, direction, market, product/business model, automation/bid/event/attribution/window, lag, peer count, distinct values, missing/ineligible entities, method, and retrieval latency. Show empirical distribution and entity percentile as context. Keep business economics, causal evidence, and decision state separate; a percentile is not a kill/scale threshold.

## Funnel readout

Show stage definitions, identity/count semantics, source, deduplication, window, lag, counts, denominators, transition rates, comparable baseline, segment mix, leading leak hypothesis, alternatives, and scenario arithmetic. Do not use fixed severity bands or call event-count ratios user conversion rates without valid nesting.

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

For material paid KEEP/WATCH, add the compact continuation record above and actual delivery status. A decision hold does not pause delivery. No-change is a valid result when continuation is justified. Read-only monitoring can recommend changes; mutation depends on the actual explicit or standing execution authority.
