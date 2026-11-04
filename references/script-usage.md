# Script usage

The scripts are read-only and use only the Python standard library. They do arithmetic and validation; they do not choose objectives or business inputs, construct peer groups, classify severity, set thresholds, infer causes, call platforms, or mutate accounts.

## media_math.py

Run from the skill directory or by absolute path:

    python3 scripts/media_math.py COMMAND --input INPUT.json

Use a single hyphen as the input path to read JSON from stdin. Output is JSON. Invalid or economically impossible inputs return exit code 2.

All values must share the stated acquisition unit, currency, and revenue/contribution basis. Satisfy each command's semantic preconditions before calculating; a warning cannot repair an ineligible input. Example numbers below demonstrate shape only; never use them as benchmarks.

### commerce

Input fields:

- currency and acquisition_unit;
- expected_net_revenue_per_unit;
- variable_costs_per_unit as named nonnegative amounts;
- desired_post_ad_contribution_per_unit and risk_reserve_per_unit, defaulting to zero;
- optional observed_cpa;
- optional marketing_spend plus advertiser_owned_revenue for MER.

Example:

    {
      "currency": "USD",
      "acquisition_unit": "new_customer",
      "revenue_basis": "settled_net_revenue",
      "expected_net_revenue_per_unit": 100,
      "variable_costs_per_unit": {
        "cogs": 40,
        "fulfillment": 10,
        "payment_fees": 4,
        "expected_returns": 6
      },
      "desired_post_ad_contribution_per_unit": 10,
      "risk_reserve_per_unit": 5,
      "observed_cpa": 20
    }

The output includes pre-ad contribution, contribution-margin ratio, break-even CPA/ROAS, target CPA/ROAS, and observed headroom. It does not establish incrementality or marginal scalability.

### leadgen

Prefer an explicit stage chain:

    {
      "currency": "USD",
      "stage_probabilities": [
        {"name": "valid", "probability": 0.80},
        {"name": "qualified", "probability": 0.50},
        {"name": "show", "probability": 0.60},
        {"name": "win", "probability": 0.20}
      ],
      "expected_contribution_per_won_sale": 2000,
      "variable_sales_cost_per_lead": 10,
      "desired_post_ad_contribution_per_lead": 10,
      "risk_reserve_per_lead": 5
    }

The shortcut fields p_qualified_given_lead and p_sale_given_qualified are also accepted. Probabilities must come from comparable, lag-complete cohorts and include quality/fraud/capacity effects where relevant.

### cohort

Use for SaaS, apps, subscriptions, or repeat-purchase cohorts:

    {
      "currency": "USD",
      "cohort_horizon": "M12",
      "periods": [
        {"period": "M0", "gross_contribution_per_acquired_unit": 30},
        {"period": "M1", "gross_contribution_per_acquired_unit": 20},
        {"period": "M2", "gross_contribution_per_acquired_unit": 15}
      ],
      "discount_rate_per_period": 0.01,
      "desired_post_ad_contribution_per_unit": 10,
      "risk_reserve_per_unit": 5,
      "observed_cac": 40
    }

The output includes discounted gross-margin LTV, break-even/target CAC, optional LTV/CAC, post-ad contribution, and the first supplied period where discounted payback is reached. Predicted periods still need uncertainty and backtesting.

### pacing

Input datetimes must include time-zone offsets. Supply an approved cumulative curve when the flight is not linear.

    {
      "currency": "USD",
      "total_flight_budget": 10000,
      "actual_cumulative_spend": 4200,
      "flight_start": "2026-08-01T00:00:00+03:00",
      "flight_end": "2026-08-11T00:00:00+03:00",
      "as_of": "2026-08-06T00:00:00+03:00",
      "planned_curve": [
        {"elapsed_fraction": 0, "cumulative_spend_fraction": 0},
        {"elapsed_fraction": 0.5, "cumulative_spend_fraction": 0.4},
        {"elapsed_fraction": 1, "cumulative_spend_fraction": 1}
      ]
    }

Without `planned_curve`, the script returns schedule and remaining-budget facts but does not emit expected-to-curve spend, pace ratio, or variance; it states that no approved curve is available. A supplied curve must be the approved plan. Pace ratio is delivery versus that curve, not an optimization instruction.

### marginal

Supply at least two observed spend and pre-ad business-contribution points on comparable definitions:

    {
      "currency": "USD",
      "outcome_basis": "advertiser_owned_pre_ad_business_contribution",
      "business_contribution_source": "settled order and variable-cost ledger",
      "comparability_confirmed": true,
      "comparability_evidence": "same market, offer, measurement definition, and completed calendar design",
      "lag_complete": true,
      "lag_basis": "orders settled through the approved conversion and refund lag",
      "observed_steps": [
        {"spend": 1000, "pre_ad_business_contribution": 1800},
        {"spend": 1500, "pre_ad_business_contribution": 2150}
      ]
    }

