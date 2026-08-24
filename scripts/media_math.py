#!/usr/bin/env python3
"""Deterministic paid-media economics, pacing, sufficiency, and marginal arithmetic.

Input is JSON from --input PATH or stdin. Output is JSON on stdout. The script
does not choose thresholds or make account changes; it exposes formulas and
assumptions so an agent can reason from advertiser-specific inputs.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Any, Iterable


class InputError(ValueError):
    """Raised for invalid or decision-ambiguous inputs."""


def _number(value: Any, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise InputError(f"{name} must be a finite number")
    if minimum is not None and result < minimum:
        raise InputError(f"{name} must be >= {minimum}")
    return result


def _sum_costs(value: Any, name: str) -> tuple[float, dict[str, float]]:
    if not isinstance(value, dict) or not value:
        raise InputError(f"{name} must be a non-empty object of named costs")
    clean: dict[str, float] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not key.strip():
            raise InputError(f"{name} keys must be non-empty strings")
        clean[key] = _number(raw, f"{name}.{key}", minimum=0)
    return sum(clean.values()), clean


def _ratio(numerator: float, denominator: float, name: str) -> float:
    if denominator == 0:
        raise InputError(f"{name} denominator must not be zero")
    return numerator / denominator


def commerce(payload: dict[str, Any]) -> dict[str, Any]:
    revenue = _number(payload.get("expected_net_revenue_per_unit"), "expected_net_revenue_per_unit", minimum=0)
    if revenue == 0:
        raise InputError("expected_net_revenue_per_unit must be > 0")
    costs_total, costs = _sum_costs(payload.get("variable_costs_per_unit"), "variable_costs_per_unit")
    desired = _number(payload.get("desired_post_ad_contribution_per_unit", 0), "desired_post_ad_contribution_per_unit", minimum=0)
    reserve = _number(payload.get("risk_reserve_per_unit", 0), "risk_reserve_per_unit", minimum=0)
    pre_ad = revenue - costs_total
    if pre_ad <= 0:
        raise InputError("pre-ad contribution must be > 0; paid acquisition has no positive break-even CPA on these inputs")
    target_cpa = pre_ad - desired - reserve
    if target_cpa <= 0:
        raise InputError("target CPA must be > 0 after desired contribution and risk reserve")

    result: dict[str, Any] = {
        "command": "commerce",
        "currency": payload.get("currency"),
        "acquisition_unit": payload.get("acquisition_unit", "order_or_customer_as_supplied"),
        "revenue_basis": payload.get("revenue_basis", "expected_net_revenue_per_unit"),
        "inputs": {
            "expected_net_revenue_per_unit": revenue,
            "variable_costs_per_unit": costs,
            "desired_post_ad_contribution_per_unit": desired,
            "risk_reserve_per_unit": reserve,
        },
        "derived": {
            "variable_costs_total_per_unit": costs_total,
            "pre_ad_contribution_per_unit": pre_ad,
            "contribution_margin_ratio": pre_ad / revenue,
            "break_even_cpa": pre_ad,
            "break_even_roas": revenue / pre_ad,
            "target_cpa": target_cpa,
            "target_roas": revenue / target_cpa,
        },
        "interpretation_limits": [
            "The acquisition unit and revenue basis must match the media decision.",
            "These are break-even and target arithmetic, not incremental-effect estimates.",
            "A scale decision still requires reconciled outcomes, marginal evidence, lag, and capacity checks.",
        ],
    }

    if "observed_cpa" in payload:
        observed = _number(payload["observed_cpa"], "observed_cpa", minimum=0)
        result["inputs"]["observed_cpa"] = observed
        result["derived"]["observed_post_ad_contribution_per_unit"] = pre_ad - observed
        result["derived"]["observed_cpa_headroom_to_target"] = target_cpa - observed
    if "marketing_spend" in payload or "advertiser_owned_revenue" in payload:
        if "marketing_spend" not in payload or "advertiser_owned_revenue" not in payload:
            raise InputError("marketing_spend and advertiser_owned_revenue must be supplied together")
        spend = _number(payload["marketing_spend"], "marketing_spend", minimum=0)
        owned_revenue = _number(payload["advertiser_owned_revenue"], "advertiser_owned_revenue", minimum=0)
        if spend == 0:
            raise InputError("marketing_spend must be > 0 when calculating MER")
        result["inputs"]["marketing_spend"] = spend
        result["inputs"]["advertiser_owned_revenue"] = owned_revenue
        result["derived"]["mer"] = owned_revenue / spend
    return result


def leadgen(payload: dict[str, Any]) -> dict[str, Any]:
    raw_stages = payload.get("stage_probabilities")
    stages: list[dict[str, float | str]] = []
    if raw_stages is None:
        raw_stages = [
            {"name": "qualified_given_lead", "probability": payload.get("p_qualified_given_lead")},
            {"name": "sale_given_qualified", "probability": payload.get("p_sale_given_qualified")},
        ]
    if not isinstance(raw_stages, list) or not raw_stages:
        raise InputError("stage_probabilities must be a non-empty array")
    for index, stage in enumerate(raw_stages):
        if not isinstance(stage, dict) or not isinstance(stage.get("name"), str):
            raise InputError(f"stage_probabilities[{index}].name must be a non-empty string")
        name = str(stage["name"]).strip()
        if not name:
            raise InputError(f"stage_probabilities[{index}].name must be a non-empty string")
        probability = _number(stage.get("probability"), f"stage_probabilities[{index}].probability", minimum=0)
        if probability > 1:
            raise InputError(f"stage_probabilities[{index}].probability must be <= 1")
        stages.append({"name": name, "probability": probability})
    contribution_sale = _number(payload.get("expected_contribution_per_won_sale"), "expected_contribution_per_won_sale", minimum=0)
    variable_cost = _number(payload.get("variable_sales_cost_per_lead", 0), "variable_sales_cost_per_lead", minimum=0)
    desired = _number(payload.get("desired_post_ad_contribution_per_lead", 0), "desired_post_ad_contribution_per_lead", minimum=0)
    reserve = _number(payload.get("risk_reserve_per_lead", 0), "risk_reserve_per_lead", minimum=0)

    expected_win_rate = math.prod(float(stage["probability"]) for stage in stages)
    pre_ad = expected_win_rate * contribution_sale - variable_cost
    if pre_ad <= 0:
        raise InputError("expected pre-ad contribution per lead must be > 0")
    target_cpl = pre_ad - desired - reserve
    if target_cpl <= 0:
        raise InputError("target CPL must be > 0 after desired contribution and risk reserve")

    return {
        "command": "leadgen",
        "currency": payload.get("currency"),
        "inputs": {
            "stage_probabilities": stages,
            "expected_contribution_per_won_sale": contribution_sale,
            "variable_sales_cost_per_lead": variable_cost,
            "desired_post_ad_contribution_per_lead": desired,
            "risk_reserve_per_lead": reserve,
        },
        "derived": {
            "expected_win_rate_per_lead": expected_win_rate,
            "expected_pre_ad_contribution_per_lead": pre_ad,
            "break_even_cpl": pre_ad,
            "target_cpl": target_cpl,
        },
        "interpretation_limits": [
            "Stage probabilities must come from comparable cohorts and include sales lag.",
            "Duplicate, spam, unreachable, no-show, cancellation, collection, and capacity effects must be represented in inputs or scenarios.",
            "The result is expected-value arithmetic, not a causal attribution of wins to media.",
        ],
    }


def cohort(payload: dict[str, Any]) -> dict[str, Any]:
    raw_periods = payload.get("periods")
    if not isinstance(raw_periods, list) or not raw_periods:
        raise InputError("periods must be a non-empty array")
    periods: list[dict[str, Any]] = []
    for index, item in enumerate(raw_periods):
        if not isinstance(item, dict) or not isinstance(item.get("period"), str) or not item.get("period", "").strip():
            raise InputError(f"periods[{index}].period must be a non-empty string")
        contribution = _number(item.get("gross_contribution_per_acquired_unit"), f"periods[{index}].gross_contribution_per_acquired_unit")
        periods.append({
            "period": item["period"].strip(),
            "gross_contribution_per_acquired_unit": contribution,
        })
    discount_rate = _number(payload.get("discount_rate_per_period", 0), "discount_rate_per_period")
    if discount_rate <= -1:
        raise InputError("discount_rate_per_period must be > -1")
    desired = _number(payload.get("desired_post_ad_contribution_per_unit", 0), "desired_post_ad_contribution_per_unit", minimum=0)
    reserve = _number(payload.get("risk_reserve_per_unit", 0), "risk_reserve_per_unit", minimum=0)

    cumulative_pv = 0.0
    discounted_periods: list[dict[str, Any]] = []
    for index, item in enumerate(periods):
        present_value = item["gross_contribution_per_acquired_unit"] / ((1 + discount_rate) ** index)
        cumulative_pv += present_value
        discounted_periods.append({
            **item,
            "discounted_contribution_per_acquired_unit": present_value,
            "cumulative_discounted_contribution_per_acquired_unit": cumulative_pv,
        })
    if cumulative_pv <= 0:
        raise InputError("discounted cohort contribution must be > 0")
    target_cac = cumulative_pv - desired - reserve
    if target_cac <= 0:
        raise InputError("target CAC must be > 0 after desired contribution and risk reserve")

    derived: dict[str, Any] = {
        "discounted_gross_margin_ltv": cumulative_pv,
        "break_even_cac": cumulative_pv,
        "target_cac": target_cac,
    }
    observed_cac = payload.get("observed_cac")
    if observed_cac is not None:
        observed_cac = _number(observed_cac, "observed_cac", minimum=0)
        derived["observed_cac"] = observed_cac
        derived["ltv_to_cac"] = None if observed_cac == 0 else cumulative_pv / observed_cac
        derived["discounted_post_ad_contribution_per_unit"] = cumulative_pv - observed_cac
        payback_period = None
        for item in discounted_periods:
            if item["cumulative_discounted_contribution_per_acquired_unit"] >= observed_cac:
                payback_period = item["period"]
                break
        derived["discounted_payback_period_first_reached"] = payback_period

    return {
        "command": "cohort",
        "currency": payload.get("currency"),
        "cohort_horizon": payload.get("cohort_horizon", periods[-1]["period"]),
        "inputs": {
            "periods": periods,
            "discount_rate_per_period": discount_rate,
            "desired_post_ad_contribution_per_unit": desired,
            "risk_reserve_per_unit": reserve,
        },
        "discounted_periods": discounted_periods,
        "derived": derived,
        "interpretation_limits": [
            "The cohort definition, horizon, retention, refunds, servicing costs, and contribution basis must match the acquisition decision.",
            "Predicted future periods require uncertainty and backtesting; this script does not create that uncertainty model.",
            "LTV arithmetic is not evidence that media caused the cohort outcomes.",
        ],
    }


def _parse_datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise InputError(f"{name} must be an ISO-8601 string with a timezone")
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InputError(f"{name} must be a valid ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputError(f"{name} must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def _validate_curve(raw: Any) -> list[tuple[float, float]]:
    if raw is None:
        return [(0.0, 0.0), (1.0, 1.0)]
    if not isinstance(raw, list) or len(raw) < 2:
        raise InputError("planned_curve must contain at least two points")
    points: list[tuple[float, float]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise InputError(f"planned_curve[{index}] must be an object")
        x = _number(item.get("elapsed_fraction"), f"planned_curve[{index}].elapsed_fraction", minimum=0)
        y = _number(item.get("cumulative_spend_fraction"), f"planned_curve[{index}].cumulative_spend_fraction", minimum=0)
        if x > 1 or y > 1:
            raise InputError("planned_curve fractions must be <= 1")
        points.append((x, y))
    if points[0] != (0.0, 0.0) or points[-1] != (1.0, 1.0):
        raise InputError("planned_curve must start at (0,0) and end at (1,1)")
    for previous, current in zip(points, points[1:]):
        if current[0] <= previous[0] or current[1] < previous[1]:
            raise InputError("planned_curve elapsed fractions must increase and cumulative spend must not decrease")
    return points


def _interpolate(points: Iterable[tuple[float, float]], x: float) -> float:
    ordered = list(points)
    if x <= 0:
        return ordered[0][1]
    if x >= 1:
        return ordered[-1][1]
    for left, right in zip(ordered, ordered[1:]):
        if left[0] <= x <= right[0]:
            width = right[0] - left[0]
            return left[1] + ((x - left[0]) / width) * (right[1] - left[1])
    raise InputError("planned_curve does not cover the elapsed fraction")


def pacing(payload: dict[str, Any]) -> dict[str, Any]:
    total_budget = _number(payload.get("total_flight_budget"), "total_flight_budget", minimum=0)
    if total_budget == 0:
        raise InputError("total_flight_budget must be > 0")
    actual_spend = _number(payload.get("actual_cumulative_spend"), "actual_cumulative_spend", minimum=0)
    start = _parse_datetime(payload.get("flight_start"), "flight_start")
    end = _parse_datetime(payload.get("flight_end"), "flight_end")
    as_of = _parse_datetime(payload.get("as_of"), "as_of")
    if end <= start:
        raise InputError("flight_end must be after flight_start")
    if not start <= as_of <= end:
        raise InputError("as_of must fall within the flight")
    total_seconds = (end - start).total_seconds()
    elapsed_fraction = (as_of - start).total_seconds() / total_seconds
    curve = _validate_curve(payload.get("planned_curve"))
    planned_fraction = _interpolate(curve, elapsed_fraction)
    expected_spend = total_budget * planned_fraction
    remaining_budget = total_budget - actual_spend
    remaining_days = (end - as_of).total_seconds() / 86400

    result: dict[str, Any] = {
        "command": "pacing",
        "currency": payload.get("currency"),
        "inputs": {
            "total_flight_budget": total_budget,
            "actual_cumulative_spend": actual_spend,
            "flight_start_utc": start.isoformat(),
            "flight_end_utc": end.isoformat(),
            "as_of_utc": as_of.isoformat(),
            "planned_curve": [
                {"elapsed_fraction": x, "cumulative_spend_fraction": y} for x, y in curve
            ],
        },
        "derived": {
            "elapsed_fraction": elapsed_fraction,
            "planned_cumulative_spend_fraction": planned_fraction,
            "expected_cumulative_spend": expected_spend,
            "pace_ratio": None if expected_spend == 0 else actual_spend / expected_spend,
            "spend_variance_to_curve": actual_spend - expected_spend,
            "remaining_budget": remaining_budget,
            "remaining_days": remaining_days,
            "required_remaining_average_daily_spend": None if remaining_days == 0 else remaining_budget / remaining_days,
        },
        "assumptions": [],
        "interpretation_limits": [
            "Pace describes delivery versus the supplied curve; it does not establish efficiency.",
            "Diagnose reporting, schedule, eligibility, bid/target, audience, asset, feed, and business constraints before changing delivery.",
            "Outcome decisions must account for conversion lag and advertiser-owned economics.",
        ],
    }
    if payload.get("planned_curve") is None:
        result["assumptions"].append("No planned curve supplied; linear cumulative spend was assumed.")
    if actual_spend > total_budget:
        result["warnings"] = ["Actual spend exceeds the supplied flight budget; verify budget definition, reporting, and overdelivery semantics."]
    return result


def _open_probability(value: Any, name: str, *, upper: float = 1.0) -> float:
    result = _number(value, name)
    if not 0 < result < upper:
        raise InputError(f"{name} must be > 0 and < {upper}")
    return result


def noise(payload: dict[str, Any]) -> dict[str, Any]:
    """Approximate one-count noise around a fixed expectation.

    This is deliberately a narrow Poisson/log-count baseline. It is not a
    two-arm test, an empirical account control limit, or a causal decision.
    """

    event_count = _number(payload.get("event_count"), "event_count", minimum=0)
    if event_count == 0:
        raise InputError("event_count must be > 0")
    confidence_level = _open_probability(payload.get("confidence_level", 0.95), "confidence_level")
    z_value = NormalDist().inv_cdf(0.5 + confidence_level / 2)
    relative_standard_error = 1 / math.sqrt(event_count)
    log_ratio_half_width = z_value * relative_standard_error
    upper_factor = math.exp(log_ratio_half_width)
    lower_factor = 1 / upper_factor

    result: dict[str, Any] = {
        "command": "noise",
        "inputs": {
            "event_count": event_count,
            "confidence_level": confidence_level,
        },
        "derived": {
            "z_value": z_value,
            "relative_standard_error": relative_standard_error,
            "approximate_ratio_band_lower": lower_factor,
            "approximate_ratio_band_upper": upper_factor,
            "approximate_downward_deviation": 1 - lower_factor,
            "approximate_upward_deviation": upper_factor - 1,
        },
        "method": "large-sample log-Poisson approximation for one observed event count versus a fixed expectation",
        "interpretation_limits": [
            "This is a screening baseline, not an account-specific anomaly threshold or causal test.",
            "If the baseline is estimated rather than fixed, include its uncertainty; a two-arm comparison needs both arms' variance.",
            "Overdispersion, seasonality, dependence, value variance, lag, model backfill, repeated looks, and measurement changes can make this band too narrow.",
        ],
    }

    if "observed_relative_change" in payload:
        relative_change = _number(payload["observed_relative_change"], "observed_relative_change")
        if relative_change < -1:
            raise InputError("observed_relative_change must be >= -1")
        observed_ratio = 1 + relative_change
        result["inputs"]["observed_relative_change"] = relative_change
        result["derived"]["observed_ratio"] = observed_ratio
        result["derived"]["outside_approximate_poisson_band"] = (
            observed_ratio < lower_factor or observed_ratio > upper_factor
        )
    return result


def power(payload: dict[str, Any]) -> dict[str, Any]:
    """Approximate equal-exposure, two-arm Poisson/log-rate sufficiency."""

    alpha = _open_probability(payload.get("alpha", 0.05), "alpha", upper=0.5)
    target_power = _number(payload.get("power", 0.8), "power")
    if not 0.5 < target_power < 1:
        raise InputError("power must be > 0.5 and < 1")
    sidedness_raw = _number(payload.get("sidedness", 2), "sidedness")
    if sidedness_raw not in (1, 2):
        raise InputError("sidedness must be 1 or 2")
    sidedness = int(sidedness_raw)

    has_effect = "minimum_detectable_relative_effect" in payload
    has_count = "expected_event_count_per_arm" in payload
    if has_effect == has_count:
        raise InputError(
            "supply exactly one of minimum_detectable_relative_effect or expected_event_count_per_arm"
        )

    z_alpha = NormalDist().inv_cdf(1 - alpha / sidedness)
    z_power = NormalDist().inv_cdf(target_power)
    coefficient = 2 * (z_alpha + z_power) ** 2
    inputs: dict[str, Any] = {
        "alpha": alpha,
        "power": target_power,
        "sidedness": sidedness,
    }

    if has_effect:
        minimum_effect = _number(
            payload["minimum_detectable_relative_effect"],
            "minimum_detectable_relative_effect",
            minimum=0,
        )
        if minimum_effect == 0:
            raise InputError("minimum_detectable_relative_effect must be > 0")
        expected_count = coefficient / math.log1p(minimum_effect) ** 2
        inputs["minimum_detectable_relative_effect"] = minimum_effect
    else:
        expected_count = _number(
            payload["expected_event_count_per_arm"],
            "expected_event_count_per_arm",
            minimum=0,
        )
        if expected_count == 0:
            raise InputError("expected_event_count_per_arm must be > 0")
        minimum_effect = math.exp(math.sqrt(coefficient / expected_count)) - 1
        inputs["expected_event_count_per_arm"] = expected_count

    rounded_per_arm = math.ceil(expected_count)
    derived: dict[str, Any] = {
        "z_alpha": z_alpha,
        "z_power": z_power,
        "minimum_detectable_relative_effect": minimum_effect,
        "expected_event_count_per_arm": expected_count,
        "required_event_count_per_arm_rounded_up": rounded_per_arm,
        "required_total_event_count_rounded_up": rounded_per_arm * 2,
    }

    if "expected_events_per_arm_per_day" in payload:
        daily_events = _number(
            payload["expected_events_per_arm_per_day"],
            "expected_events_per_arm_per_day",
            minimum=0,
        )
        if daily_events == 0:
            raise InputError("expected_events_per_arm_per_day must be > 0")
        inputs["expected_events_per_arm_per_day"] = daily_events
        required_days = expected_count / daily_events
        derived["approximate_required_days"] = required_days
        derived["approximate_required_days_rounded_up"] = math.ceil(required_days)

    return {
        "command": "power",
        "inputs": inputs,
        "derived": derived,
        "method": "normal approximation to an equal-exposure two-arm Poisson log-rate ratio",
        "interpretation_limits": [
            "This is a planning baseline for event counts, not a complete experiment design or a winner declaration.",
            "It assumes equal exposure, independent Poisson events, a fixed analysis, and the supplied alpha, power, and sidedness.",
            "Overdispersion, unequal exposure, clustering, repeated looks, multiple comparisons, delivery divergence, contamination, lag, and revenue/value outcomes require a richer design and usually more data.",
            "Use a minimum effect that is commercially meaningful; a detectable effect is not an expected or incremental effect.",
        ],
    }


def marginal(payload: dict[str, Any]) -> dict[str, Any]:
    raw_steps = payload.get("observed_steps")
    if not isinstance(raw_steps, list) or len(raw_steps) < 2:
        raise InputError("observed_steps must contain at least two spend/outcome points")
    steps: list[dict[str, float]] = []
    for index, item in enumerate(raw_steps):
        if not isinstance(item, dict):
            raise InputError(f"observed_steps[{index}] must be an object")
        spend = _number(item.get("spend"), f"observed_steps[{index}].spend", minimum=0)
        contribution = _number(item.get("pre_ad_business_contribution"), f"observed_steps[{index}].pre_ad_business_contribution", minimum=0)
        steps.append({"spend": spend, "pre_ad_business_contribution": contribution})
    steps.sort(key=lambda item: item["spend"])
    if len({step["spend"] for step in steps}) != len(steps):
        raise InputError("observed_steps spend values must be unique")

    intervals: list[dict[str, float]] = []
    for left, right in zip(steps, steps[1:]):
        delta_spend = right["spend"] - left["spend"]
        delta_contribution = right["pre_ad_business_contribution"] - left["pre_ad_business_contribution"]
        intervals.append({
            "from_spend": left["spend"],
            "to_spend": right["spend"],
            "incremental_spend": delta_spend,
            "incremental_pre_ad_business_contribution": delta_contribution,
            "marginal_contribution_return_before_ad_cost": delta_contribution / delta_spend,
            "incremental_post_ad_contribution": delta_contribution - delta_spend,
        })
    return {
        "command": "marginal",
        "currency": payload.get("currency"),
        "observed_steps": steps,
        "intervals": intervals,
        "interpretation_limits": [
            "These are descriptive slopes between supplied points, not a causal response curve.",
            "Comparable periods, demand, mix, tracking, lag, and business contribution definitions must be verified.",
            "Do not extrapolate beyond the observed spend range without an explicit model and uncertainty.",
        ],
    }


COMMANDS = {
    "cohort": cohort,
    "commerce": commerce,
    "leadgen": leadgen,
    "noise": noise,
    "pacing": pacing,
    "power": power,
    "marginal": marginal,
}


def _read_payload(path: str) -> dict[str, Any]:
    if path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise InputError("input JSON must be an object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--input", default="-", help="JSON file path, or - for stdin")
    args = parser.parse_args(argv)
    try:
        result = COMMANDS[args.command](_read_payload(args.input))
    except (InputError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
