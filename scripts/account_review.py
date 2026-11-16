#!/usr/bin/env python3
"""Deterministic benchmark, funnel, and weekly-review arithmetic.

The script does not select objectives, invent peer groups, classify severity,
infer causes, recommend media changes, or call advertising platforms. Callers
must supply qualified definitions and comparability evidence.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


class InputError(ValueError):
    """Raised when the supplied arithmetic contract is invalid or ambiguous."""


def _number(value: Any, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise InputError(f"{name} must be a finite number")
    if minimum is not None and result < minimum:
        raise InputError(f"{name} must be >= {minimum}")
    return result


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{name} must be a non-empty string")
    return value.strip()


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{name} must be an object")
    return value


def _list(value: Any, name: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise InputError(f"{name} must be an array with at least {minimum} item(s)")
    return value


def _parse_datetime(value: Any, name: str) -> datetime:
    raw = _string(value, name).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise InputError(f"{name} must be a valid ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputError(f"{name} must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def _lag_contract(container: dict[str, Any], prefix: str) -> dict[str, str]:
    state = container.get("lag_state")
    if state not in {"complete", "not_applicable"}:
        raise InputError(f"{prefix}.lag_state must be complete or not_applicable")
    basis = _string(container.get("lag_basis"), f"{prefix}.lag_basis")
    return {"lag_state": state, "lag_basis": basis}


def _comparability_contract(container: dict[str, Any], prefix: str) -> str:
    if container.get("comparability_confirmed") is not True:
        raise InputError(f"{prefix}.comparability_confirmed must be true")
    return _string(
        container.get("comparability_evidence"),
        f"{prefix}.comparability_evidence",
    )


def _metric_contract(payload: dict[str, Any]) -> dict[str, Any]:
    metric = _object(payload.get("metric"), "metric")
    name = _string(metric.get("name"), "metric.name")
    unit = _string(metric.get("unit"), "metric.unit")
    direction = metric.get("direction")
    if direction not in {"higher_is_better", "lower_is_better"}:
        raise InputError(
            "metric.direction must be higher_is_better or lower_is_better"
        )
    return {"name": name, "unit": unit, "direction": direction}


def _quantile(sorted_values: list[float], probability: float) -> float:
    """R-7 / NumPy-linear empirical quantile."""

    if not sorted_values:
        raise InputError("cannot calculate a quantile from an empty array")
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] + fraction * (
        sorted_values[upper] - sorted_values[lower]
    )


def benchmark(payload: dict[str, Any]) -> dict[str, Any]:
    metric = _metric_contract(payload)
    metric_raw = _object(payload.get("metric"), "metric")
    value_mode = metric_raw.get("value_mode")
    if value_mode not in {"direct", "ratio"}:
        raise InputError("metric.value_mode must be direct or ratio")
    multiplier = _number(metric_raw.get("multiplier", 1), "metric.multiplier", minimum=0)
    if multiplier == 0:
        raise InputError("metric.multiplier must be > 0")
    metric["value_mode"] = value_mode
    metric["multiplier"] = multiplier
    peer_group = _object(payload.get("peer_group"), "peer_group")
    required_strings = [
        "advertiser_id",
        "objective",
        "grain",
        "market",
        "automation_mode",
        "bid_strategy",
        "optimization_event",
        "attribution",
        "window",
        "timezone",
        "metric_definition",
        "source",
        "report_latency",
        "eligibility_basis",
    ]
    clean_group = {
        field: _string(peer_group.get(field), f"peer_group.{field}")
        for field in required_strings
    }
    clean_group["comparability_confirmed"] = True
    clean_group["comparability_evidence"] = _comparability_contract(
        peer_group, "peer_group"
    )
    clean_group.update(_lag_contract(peer_group, "peer_group"))

    expected_raw = peer_group.get("expected_entity_count")
    if isinstance(expected_raw, bool) or not isinstance(expected_raw, int):
        raise InputError("peer_group.expected_entity_count must be an integer")
    if expected_raw < 2:
        raise InputError("peer_group.expected_entity_count must be >= 2")
    missing_raw = _list(
        peer_group.get("missing_or_ineligible_entities"),
        "peer_group.missing_or_ineligible_entities",
    )
    missing_entities = [
        _string(item, f"peer_group.missing_or_ineligible_entities[{index}]")
        for index, item in enumerate(missing_raw)
    ]
    if len(set(missing_entities)) != len(missing_entities):
        raise InputError("peer_group.missing_or_ineligible_entities must be unique")
    clean_group["expected_entity_count"] = expected_raw
    clean_group["missing_or_ineligible_entities"] = missing_entities

    raw_entities = _list(payload.get("entities"), "entities", minimum=2)
    entities: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_entities):
        item = _object(raw, f"entities[{index}]")
        entity_id = _string(item.get("id"), f"entities[{index}].id")
        if entity_id in seen:
            raise InputError(f"entities[{index}].id duplicates {entity_id}")
        seen.add(entity_id)
        clean_item: dict[str, Any] = {"id": entity_id, "name": item.get("name")}
        if value_mode == "direct":
            clean_item["value"] = _number(
                item.get("value"), f"entities[{index}].value"
            ) * multiplier
        else:
            numerator = _number(
                item.get("numerator"), f"entities[{index}].numerator", minimum=0
            )
            denominator = _number(
                item.get("denominator"),
                f"entities[{index}].denominator",
                minimum=0,
            )
            if denominator == 0:
                raise InputError(f"entities[{index}].denominator must be > 0")
            clean_item.update(
                {
                    "numerator": numerator,
                    "denominator": denominator,
                    "value": numerator / denominator * multiplier,
                }
            )
        entities.append(clean_item)

    if expected_raw != len(entities) + len(missing_entities):
        raise InputError(
            "peer_group.expected_entity_count must equal eligible entities plus missing_or_ineligible_entities"
        )
    if set(missing_entities) & seen:
        raise InputError(
            "missing_or_ineligible_entities must not duplicate an eligible entity id"
        )

    sorted_values = sorted(item["value"] for item in entities)
    enriched: list[dict[str, Any]] = []
    count = len(sorted_values)
    for item in entities:
        value = item["value"]
        below = sum(candidate < value for candidate in sorted_values)
        above = sum(candidate > value for candidate in sorted_values)
        equal = count - below - above
        raw_percentile = 100 * (below + 0.5 * equal) / count
        if metric["direction"] == "higher_is_better":
            performance_percentile = raw_percentile
        else:
            performance_percentile = 100 * (above + 0.5 * equal) / count
        enriched.append(
            {
                **item,
                "raw_value_percentile_midrank": raw_percentile,
                "performance_percentile_midrank": performance_percentile,
                "tie_count": equal,
            }
        )

    return {
        "command": "benchmark",
        "metric": metric,
        "peer_group": clean_group,
        "distribution": {
            "method": "empirical R-7 linear quantiles and midrank percentiles",
            "peer_count": count,
            "distinct_value_count": len(set(sorted_values)),
            "minimum": sorted_values[0],
            "p25": _quantile(sorted_values, 0.25),
            "p50": _quantile(sorted_values, 0.50),
            "p75": _quantile(sorted_values, 0.75),
            "maximum": sorted_values[-1],
        },
        "entities": enriched,
        "interpretation_limits": [
            "Percentiles describe this supplied peer distribution; they do not establish profitability, incrementality, or an action threshold.",
            "Peer count, ties, missing entities, eligibility, reporting latency, and comparability determine resolution and transportability.",
            "Do not turn P25 or P75 into a universal pause, scale, bid, or budget rule.",
        ],
    }


def _clean_stages(raw: Any, prefix: str) -> list[dict[str, Any]]:
    items = _list(raw, prefix, minimum=2)
    stages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_item in enumerate(items):
        item = _object(raw_item, f"{prefix}[{index}]")
        name = _string(item.get("name"), f"{prefix}[{index}].name")
        if name in seen:
            raise InputError(f"{prefix}[{index}].name duplicates {name}")
        seen.add(name)
        stages.append(
            {
                "name": name,
                "definition": item.get("definition"),
                "count": _number(
                    item.get("count"), f"{prefix}[{index}].count", minimum=0
                ),
            }
        )
    return stages


def _rate(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _transition_rows(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for upstream, downstream in zip(stages, stages[1:]):
        rows.append(
            {
                "from_stage": upstream["name"],
                "to_stage": downstream["name"],
                "upstream_count": upstream["count"],
                "downstream_count": downstream["count"],
                "stage_to_previous_rate": _rate(
                    downstream["count"], upstream["count"]
                ),
                "count_difference": downstream["count"] - upstream["count"],
            }
        )
    return rows


def funnel(payload: dict[str, Any]) -> dict[str, Any]:
    context = _object(payload.get("context"), "context")
    count_semantics = context.get("count_semantics")
    if count_semantics not in {"unique_entities", "events", "other"}:
        raise InputError(
            "context.count_semantics must be unique_entities, events, or other"
        )
    nonincreasing = context.get("stage_chain_expected_nonincreasing")
    if not isinstance(nonincreasing, bool):
        raise InputError(
            "context.stage_chain_expected_nonincreasing must be boolean"
        )
    clean_context = {
        "funnel_name": _string(context.get("funnel_name"), "context.funnel_name"),
        "source": _string(context.get("source"), "context.source"),
        "window": _string(context.get("window"), "context.window"),
        "timezone": _string(context.get("timezone"), "context.timezone"),
        "identity_unit": _string(context.get("identity_unit"), "context.identity_unit"),
        "deduplication_state": _string(
            context.get("deduplication_state"), "context.deduplication_state"
        ),
        "count_semantics": count_semantics,
        "stage_chain_expected_nonincreasing": nonincreasing,
        **_lag_contract(context, "context"),
    }
    stages = _clean_stages(payload.get("stages"), "stages")
    if nonincreasing:
        for left, right in zip(stages, stages[1:]):
            if right["count"] > left["count"]:
                raise InputError(
                    f"stage {right['name']} exceeds {left['name']} while a nested non-increasing chain was asserted"
                )

    result: dict[str, Any] = {
        "command": "funnel",
        "context": clean_context,
        "stages": stages,
        "transitions": _transition_rows(stages),
        "overall_first_to_last_rate": _rate(stages[-1]["count"], stages[0]["count"]),
        "interpretation_limits": [
            "The script calculates supplied stage arithmetic; it does not classify severity, infer a leak cause, or forecast a causal lift.",
            "Event counts are not necessarily nested users. Call a ratio a conversion rate only when identity, deduplication, and stage nesting are valid.",
            "Segment and baseline comparisons require stable definitions, binding, mix, lag, and source coverage.",
        ],
    }

    comparison_raw = payload.get("comparison")
    if comparison_raw is not None:
        comparison = _object(comparison_raw, "comparison")
        comparison_stages = _clean_stages(
            comparison.get("stages"), "comparison.stages"
        )
        if [item["name"] for item in comparison_stages] != [
            item["name"] for item in stages
        ]:
            raise InputError("comparison stage names and order must match current stages")
        comparison_evidence = _comparability_contract(comparison, "comparison")
        comparison_lag = _lag_contract(comparison, "comparison")
        if nonincreasing:
            for left, right in zip(comparison_stages, comparison_stages[1:]):
                if right["count"] > left["count"]:
                    raise InputError(
                        f"comparison stage {right['name']} exceeds {left['name']} while a nested non-increasing chain was asserted"
                    )

        baseline_rows = _transition_rows(comparison_stages)
        current_rows = result["transitions"]
        compared_rows: list[dict[str, Any]] = []
        for current, baseline in zip(current_rows, baseline_rows):
            current_rate = current["stage_to_previous_rate"]
            baseline_rate = baseline["stage_to_previous_rate"]
            absolute_change = (
                None
                if current_rate is None or baseline_rate is None
                else current_rate - baseline_rate
            )
            relative_change = (
                None
                if absolute_change is None or baseline_rate == 0
                else absolute_change / abs(baseline_rate)
            )
            compared_rows.append(
                {
                    "from_stage": current["from_stage"],
                    "to_stage": current["to_stage"],
                    "current_rate": current_rate,
                    "comparison_rate": baseline_rate,
                    "absolute_rate_change": absolute_change,
                    "relative_rate_change": relative_change,
                    "current_downstream_count": current["downstream_count"],
                    "comparison_downstream_count": baseline["downstream_count"],
                    "downstream_count_change": current["downstream_count"]
                    - baseline["downstream_count"],
                }
            )
        result["comparison"] = {
            "window": _string(comparison.get("window"), "comparison.window"),
            "comparability_confirmed": True,
            "comparability_evidence": comparison_evidence,
            **comparison_lag,
            "stages": comparison_stages,
            "transitions": compared_rows,
            "overall_first_to_last_rate": _rate(
                comparison_stages[-1]["count"], comparison_stages[0]["count"]
            ),
        }
    return result


def _clean_periods(raw: Any) -> list[dict[str, Any]]:
    items = _list(raw, "periods", minimum=2)
    periods: list[dict[str, Any]] = []
    labels: set[str] = set()
    previous_start: datetime | None = None
    previous_end: datetime | None = None
    for index, raw_item in enumerate(items):
        item = _object(raw_item, f"periods[{index}]")
        label = _string(item.get("label"), f"periods[{index}].label")
        if label in labels:
            raise InputError(f"periods[{index}].label duplicates {label}")
        labels.add(label)
        start = _parse_datetime(item.get("start"), f"periods[{index}].start")
        end = _parse_datetime(item.get("end"), f"periods[{index}].end")
        if end <= start:
            raise InputError(f"periods[{index}].end must be after start")
        if previous_start is not None and start <= previous_start:
            raise InputError("periods must be supplied in strictly increasing time order")
        if previous_end is not None and start < previous_end:
            raise InputError("periods must not overlap")
        periods.append(
            {
                "label": label,
                "start_utc": start.isoformat(),
                "end_utc": end.isoformat(),
                "duration_seconds": (end - start).total_seconds(),
                "numerator": _number(
                    item.get("numerator"), f"periods[{index}].numerator", minimum=0
                ),
                "denominator": _number(
                    item.get("denominator"),
                    f"periods[{index}].denominator",
                    minimum=0,
                ),
            }
        )
        previous_start = start
        previous_end = end
    return periods


def _clean_entity_rows(raw: Any, prefix: str) -> list[dict[str, Any]]:
    items = _list(raw, prefix)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_item in enumerate(items):
        item = _object(raw_item, f"{prefix}[{index}]")
        entity_id = _string(item.get("id"), f"{prefix}[{index}].id")
        if entity_id in seen:
            raise InputError(f"{prefix}[{index}].id duplicates {entity_id}")
        seen.add(entity_id)
        rows.append(
            {
                "id": entity_id,
                "name": item.get("name"),
                "numerator": _number(
                    item.get("numerator"), f"{prefix}[{index}].numerator", minimum=0
                ),
                "denominator": _number(
                    item.get("denominator"),
                    f"{prefix}[{index}].denominator",
                    minimum=0,
                ),
            }
        )
    return rows


def review(payload: dict[str, Any]) -> dict[str, Any]:
    metric = _metric_contract(payload)
    metric_raw = _object(payload.get("metric"), "metric")
    multiplier = _number(metric_raw.get("multiplier", 1), "metric.multiplier", minimum=0)
    if multiplier == 0:
        raise InputError("metric.multiplier must be > 0")
    metric["multiplier"] = multiplier

    scope = _object(payload.get("scope"), "scope")
    clean_scope = {
        field: _string(scope.get(field), f"scope.{field}")
        for field in [
            "advertiser_id",
            "objective",
            "business_outcome",
            "grain",
            "timezone",
            "source",
            "metric_definition",
            "report_latency",
        ]
    }
    clean_scope["comparability_confirmed"] = True
    clean_scope["comparability_evidence"] = _comparability_contract(scope, "scope")
    clean_scope.update(_lag_contract(scope, "scope"))

    periods = _clean_periods(payload.get("periods"))
    for item in periods:
        item["metric_value"] = (
            None
            if item["denominator"] == 0
            else item["numerator"] / item["denominator"] * multiplier
        )
    prior = periods[-2]
    current = periods[-1]
    if current["metric_value"] is None or prior["metric_value"] is None:
        absolute_change = None
        relative_change = None
        directional_improvement = None
    else:
        absolute_change = current["metric_value"] - prior["metric_value"]
        relative_change = (
            None
            if prior["metric_value"] == 0
            else absolute_change / abs(prior["metric_value"])
        )
        directional_improvement = (
            absolute_change
            if metric["direction"] == "higher_is_better"
            else -absolute_change
        )

    valid_values = [
        item["metric_value"]
        for item in periods
        if item["metric_value"] is not None
    ]
    descriptive: dict[str, Any] = {
        "valid_period_count": len(valid_values),
        "minimum": min(valid_values) if valid_values else None,
        "median": median(valid_values) if valid_values else None,
        "maximum": max(valid_values) if valid_values else None,
        "descriptive_slope_per_period": None,
    }
    if len(valid_values) == len(periods) and len(periods) >= 3:
        x_mean = (len(periods) - 1) / 2
        y_mean = sum(valid_values) / len(valid_values)
        denominator = sum((index - x_mean) ** 2 for index in range(len(periods)))
        descriptive["descriptive_slope_per_period"] = sum(
            (index - x_mean) * (value - y_mean)
            for index, value in enumerate(valid_values)
        ) / denominator

    result: dict[str, Any] = {
        "command": "review",
        "metric": metric,
        "scope": clean_scope,
        "periods": periods,
        "current_vs_prior": {
            "current_label": current["label"],
            "prior_label": prior["label"],
            "current_value": current["metric_value"],
            "prior_value": prior["metric_value"],
            "absolute_change": absolute_change,
            "relative_change": relative_change,
            "directional_improvement_in_metric_units": directional_improvement,
            "current_numerator_change": current["numerator"] - prior["numerator"],
            "current_denominator_change": current["denominator"]
            - prior["denominator"],
        },
        "multi_period_description": descriptive,
        "interpretation_limits": [
            "The ratio is calculated from summed numerator and denominator inputs; do not average row-level ratios.",
            "The slope is descriptive context, not proof that a trend will persist or that media caused the movement.",
            "Objective selection, materiality, sparse-count uncertainty, mix, lag, and business impact remain decision work outside this arithmetic.",
        ],
    }

    has_current_entities = "current_entities" in payload
    has_prior_entities = "prior_entities" in payload
    expected_ids = None
    if "expected_active_entity_ids" in scope:
        supplied = _list(scope["expected_active_entity_ids"], "scope.expected_active_entity_ids")
        validated = [_string(item, "scope.expected_active_entity_ids item") for item in supplied]
        expected_ids = set(validated)
        if len(expected_ids) != len(validated):
            raise InputError("scope.expected_active_entity_ids contains duplicate IDs; use paid-sweep for census diagnostics")
        if not has_current_entities:
            raise InputError("independent expected active IDs require current_entities; use paid-sweep for full census")
    if has_current_entities != has_prior_entities:
        raise InputError(
            "current_entities and prior_entities must be supplied together"
        )
    if has_current_entities:
        current_rows = _clean_entity_rows(
            payload.get("current_entities"), "current_entities"
        )
        prior_rows = _clean_entity_rows(payload.get("prior_entities"), "prior_entities")
        current_map = {item["id"]: item for item in current_rows}
        prior_map = {item["id"]: item for item in prior_rows}
        if expected_ids is not None and set(current_map) != expected_ids:
            missing = sorted(expected_ids - set(current_map))
            extra = sorted(set(current_map) - expected_ids)
            raise InputError(f"current_entities differs from independent expected active IDs; missing={missing!r}, extra={extra!r}; use paid-sweep for full census")
        movers: list[dict[str, Any]] = []
        for entity_id in sorted(set(current_map) | set(prior_map)):
            now = current_map.get(entity_id, {"numerator": 0.0, "denominator": 0.0})
            before = prior_map.get(entity_id, {"numerator": 0.0, "denominator": 0.0})
            now_value = _rate(now["numerator"], now["denominator"])
            before_value = _rate(before["numerator"], before["denominator"])
            movers.append(
                {
                    "id": entity_id,
                    "name": now.get("name") or before.get("name"),
                    "current_metric_value": None
                    if now_value is None
                    else now_value * multiplier,
                    "prior_metric_value": None
                    if before_value is None
                    else before_value * multiplier,
                    "numerator_change": now["numerator"] - before["numerator"],
                    "denominator_change": now["denominator"]
                    - before["denominator"],
                    "current_numerator_share": _rate(
                        now["numerator"], current["numerator"]
                    ),
                    "current_denominator_share": _rate(
                        now["denominator"], current["denominator"]
                    ),
                }
            )
        movers.sort(
            key=lambda item: (
                abs(item["denominator_change"]),
                abs(item["numerator_change"]),
                item["id"],
            ),
            reverse=True,
        )
        current_entity_numerator = sum(item["numerator"] for item in current_rows)
        current_entity_denominator = sum(item["denominator"] for item in current_rows)
        prior_entity_numerator = sum(item["numerator"] for item in prior_rows)
        prior_entity_denominator = sum(item["denominator"] for item in prior_rows)
        result["entity_change_descriptors"] = {
            "ordering": "absolute denominator change, then absolute numerator change; descriptive, not causal",
            "entities": movers,
            "coverage_reconciliation": {
                "current_numerator_difference_to_period": current_entity_numerator
                - current["numerator"],
                "current_denominator_difference_to_period": current_entity_denominator
                - current["denominator"],
                "prior_numerator_difference_to_period": prior_entity_numerator
                - prior["numerator"],
                "prior_denominator_difference_to_period": prior_entity_denominator
                - prior["denominator"],
            },
        }
    return result


COMMANDS = {
    "benchmark": benchmark,
    "funnel": funnel,
    "review": review,
}


def _read_payload(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise InputError("input JSON must be an object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted({*COMMANDS, "paid-sweep"}))
    parser.add_argument("--input", default="-", help="JSON file path, or - for stdin")
    parser.add_argument("--top", type=int, help="Paid-sweep summary limit only; never truncates the census")
    args = parser.parse_args(argv)
    if args.top is not None and args.command != "paid-sweep":
        parser.error("--top applies only to paid-sweep")
    try:
        payload = _read_payload(args.input)
        if args.command == "paid-sweep":
            from paid_sweep import sweep

            result = sweep(payload, top=args.top)
            if "creative_evidence_events" in payload:
                events = payload["creative_evidence_events"]
                if not isinstance(events, list) or any(not isinstance(event, dict) for event in events):
                    raise InputError("creative_evidence_events must be a list of independently sourced event objects")
                # These are normalized attestations, not facts verified by this
                # transport. The decision verifier binds each relied-on event.
                result["creative_evidence_events"] = events
            result["audit_ready"] = False
            result["missing_current_decision_ids"] = result["coverage"]["expected_active_ids"]
            if "decision_handoff" in payload:
                from paid_decisions import InputError as HandoffInputError, handoff

                supplied = _object(payload["decision_handoff"], "decision_handoff")
                try:
                    decision_handoff = handoff({**supplied, "scope": result["scope"], "inventory": payload["inventory"],
                                                 "current_rows": result["entities"],
                                                 "current_meta_source": payload["lifecycle"]["manifest"].get("source_id")})
                except HandoffInputError as exc:
                    decision_handoff = {"complete_for_decision": False, "input_error": str(exc)}
                result["decision_handoff"] = decision_handoff
                current_ids = {row["binding"]["ad_id"] for row in decision_handoff.get("decisions", [])
                               if row.get("current") is not None and row.get("status") != "unresolved"}
                missing_ids = sorted(set(result["coverage"]["expected_active_ids"]) - current_ids)
                result["missing_current_decision_ids"] = missing_ids
                result["audit_ready"] = (result["complete_for_decision"] and decision_handoff["complete_for_decision"] and not missing_ids)
        else:
            result = COMMANDS[args.command](payload)
    except (ValueError, OSError) as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {"ok": True, "result": result},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