The command rejects platform-attributed revenue, unconfirmed comparability, incomplete lag, or an unnamed business-contribution source. The output shows descriptive interval slopes and incremental post-ad contribution. It explicitly is not a causal response curve and must not be extrapolated.

### noise

Use this as a first-pass count-noise screen against a fixed expectation:

    {
      "event_count": 100,
      "confidence_level": 0.95,
      "observed_relative_change": 0.30
    }

The output reports the Poisson relative standard error `1/sqrt(C)` and an approximate multiplicative ratio band `exp(±z/sqrt(C))`. `observed_relative_change` is optional and only checks whether its ratio sits outside that approximate band. This is not an account alarm, a two-arm test, or causal evidence. Add baseline uncertainty, overdispersion, dependence, seasonality, lag/backfill, repeated looks, and measurement changes as the design requires.

### power

Use this to plan or invert an equal-exposure, two-arm Poisson/log-rate event-count baseline. Supply exactly one of `minimum_detectable_relative_effect` or `expected_event_count_per_arm`:

    {
      "minimum_detectable_relative_effect": 0.20,
      "alpha": 0.05,
      "power": 0.80,
      "sidedness": 2,
      "expected_events_per_arm_per_day": 5
    }

The output reports approximate required event counts per arm and total; if daily per-arm events are supplied, it also reports approximate duration. With an event count instead of an effect, it returns the implied minimum detectable relative effect. In inverse mode, `expected_event_count_per_arm` must be the count expected in **each** arm, never the pooled total. Set `event_count_basis` to `per_arm_expected_count` and provide both equal arm expectations as `arm_expected_event_counts.arm_a` and `.arm_b`; the helper rejects missing or unequal-arm evidence and any supplied pooled total that disagrees with those arm expectations. This is a transparent planning baseline, not a complete experiment design. Unequal exposure, overdispersion, clustering, repeated looks, multiple comparisons, divergent delivery, contamination, conversion lag, and revenue/value outcomes need a richer method.

Inverse example:

    {
      "expected_event_count_per_arm": 66,
      "event_count_basis": "per_arm_expected_count",
      "arm_expected_event_counts": {"arm_a": 66, "arm_b": 66},
      "alpha": 0.05,
      "power": 0.80,
      "sidedness": 2
    }

## account_review.py

Run from the skill directory or by absolute path:

    python3 scripts/account_review.py COMMAND --input INPUT.json

Commands are `benchmark`, `funnel`, and `review`. A single hyphen reads JSON from stdin. Output is JSON. Invalid definitions, open comparability gates, incomplete lag contracts, duplicate identifiers, or structurally impossible inputs return exit code 2.

### benchmark

Use for descriptive within-advertiser empirical quantiles after the peer group is proven comparable:

    {
      "metric": {
        "name": "CPA",
        "unit": "USD_per_purchase",
        "direction": "lower_is_better",
        "value_mode": "ratio",
        "multiplier": 1
      },
      "peer_group": {
        "advertiser_id": "adv_example",
        "objective": "WEB_CONVERSIONS",
        "grain": "campaign",
        "market": "US",
        "automation_mode": "regular",
        "bid_strategy": "maximum_delivery",
        "optimization_event": "PURCHASE",
        "attribution": "account setting snapshot",
        "window": "2026-08-01/2026-08-31",
        "timezone": "Europe/Istanbul",
        "metric_definition": "spend / attributed purchase count",
        "source": "TikTok integrated report snapshot",
        "report_latency": "retrieved after complete reporting lag",
        "eligibility_basis": "all campaigns with required metric inputs and complete delivery window",
        "expected_entity_count": 3,
        "missing_or_ineligible_entities": [],
        "comparability_confirmed": true,
        "comparability_evidence": "same advertiser, objective, grain, event, attribution and complete window",
        "lag_state": "complete",
        "lag_basis": "all campaigns observed through the selected conversion lag"
      },
      "entities": [
        {"id": "campaign_a", "numerator": 245, "denominator": 10},
        {"id": "campaign_b", "numerator": 312, "denominator": 10},
        {"id": "campaign_c", "numerator": 281, "denominator": 10}
      ]
    }

Use `value_mode=ratio` to calculate each entity from numerator / denominator × multiplier, or `value_mode=direct` for a genuinely direct metric supplied as `value`. The output contains R-7 linear P25/P50/P75 values and midrank raw/performance percentiles. A higher performance percentile means better only under the supplied direction. It emits no top/bottom label and no action. Peer selection, missing entities, eligibility, sample resolution, business economics, and causal interpretation remain outside the calculation.

### funnel

