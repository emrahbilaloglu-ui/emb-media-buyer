# Script usage

The scripts are read-only and use only the Python standard library. They do arithmetic and validation; they do not choose business inputs, set thresholds, call platforms, or mutate accounts.

## media_math.py

Run from the skill directory or by absolute path:

    python3 scripts/media_math.py COMMAND --input INPUT.json

Use a single hyphen as the input path to read JSON from stdin. Output is JSON. Invalid or economically impossible inputs return exit code 2.

All values must share the stated acquisition unit, currency, and revenue/contribution basis. Example numbers below demonstrate shape only; never use them as benchmarks.

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

Without planned_curve, the script labels linear spend as an assumption. Pace ratio is delivery versus curve, not an optimization instruction.

### marginal

Supply at least two observed spend and pre-ad business-contribution points on comparable definitions:

    {
      "currency": "USD",
      "observed_steps": [
        {"spend": 1000, "pre_ad_business_contribution": 1800},
        {"spend": 1500, "pre_ad_business_contribution": 2150}
      ]
    }

The output shows descriptive interval slopes and incremental post-ad contribution. It explicitly is not a causal response curve and must not be extrapolated.

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

The output reports approximate required event counts per arm and total; if daily per-arm events are supplied, it also reports approximate duration. With an event count instead of an effect, it returns the implied minimum detectable relative effect. This is a transparent planning baseline, not a complete experiment design. Unequal exposure, overdispersion, clustering, repeated looks, multiple comparisons, divergent delivery, contamination, conversion lag, and revenue/value outcomes need a richer method.

## validate_decision_packet.py

Validate a packet:

    python3 scripts/validate_decision_packet.py decision.json

Use --strict to fail on warnings as well as errors. The validator checks:

- core scope, evidence labels, metric qualifiers, data quality, diagnosis, plan, and unknowns;
- causal claims against evidence rung;
- competing hypotheses;
- economics/reconciliation for a money-moving act;
- complete experiment contract for test;
- exact approval, changes, preflight, read-back, rollback, and execution state for execute;
- rates without denominators and ambiguous qualifiers.

The human/tooling schema is assets/schemas/decision-packet.schema.json. Passing validation means the packet is structurally and semantically ready for review; it does not prove that external evidence is true or that a live change applied.
