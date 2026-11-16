"""Build an exhaustive paid-delivery census from independently supplied local evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
import math
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCOPE_FIELDS = ("platform", "account_id", "campaign_id", "currency", "timezone", "as_of", "attribution", "report_time")
BASE_METRICS = ("spend", "impressions", "lpv", "atc", "checkout")
METRICS = (*BASE_METRICS, "purchases", "purchase_value")
CORE_METRICS = ("spend", "purchases", "purchase_value")
ACTIVE = {"ACTIVE", "ENABLED", "DELIVERING"}
INACTIVE = {"PAUSED", "DISABLED", "ARCHIVED", "DELETED", "REMOVED", "ENDED", "COMPLETED", "INACTIVE"}
PARENT_BLOCKED = {"ADSET_PAUSED", "CAMPAIGN_PAUSED"}


class SweepInputError(ValueError):
    """The input cannot be interpreted as a normalized snapshot."""


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _object(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise SweepInputError(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise SweepInputError(f"{label} must be an array")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    if not _text(value):
        raise SweepInputError(f"{label} must be a timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SweepInputError(f"{label} must be a timezone-aware ISO timestamp") from exc
    if parsed.utcoffset() is None:
        raise SweepInputError(f"{label} must include an offset")
    return parsed


def _date(value: Any, label: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise SweepInputError(f"{label} must be an ISO calendar date") from exc
    if parsed.isoformat() != value:
        raise SweepInputError(f"{label} must use YYYY-MM-DD")
    return parsed


def _metric(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        numeric = float(value)
    except OverflowError:
        return None
    return numeric if math.isfinite(numeric) and numeric >= 0 else None


def _sum(rows: list[dict], key: str) -> float | None:
    values = [item.get(key) for item in rows]
    return None if any(value is None for value in values) else math.fsum(values)


def _status(value: Any) -> str:
    return value.strip().upper() if _text(value) else "UNKNOWN"


def _manifest_checks(manifest: dict, scope: dict, name: str) -> list[str]:
    checks = [f"{name}:scope_mismatch:{key}" for key in SCOPE_FIELDS if manifest.get(key) != scope[key]]
    if not _text(manifest.get("source_id")):
        checks.append(f"{name}:source_id_missing")
    try:
        retrieved = _timestamp(manifest.get("retrieved_at"), f"{name}.retrieved_at")
        if retrieved > _timestamp(scope["as_of"], "scope.as_of"):
            checks.append(f"{name}:source_retrieved_after_as_of")
    except SweepInputError:
        checks.append(f"{name}:retrieved_at_invalid")
    if manifest.get("complete") is not True or manifest.get("pagination_complete") is not True:
        checks.append(f"{name}:query_or_pagination_incomplete")
    return checks


def _dataset(raw: Any, name: str, scope: dict, start: date, end: date, inventory: dict, parents: dict) -> dict:
    bundle = _object(raw, name)
    manifest = _object(bundle.get("manifest"), f"{name}.manifest")
    daily = name == "ad_days"
    source_issues = _manifest_checks(manifest, scope, name)
    availability = manifest.get("availability", "available")
    if not isinstance(availability, str) or availability not in {"available", "unavailable", "unqueried"}:
        availability = "unknown"
    if availability != "available":
        source_issues.append(f"{name}:source_{availability}")
    if manifest.get("grain") != ("ad_day" if daily else "ad"):
        source_issues.append(f"{name}:grain_mismatch")
    if (manifest.get("start_date"), manifest.get("end_date")) != (start.isoformat(), end.isoformat()):
        source_issues.append(f"{name}:window_mismatch")
    if not _text(manifest.get("query_scope_evidence")):
        source_issues.append(f"{name}:query_scope_unverified")
    mapping = manifest.get("mapping")
    mapping_ok = isinstance(mapping, dict) and all(_text(mapping.get(key)) for key in ("count_action_type", "value_action_type", "evidence"))
    if not mapping_ok:
        source_issues.append(f"{name}:canonical_mapping_unverified")
        mapping = {}
    grouped: dict[str, list[dict]] = defaultdict(list)
    row_issues: dict[str, set[str]] = defaultdict(set)
    observed = Counter()
    for index, raw_row in enumerate(_array(bundle.get("rows"), f"{name}.rows")):
        row = _object(raw_row, f"{name}.rows[{index}]")
        ad_id = row.get("ad_id")
        if not _text(ad_id):
            raise SweepInputError(f"{name}.rows[{index}].ad_id must be a nonempty string")
        day = _date(row.get("date"), f"{name}.rows[{index}].date") if daily else None
        observed[(ad_id, day)] += 1
        if day is not None and not start <= day <= end:
            row_issues[ad_id].add("row_date_outside_source_scope")
        for key, expected in (("start_date", day or start), ("end_date", day or end)):
            if key in row and row[key] != expected.isoformat():
                row_issues[ad_id].add(f"row_scope_drift:{key}")
        if (row.get("account_id"), row.get("campaign_id")) != (scope["account_id"], scope["campaign_id"]):
            row_issues[ad_id].add("account_or_campaign_drift")
        parent_id = row.get("parent_id")
        if not _text(parent_id) or parent_id not in parents:
            row_issues[ad_id].add("unknown_parent")
        native = inventory.get(ad_id)
        if native is not None:
            if parent_id != native["parent_id"]:
                row_issues[ad_id].add("parent_drift")
            if "epoch_id" in row and row["epoch_id"] != native["epoch_id"]:
                row_issues[ad_id].add("snapshot_epoch_drift")
            if day is not None and day < _date(native["lifecycle_start"], f"inventory.{ad_id}.lifecycle_start"):
                row_issues[ad_id].add("row_before_native_lifecycle")
        for key in ("currency", "timezone", "attribution", "report_time", "as_of"):
            if key in row and row[key] != scope[key]:
                row_issues[ad_id].add(f"row_scope_drift:{key}")
        metrics = {key: _metric(row.get(key)) for key in BASE_METRICS}
        if metrics["spend"] is None or any(row.get(key) is not None and metrics[key] is None for key in BASE_METRICS):
            row_issues[ad_id].add("invalid_delivery_metric")
        actions = row.get("actions")
        values = row.get("action_values")
        count_key = mapping.get("count_action_type")
        value_key = mapping.get("value_action_type")
        count = _metric(actions.get(count_key)) if mapping_ok and isinstance(actions, dict) else None
        count_aliases = mapping.get("count_aliases", [])
        alias_positive = isinstance(actions, dict) and isinstance(count_aliases, list) and any(
            (_metric(actions.get(alias)) or 0) > 0 for alias in count_aliases if _text(alias)
        )
        if mapping_ok and isinstance(actions, dict) and count_key not in actions and not alias_positive and mapping.get("missing_count_is_zero") is True:
            count = 0.0
        if count is None:
            row_issues[ad_id].add("ALIAS_UNMAPPED")
        value_currency = row.get("value_currency", mapping.get("value_currency"))
        value = _metric(values.get(value_key)) if mapping_ok and isinstance(values, dict) and value_currency == scope["currency"] else None
        if (value is None and count == 0 and isinstance(values, dict) and value_key not in values
                and mapping.get("missing_value_for_zero_count_is_zero") is True and value_currency == scope["currency"]):
            value = 0.0
        if value is None:
            row_issues[ad_id].add("VALUE_UNVERIFIED")
        if count == 0 and value is not None and value > 0:
            row_issues[ad_id].add("COUNT_VALUE_CONFLICT")
        grouped[ad_id].append({"date": day, "parent_id": parent_id, **metrics, "purchases": count, "purchase_value": value})
    duplicate_keys = [{"ad_id": ad_id, "date": day.isoformat() if day else None, "rows": n}
                      for (ad_id, day), n in sorted(observed.items()) if n > 1]
    for item in duplicate_keys:
        row_issues[item["ad_id"]].add("duplicate_grain_key")
    return {"manifest": manifest, "availability": availability, "source_issues": source_issues, "grouped": grouped,
            "row_issues": row_issues, "duplicate_keys": duplicate_keys, "observed_rows": sum(observed.values()),
            "unique_rows": len(observed), "extras": sorted(set(grouped) - set(inventory))}


def _controls(raw: Any, scope: dict, start: date, end: date, data: dict, inventory_source: str) -> tuple[dict, list[str]]:
    controls = _object(raw, "controls")
    manifest = _object(controls.get("manifest"), "controls.manifest")
    issues = _manifest_checks(manifest, scope, "controls")
    if manifest.get("independent") is not True or manifest.get("source_id") in [inventory_source, *(src["manifest"].get("source_id") for src in data.values())]:
        issues.append("controls:independent_source_unverified")
    if manifest.get("grain") != "campaign_and_parent" or (manifest.get("start_date"), manifest.get("end_date")) != (start.isoformat(), end.isoformat()):
        issues.append("controls:grain_or_window_mismatch")
    if not _text(manifest.get("query_scope_evidence")):
        issues.append("controls:query_scope_unverified")
    policy = _object(controls.get("residual_policy", {}), "controls.residual_policy")
    for key, raw_rule in policy.items():
        rule = _object(raw_rule, f"controls.residual_policy.{key}")
        if key not in METRICS or _metric(rule.get("absolute_tolerance")) is None or not all(_text(rule.get(k)) for k in ("evidence", "impact")):
            raise SweepInputError(f"controls.residual_policy.{key} requires a supported metric, nonnegative tolerance, evidence, and impact")
    parent_totals = {}
    for index, raw_parent in enumerate(_array(controls.get("parents", []), "controls.parents")):
        parent = _object(raw_parent, f"controls.parents[{index}]")
        parent_id = parent.get("parent_id")
        if not _text(parent_id) or parent_id in parent_totals:
            raise SweepInputError("controls.parents requires unique nonempty parent_id values")
        parent_totals[parent_id] = _object(parent.get("totals"), f"controls.parents[{index}].totals")
    campaign_totals = _object(controls.get("totals"), "controls.totals")

    def compare(rows: list[dict], expected: dict) -> dict:
        comparisons = {}
        for key in sorted(set(CORE_METRICS) | (set(METRICS) & set(expected))):
            control = _metric(expected.get(key))
            observed = _sum(rows, key)
            residual = observed - control if observed is not None and control is not None else None
            exact = residual is not None and math.isclose(residual, 0.0, abs_tol=1e-9)
            rule = policy.get(key)
            accepted = exact or (residual is not None and rule is not None and abs(residual) <= float(rule["absolute_tolerance"]) + 1e-9)
            comparisons[key] = {"control": control, "observed": observed, "residual": residual, "exact": exact,
                                "accepted": accepted, "policy": rule if not exact else None}
        return {"metrics": comparisons, "accepted": all(row["accepted"] for row in comparisons.values()),
                "exact": all(row["exact"] for row in comparisons.values())}

    reconciliation = {"manifest": manifest, "residuals_allocated": False, "by_dataset": {}}
    for name, source in data.items():
        rows = [row for grouped in source["grouped"].values() for row in grouped]
        by_parent: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            if _text(row["parent_id"]):
                by_parent[row["parent_id"]].append(row)
        campaign = compare(rows, campaign_totals)
        parents = {parent_id: compare(by_parent[parent_id], totals) for parent_id, totals in sorted(parent_totals.items())}
        reconciliation["by_dataset"][name] = {"campaign": campaign, "parents": parents}
    return reconciliation, issues


def _window(rows: list[dict], start: date, end: date, *, state: str, daily: bool = False) -> dict:
    verified = state in {"observed", "observed_with_unreported_dates", "sparse_no_delivery"}
    totals = {key: _sum(rows, key) if verified else None for key in METRICS}
    spend, purchases, value = (totals[key] for key in CORE_METRICS)
    dates = [item["date"] for item in rows if item["date"] is not None and (item["purchases"] or 0) > 0]
    last = max(dates) if verified and purchases is not None and dates else None
    after = _sum([item for item in rows if item["date"] is not None and item["date"] > last], "spend") if last else None
    absent = []
    if daily:
        seen_dates = {item["date"] for item in rows}
        absent = [(start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)
                  if start + timedelta(days=offset) not in seen_dates]
    return {"start_date": start.isoformat(), "end_date": end.isoformat(), "state": state, "observed_rows": len(rows),
            "unreported_dates": absent, **totals,
            "cpa": spend / purchases if spend is not None and purchases else None,
            "roas": value / spend if value is not None and spend else None,
            "last_purchase_report_date": last.isoformat() if last else None,
            "spend_after_last_purchase_report_date": after}


def sweep(payload: dict, *, top: int | None = None) -> dict:
    """Reconcile provider-neutral census evidence and retain every scoped entity."""
    if top is not None and (isinstance(top, bool) or not isinstance(top, int) or top < 0):
        raise SweepInputError("top must be a nonnegative integer")
    scope = _object(_object(payload, "payload").get("scope"), "scope")
    if not all(_text(scope.get(key)) for key in (*SCOPE_FIELDS, "lifecycle_start")):
        raise SweepInputError("scope requires platform, account_id, campaign_id, currency, timezone, as_of, attribution, report_time, and lifecycle_start")
    try:
        timezone = ZoneInfo(scope["timezone"])
    except ZoneInfoNotFoundError as exc:
        raise SweepInputError("scope.timezone must identify an IANA time zone") from exc
    as_of = _timestamp(scope["as_of"], "scope.as_of").astimezone(timezone)
    start, end = _date(scope["lifecycle_start"], "scope.lifecycle_start"), as_of.date()
    if start > end:
        raise SweepInputError("scope.lifecycle_start is after the local as_of date")
    native = _object(payload.get("inventory"), "inventory")
    native_manifest = _object(native.get("manifest"), "inventory.manifest")
    native_issues = _manifest_checks(native_manifest, scope, "inventory")
    if native_manifest.get("independent") is not True:
        native_issues.append("inventory:independent_population_unverified")
    parents = {}
    ads = {}
    native_row_issues: dict[str, set[str]] = defaultdict(set)
    for index, raw_parent in enumerate(_array(native.get("parents"), "inventory.parents")):
        parent = _object(raw_parent, f"inventory.parents[{index}]")
        parent_id = parent.get("parent_id")
        if not _text(parent_id):
            raise SweepInputError("inventory.parents requires parent_id")
        if parent_id in parents:
            native_issues.append(f"inventory:duplicate_parent:{parent_id}")
            continue
        if (parent.get("account_id"), parent.get("campaign_id"), parent.get("currency")) != (scope["account_id"], scope["campaign_id"], scope["currency"]):
            native_issues.append(f"inventory:parent_scope_drift:{parent_id}")
        parents[parent_id] = parent
    if not parents:
        native_issues.append("inventory:parent_inventory_empty")
    for index, raw_ad in enumerate(_array(native.get("ads"), "inventory.ads")):
        ad = _object(raw_ad, f"inventory.ads[{index}]")
        ad_id = ad.get("ad_id")
        if not _text(ad_id):
            raise SweepInputError("inventory.ads requires ad_id")
        if ad_id in ads:
            native_row_issues[ad_id].add("duplicate_native_ad_id")
            native_issues.append(f"inventory:duplicate_native_ad_id:{ad_id}")
            continue
        parent_id = ad.get("parent_id")
        if not _text(parent_id) or parent_id not in parents:
            native_row_issues[ad_id].add("native_parent_unverified")
        if (ad.get("account_id"), ad.get("campaign_id")) != (scope["account_id"], scope["campaign_id"]):
            native_row_issues[ad_id].add("native_account_or_campaign_drift")
        ad_start = _date(ad.get("lifecycle_start"), f"inventory.{ad_id}.lifecycle_start")
        if not start <= ad_start <= end:
            native_row_issues[ad_id].add("native_lifecycle_outside_scope")
        raw_epoch_start = ad.get("epoch_started_at")
        epoch_start = None
        if raw_epoch_start is not None:
            try:
                epoch_start = _timestamp(raw_epoch_start, f"inventory.{ad_id}.epoch_started_at").astimezone(timezone)
            except SweepInputError:
                native_row_issues[ad_id].add("native_epoch_timestamp_invalid")
        if not _text(ad.get("epoch_id")) or ad.get("binding_verified") is not True or (epoch_start is not None and epoch_start > as_of):
            native_row_issues[ad_id].add("native_epoch_binding_unverified")
        configured, effective = _status(ad.get("configured_status")), _status(ad.get("effective_status"))
        historical = configured in INACTIVE and effective in (INACTIVE | PARENT_BLOCKED)
        active = configured in ACTIVE and effective in ACTIVE
        if not (active or historical):
            native_row_issues[ad_id].add("configured_effective_status_unresolved")
        if active and _text(parent_id) and parent_id in parents and any(
            _status(parents[parent_id].get(key)) not in ACTIVE for key in ("configured_status", "effective_status")
        ):
            native_row_issues[ad_id].add("active_parent_status_conflict")
        ads[ad_id] = {**ad, "parent_id": parent_id, "epoch_id": ad.get("epoch_id"), "configured_status": configured,
                      "effective_status": effective, "disposition": "historical" if historical else "active_decision",
                      "_ad_start": ad_start, "_epoch_start": epoch_start}
    if not ads:
        native_issues.append("inventory:ad_population_empty")

    data = {name: _dataset(payload.get(name), name, scope, start, end, ads, parents) for name in ("lifecycle", "ad_days")}
    if native_manifest.get("source_id") in [item["manifest"].get("source_id") for item in data.values()]:
        native_issues.append("inventory:source_reuses_analytics_population")
    if data["lifecycle"]["manifest"].get("source_id") == data["ad_days"]["manifest"].get("source_id"):
        native_issues.append("analytics:lifecycle_and_ad_days_not_separately_sourced")
    for key in ("count_action_type", "value_action_type", "value_currency"):
        manifests = [item["manifest"].get("mapping") for item in data.values()]
        if all(isinstance(mapping, dict) for mapping in manifests) and manifests[0].get(key) != manifests[1].get(key):
            native_issues.append(f"analytics:canonical_mapping_mismatch:{key}")
    reconciliation, control_issues = _controls(payload.get("controls"), scope, start, end, data, native_manifest.get("source_id"))
    for name, result in reconciliation["by_dataset"].items():
        if not result["campaign"]["accepted"] or any(not item["accepted"] for item in result["parents"].values()):
            control_issues.append(f"controls:{name}:unresolved_residual")
        if set(result["parents"]) - set(parents):
            control_issues.append(f"controls:{name}:unknown_parent_control")

    def sparse_ok(name: str, parent_id: str) -> bool:
        source = data[name]
        control = reconciliation["by_dataset"][name]
        parent_rows_valid = not any(
            source["row_issues"][ad_id] and any(row["parent_id"] == parent_id for row in rows)
            for ad_id, rows in source["grouped"].items()
        )
        return (not native_issues and not control_issues and not source["source_issues"] and not source["extras"]
                and parent_rows_valid and _text(source["manifest"].get("sparse_no_delivery_evidence"))
                and control["campaign"]["accepted"] and control["parents"].get(parent_id, {}).get("exact") is True
                and "impressions" in control["parents"][parent_id]["metrics"])

    ranges = {"lifecycle": (start, end), "last_7_closed": (max(start, end - timedelta(days=7)), end - timedelta(days=1)),
              "last_3_closed": (max(start, end - timedelta(days=3)), end - timedelta(days=1)), "partial_day": (end, end)}
    entities = []
    for ad_id in sorted(set(ads) | set(data["lifecycle"]["grouped"]) | set(data["ad_days"]["grouped"])):
        ad = ads.get(ad_id)
        if ad is None:
            entities.append({"ad_id": ad_id, "disposition": "unresolved", "coverage_state": "inconsistent", "observation_state": "INCONSISTENT",
                             "current_paid_delivery": None, "issues": ["no_independent_native_inventory_row"], "metrics": {}})
            continue
        parent_id = ad["parent_id"]
        full_rows = data["lifecycle"]["grouped"].get(ad_id, [])
        day_rows = data["ad_days"]["grouped"].get(ad_id, [])
        binding_issues = set(native_row_issues[ad_id])
        dataset_issues = {}
        diagnostics = set()
        for name, source in data.items():
            row_issues = source["row_issues"][ad_id]
            diagnostics.update(row_issues & {"ALIAS_UNMAPPED", "VALUE_UNVERIFIED", "COUNT_VALUE_CONFLICT"})
            dataset_issues[name] = (row_issues - {"ALIAS_UNMAPPED", "VALUE_UNVERIFIED"}) | set(source["source_issues"])
        hard_issues = binding_issues | set().union(*dataset_issues.values())
        ad_start = ad["_ad_start"]
        epoch_start = ad["_epoch_start"]
        epoch_day = end + timedelta(days=1)
        if epoch_start is not None:
            epoch_day = epoch_start.date()
            if epoch_start.hour or epoch_start.minute or epoch_start.second or epoch_start.microsecond:
                epoch_day += timedelta(days=1)
        per_windows = {**ranges, "current_epoch": (max(start, epoch_day), end)}
        sparse = {name: _text(parent_id) and sparse_ok(name, parent_id) for name in data}
        metrics = {}
        for key, (left, right) in per_windows.items():
            left = max(left, ad_start)
            name = "lifecycle" if key == "lifecycle" else "ad_days"
            rows = full_rows if key == "lifecycle" else [item for item in day_rows if left <= item["date"] <= right]
            expected_days = max(0, (right - left).days + 1)
            if key == "current_epoch" and epoch_start is None:
                state = "epoch_start_unknown"
                left = ad_start
            elif left > right:
                state = "not_applicable"
            elif data[name]["availability"] in {"unavailable", "unqueried"}:
                state = data[name]["availability"]
            elif binding_issues or dataset_issues[name]:
                state = "inconsistent"
            elif not rows:
                state = "sparse_no_delivery" if sparse[name] else "missing"
            elif key != "lifecycle" and len(rows) < expected_days and not sparse[name]:
                state = "observed_with_unreported_dates"
            else:
                state = "observed"
            metrics[key] = _window(rows, left, right, state=state, daily=name == "ad_days")
            metrics[key]["source"] = data[name]["manifest"].get("source_id")
        full = metrics["lifecycle"]
        daily_state = "missing"
        if data["ad_days"]["availability"] in {"unavailable", "unqueried"}:
            daily_state = data["ad_days"]["availability"]
        elif binding_issues or dataset_issues["ad_days"]:
            daily_state = "inconsistent"
        else:
            if day_rows:
                daily_state = "observed" if len(day_rows) == (end - ad_start).days + 1 or sparse["ad_days"] else "observed_with_unreported_dates"
            elif sparse["ad_days"]:
                daily_state = "sparse_no_delivery"
        daily_full = _window(day_rows, ad_start, end, state=daily_state, daily=True)
        daily_full["source"] = data["ad_days"]["manifest"].get("source_id")
        for key in ("last_purchase_report_date", "spend_after_last_purchase_report_date"):
            full[key] = daily_full[key]
        metrics["ad_days_lifecycle"] = daily_full
        metric_residuals = {}
        for key in METRICS:
            lhs, rhs = full[key], daily_full[key]
            if lhs is not None and rhs is not None:
                residual = rhs - lhs
                metric_residuals[key] = residual
                rule = payload["controls"].get("residual_policy", {}).get(key)
                if not math.isclose(residual, 0.0, abs_tol=1e-9) and (rule is None or abs(residual) > float(rule["absolute_tolerance"]) + 1e-9):
                    hard_issues.add(f"lifecycle_daily_mismatch:{key}")
        coverage_state = full["state"]
        if binding_issues or (hard_issues and not {full["state"], daily_full["state"]} & {"unavailable", "unqueried"}) or (full["state"] == "sparse_no_delivery" and (daily_full["spend"] or 0) > 0):
            coverage_state = "inconsistent"
        elif daily_full["state"] in {"unavailable", "unqueried"} and coverage_state in {"observed", "sparse_no_delivery"}:
            coverage_state = daily_full["state"]
        elif daily_full["state"] == "missing" and coverage_state in {"observed", "sparse_no_delivery"}:
            coverage_state = "missing"
        observation = {"sparse_no_delivery": "SPARSE_NO_DELIVERY", "missing": "MISSING", "inconsistent": "INCONSISTENT",
                       "unavailable": "UNAVAILABLE", "unqueried": "UNQUERIED"}.get(coverage_state)
        if observation is None:
            observation = "PAID" if (full["spend"] or 0) > 0 else "OBSERVED_ZERO"
        exposure = None
        if ad["disposition"] == "historical":
            exposure = False
        elif ad["configured_status"] in ACTIVE and ad["effective_status"] in ACTIVE and coverage_state in {"observed", "sparse_no_delivery"}:
            exposure = full["spend"] > 0
        entities.append({**{key: val for key, val in ad.items() if not key.startswith("_")}, "coverage_state": coverage_state,
                         "observation_state": observation, "current_paid_delivery": exposure, "issues": sorted(hard_issues | diagnostics),
                         "metrics": metrics, "daily_minus_lifecycle_residuals": metric_residuals,
                         "ad_day_observations": [
                             {"date": item["date"].isoformat(), **{key: item[key] for key in METRICS}}
                             for item in sorted(day_rows, key=lambda item: item["date"])
                         ] if daily_full["state"] in {"observed", "observed_with_unreported_dates", "sparse_no_delivery"} and not hard_issues else None,
                         "epoch_boundary_day_excluded": epoch_start.date().isoformat() if epoch_start and epoch_day > epoch_start.date() else None})

    decision_rows = [row for row in entities if row["disposition"] == "active_decision"]
    valid = [row for row in decision_rows if row["coverage_state"] in {"observed", "sparse_no_delivery"}]
    lifecycle = lambda row: row["metrics"]["lifecycle"]
    paid = [row for row in valid if (lifecycle(row)["spend"] or 0) > 0]
    zero = [row for row in paid if lifecycle(row)["purchases"] == 0]
    positive = [row for row in valid if (lifecycle(row)["purchases"] or 0) > 0]
    verified_value = [row for row in positive if lifecycle(row)["purchase_value"] is not None]
    conflict_ids = set()
    for index, left in enumerate(verified_value):
        lm = lifecycle(left)
        for right in verified_value[index + 1:]:
            rm = lifecycle(right)
            if (lm["purchases"] - rm["purchases"]) * (lm["purchase_value"] - rm["purchase_value"]) < 0:
                conflict_ids.update((left["ad_id"], right["ad_id"]))
    for row in decision_rows:
        row["count_value_order_conflict"] = row["ad_id"] in conflict_ids
        row["count_value_state"] = "COUNT_VALUE_CONFLICT" if row["count_value_order_conflict"] or "COUNT_VALUE_CONFLICT" in row["issues"] else "VALUE_UNVERIFIED" if "VALUE_UNVERIFIED" in row["issues"] else "ALIAS_UNMAPPED" if "ALIAS_UNMAPPED" in row["issues"] else None
    rank = lambda rows, key: [row["ad_id"] for row in sorted(rows, key=lambda item: (-(lifecycle(item)[key] or 0), item["ad_id"]))]
    lanes = {"paid_zero_purchase_by_spend": rank(zero, "spend"), "positive_purchase_by_spend": rank(positive, "spend"),
             "positive_purchase_by_cpa": rank([row for row in positive if lifecycle(row)["cpa"] is not None], "cpa"),
             "positive_purchase_by_low_roas": [row["ad_id"] for row in sorted(verified_value, key=lambda item: (lifecycle(item)["roas"] if lifecycle(item)["roas"] is not None else math.inf, item["ad_id"])) if lifecycle(row)["roas"] is not None],
             "positive_purchase_by_attributed_value": rank(verified_value, "purchase_value"),
             "count_value_conflict_ids": sorted(conflict_ids), "value_unverified_ids": [row["ad_id"] for row in entities if "VALUE_UNVERIFIED" in row["issues"]],
             "zero_exposure_ids": [row["ad_id"] for row in valid if lifecycle(row)["spend"] == 0],
             "unresolved_active_ids": [row["ad_id"] for row in decision_rows if row not in valid or row["issues"]]}
    coverage = {"expected_ids": sorted(ads), "expected_active_ids": [row["ad_id"] for row in decision_rows],
                "inventory_manifest": native_manifest, "inventory_issues": native_issues, "control_issues": control_issues, "sources": {}}
    for name, source in data.items():
        observed_ids = set(source["grouped"])
        missing_ids = set(ads) - observed_ids
        metric_key = "lifecycle" if name == "lifecycle" else "ad_days_lifecycle"
        sparse_ids = {row["ad_id"] for row in entities if row["ad_id"] in missing_ids
                      and row["metrics"][metric_key]["state"] == "sparse_no_delivery"
                      and row["coverage_state"] in {"observed", "sparse_no_delivery"}}
        coverage["sources"][name] = {"manifest": source["manifest"], "observed_ids": sorted(observed_ids),
                                     "missing_ids": sorted(missing_ids), "extra_ids": source["extras"],
                                     "sparse_no_delivery_ids": sorted(sparse_ids), "unresolved_missing_ids": sorted(missing_ids - sparse_ids),
                                     "observed_rows": source["observed_rows"], "unique_rows": source["unique_rows"],
                                     "duplicate_keys": source["duplicate_keys"], "issues": source["source_issues"]}
    complete = not (native_issues or control_issues or lanes["unresolved_active_ids"] or
                    any(source["source_issues"] or source["extras"] or source["duplicate_keys"] for source in data.values()))
    return {"command": "paid-sweep", "scope": dict(scope), "complete_for_decision": complete, "coverage": coverage,
            "windows": {key: {"start_date": left.isoformat(), "end_date": right.isoformat(), "partial": key == "partial_day"} for key, (left, right) in ranges.items()},
            "entities": entities, "lanes": lanes, "control_reconciliation": reconciliation,
            "summary": {"entity_count": len(entities), "active_decision_count": len(decision_rows),
                        "historical_count": sum(row["disposition"] == "historical" for row in entities),
                        "observation_counts": dict(sorted(Counter(row["observation_state"] for row in entities).items())),
                        "lane_counts": {key: len(ids) for key, ids in lanes.items()}, "top": {key: ids[:top] for key, ids in lanes.items()}},
            "interpretation_limits": ["Rankings are descriptive review aids, not cuts, profit, incremental effects, or authorization.",
                                      "Partial-day credit and earlier snapshots remain distinct; residuals are never distributed to ads.",
                                      "Purchase dates are dates on the named reporting basis, not verified merchant order timestamps."]}