Use for stage counts, rates, and an optional comparable baseline:

    {
      "context": {
        "funnel_name": "settled commerce",
        "source": "advertiser analytics and order ledger",
        "window": "2026-08-24/2026-08-31",
        "timezone": "Europe/Istanbul",
        "identity_unit": "unique session progressing to unique settled order",
        "deduplication_state": "verified at each stage",
        "count_semantics": "unique_entities",
        "stage_chain_expected_nonincreasing": true,
        "lag_state": "complete",
        "lag_basis": "orders settled through the refund lag"
      },
      "stages": [
        {"name": "session", "count": 1000},
        {"name": "checkout", "count": 100},
        {"name": "settled_order", "count": 40}
      ],
      "comparison": {
        "window": "2026-08-17/2026-08-24",
        "comparability_confirmed": true,
        "comparability_evidence": "same source, market, offer and complete seven-day window",
        "lag_state": "complete",
        "lag_basis": "same refund lag",
        "stages": [
          {"name": "session", "count": 800},
          {"name": "checkout", "count": 80},
          {"name": "settled_order", "count": 24}
        ]
      }
    }

Set `count_semantics` to `events` or `other` when rows are not unique nested people/orders. Set `stage_chain_expected_nonincreasing` to false when later event counts can exceed earlier counts; then do not describe the ratios as population conversion rates. The script deliberately does not assign critical/moderate labels, diagnose a cause, or promise impact.

### review

Use for objective-aware current-versus-prior ratio aggregation and multi-period context. The caller selects the correct metric and supplies its numerator and denominator. For CPA use spend / conversions with multiplier 1; for CTR use clicks / impressions with multiplier 100 if the desired unit is percent; for CPM use spend / impressions with multiplier 1000.

    {
      "metric": {
        "name": "CPA",
        "unit": "USD_per_purchase",
        "direction": "lower_is_better",
        "multiplier": 1
      },
      "scope": {
        "advertiser_id": "adv_example",
        "objective": "WEB_CONVERSIONS",
        "business_outcome": "settled new-customer purchase",
        "grain": "account",
        "timezone": "Europe/Istanbul",
        "source": "TikTok report snapshot",
        "metric_definition": "total spend / total attributed purchases",
        "report_latency": "retrieved after the selected conversion lag",
        "comparability_confirmed": true,
        "comparability_evidence": "complete equivalent weeks with unchanged definitions",
        "lag_state": "complete",
        "lag_basis": "both weeks observed through the selected conversion lag"
      },
      "periods": [
        {"label": "W1", "start": "2026-08-03T00:00:00+03:00", "end": "2026-08-10T00:00:00+03:00", "numerator": 600, "denominator": 6},
        {"label": "W2", "start": "2026-08-10T00:00:00+03:00", "end": "2026-08-17T00:00:00+03:00", "numerator": 700, "denominator": 7},
        {"label": "W3", "start": "2026-08-17T00:00:00+03:00", "end": "2026-08-24T00:00:00+03:00", "numerator": 800, "denominator": 8},
        {"label": "W4", "start": "2026-08-24T00:00:00+03:00", "end": "2026-08-31T00:00:00+03:00", "numerator": 900, "denominator": 10}
      ]
    }

Optional `current_entities` and `prior_entities` arrays use `id`, optional `name`, `numerator`, and `denominator`. The output describes entity numerator/denominator movement and reconciles their sums to the period totals. It does not call entity movement a causal contribution to a ratio change. The multi-period slope is descriptive and carries no persistence, significance, or materiality claim.

## validate_decision_packet.py

Validate a packet:

    python3 scripts/validate_decision_packet.py decision.json

Use --strict to fail on warnings as well as errors. The validator checks:

- core scope, evidence labels, metric qualifiers, data quality, diagnosis, plan, and unknowns;
- causal claims against evidence rung;
- competing hypotheses;
- version 1.3 exposure direction, claim type, sourced qualitative/economic decision basis, scoped gates, and conditional paid-continuation contract; version 1.2 retains its legacy rules;
- economics/reconciliation for expansion/profit claims, while ordinary verified operational stop/rotation need not fabricate economics, reconciliation, thresholds, or safety incidents;
- threshold origin, source/derivation, scope, approval state, and owner approval for proposed-governance money moves;
- complete experiment contract for test;
- a current capability manifest for execute, including resolved write and independent read tools; mixed dispatchers and unknown mutability are rejected;
- exact arithmetic for numeric current/proposed deltas, null deltas for state changes, structured currency/model/period/horizon exposure that reproduces for budget and activation changes, nominal-reference versus verified-bound semantics, and an independent read-back tool with expected/observed state matching;
- rejection of any execution block on read-only, prepare, or monitor packets;
- exact approval, changes, preflight, read-back, rollback, and execution state for execute;
- rates without denominators and ambiguous qualifiers.

The human/tooling schema is assets/schemas/decision-packet.schema.json. Passing validation means the packet is structurally and semantically ready for review; it does not prove that external evidence is true or that a live change applied.
