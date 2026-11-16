"""Check bounded creative WATCH contracts against native evidence; never change delivery."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from math import isfinite, isclose
from operator import eq, ge, gt, le, lt
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


METRICS = {"spend", "impressions", "lpv", "atc", "checkout", "purchases"}
OPPORTUNITY = {"spend", "impressions", "lpv"}
OPERATORS = {"lt": lt, "lte": le, "eq": eq, "gte": ge, "gt": gt}
TECHNICAL_EVENTS = {"technical_change", "measurement_restored", "placement_fault_confirmed"}
BINDING = ("account_id", "campaign_id", "parent_id", "ad_id", "epoch_id")
CONTEXT = ("currency", "timezone", "attribution", "report_time")
QUALIFIED = {"observed", "sparse_no_delivery"}


def _obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _choice(value: Any, choices) -> bool:
    return isinstance(value, str) and value in choices


def _num(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return False
    try:
        return isfinite(value) and value >= 0
    except OverflowError:
        return False


def _time(value: Any) -> datetime | None:
    if not _text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def _date(value: Any) -> date | None:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.isoformat() == value else None


def _dates(window: Any) -> tuple[date, date] | None:
    window = _obj(window)
    start, end = _date(window.get("start_date")), _date(window.get("end_date"))
    return (start, end) if start and end and start <= end else None


def _first_clean_date(change: datetime, zone: ZoneInfo) -> date:
    local = change.astimezone(zone)
    mixed = any((local.hour, local.minute, local.second, local.microsecond))
    return local.date() + timedelta(days=mixed)


def _bound(row: dict, scope: dict) -> bool:
    return (
        row.get("binding_verified") is True
        and all(_text(row.get(key)) for key in BINDING)
        and all(row.get(key) == scope.get(key) for key in ("account_id", "campaign_id"))
        and _choice(row.get("coverage_state"), QUALIFIED)
    )


def _metric(row: dict, window: tuple[date, date], name: str) -> tuple[float | None, str | None]:
    """Exact dates only; omitted rows/aliases never become zero."""
    if not _choice(name, METRICS | {"purchase_value"}):
        return None, None
    metrics = _obj(row.get("metrics"))
    start, end = window
    # Lifecycle totals can include the current partial date or credit revisions.
    # Match explicit period windows before trying the strictly dated rows.
    for key in ("last_3_closed", "last_7_closed", "current_epoch", "partial_day", "ad_days_lifecycle", "lifecycle"):
        item = _obj(metrics.get(key))
        if (
            _dates(item) == window
            and _choice(item.get("state"), QUALIFIED)
            and _text(item.get("source"))
            and _num(item.get(name))
        ):
            return item[name], item["source"]
    days = row.get("ad_day_observations")
    source = _obj(metrics.get("ad_days_lifecycle")).get("source")
    if not isinstance(days, list) or not _text(source):
        return None, None
    selected: dict[date, float] = {}
    for item in days:
        item = _obj(item)
        day = _date(item.get("date"))
        if day is not None and start <= day <= end:
            if day in selected or not _num(item.get(name)):
                return None, None
            selected[day] = item[name]
    return (sum(selected.values()), source) if len(selected) == (end - start).days + 1 else (None, None)


def _condition_valid(condition: Any) -> bool:
    item = _obj(condition)
    if not _text(item.get("source")):
        return False
    if item.get("kind") == "metric":
        return bool(
            _dates(item.get("window")) and _choice(item.get("metric"), METRICS)
            and _choice(item.get("op"), OPERATORS) and _num(item.get("value"))
        )
    return (
        item.get("kind") == "technical_event"
        and _choice(item.get("event_type"), TECHNICAL_EVENTS)
        and _text(item.get("expected_state"))
    )


def _source_events(events: Any, row: dict, as_of: datetime) -> dict[str, dict]:
    """Accept only separate normalized evidence; duplicate IDs are ambiguous."""
    if not isinstance(events, (list, tuple)):
        return {}
    verified: dict[str, dict] = {}
    seen: set[str] = set()
    for event in events:
        event = _obj(event)
        key = event.get("id")
        if not _text(key):
            continue
        if key in seen:
            verified.pop(key, None)
            continue
        seen.add(key)
        observed = _time(event.get("observed_at"))
        occurred = _time(event.get("occurred_at"))
        if (
            event.get("verified") is True and _text(event.get("source"))
            and (observed is not None and observed <= as_of)
            and (occurred is not None and occurred <= observed)
            and all(event.get(field) == row.get(field) for field in BINDING)
        ):
            verified[key] = event
    return verified


def _trigger(
    condition: Any, row: dict, events: dict, opened: datetime, as_of: datetime,
    due: datetime, zone: ZoneInfo, *, spend_bound: bool = False,
) -> tuple[str, dict | None]:
    """Metric condition.source is rule provenance; claim evidence uses the native window source."""
    if not _condition_valid(condition):
        return "unknown", None
    if condition["kind"] == "technical_event":
        candidates = [
            event for event in events.values()
            if event.get("event_type") == condition["event_type"]
            and event["source"] == condition["source"]
            and opened < _time(event["observed_at"]) <= as_of
            and opened <= _time(event["occurred_at"])
        ]
        if not candidates:
            return ("pending", None) if opened == as_of else ("unknown", None)
        latest_time = max(_time(item["observed_at"]) for item in candidates)
        latest = [item for item in candidates if _time(item["observed_at"]) == latest_time]
        states = {item["state"] for item in latest if _text(item.get("state"))}
        if len(states) != 1 or any(not _text(item.get("state")) for item in latest):
            return "unknown", None
        matched = latest[0]
        state = "met" if matched["state"] == condition["expected_state"] else "pending"
        return state, {field: matched.get(field) for field in ("id", "source", "observed_at", "state")}
    start, end = _dates(condition["window"])
    if start < opened.astimezone(zone).date() or end >= due.astimezone(zone).date():
        return "unknown", None
    epoch_started = _time(row.get("epoch_started_at"))
    if not spend_bound and epoch_started and start < _first_clean_date(epoch_started, zone):
        return "unknown", None
    today = as_of.astimezone(zone).date()
    if end >= today and not spend_bound:
        return "pending", None  # time not yet observable; expiration is independent
    if start > today:
        return "pending", None
    read_window = (start, min(end, today)) if spend_bound else (start, end)
    observed, source = _metric(row, read_window, condition["metric"])
    if observed is None:
        return "unknown", None
    met = OPERATORS[condition["op"]](observed, condition["value"])
    return ("met" if met else "pending"), {
        "observed": observed, "source": source,
        "window": {"start_date": read_window[0].isoformat(), "end_date": read_window[1].isoformat()},
    }


def _fact(
    basis: Any, row: dict, scope: dict, events: dict, as_of: datetime, zone: ZoneInfo,
    history: dict, previous: datetime | None, prior_watch: bool, condition: Any,
) -> dict | None:
    basis = _obj(basis)
    kind = basis.get("kind")
    window = _dates(basis.get("window"))
    today = as_of.astimezone(zone).date()
    prior_row = _obj(history.get("prior_row"))
    event = _obj(events.get(basis.get("event_id"))) if _text(basis.get("event_id")) else {}

    if kind == "approved_retention":
        return {"kind": kind, "source": "same-bound independent handoff MAIN retention"} if history.get("main_retained") is True else None

    if kind in ("first_checkout", "low_opportunity"):
        if window is None or not (today - timedelta(days=1) <= window[1] <= today):
            return None
        if kind == "first_checkout":
            # A single checkout can justify a first bounded look, never reset an open WATCH.
            observed, source = _metric(row, window, "checkout")
            lifetime = _obj(_obj(row.get("metrics")).get("lifecycle"))
            if prior_watch or observed != 1 or lifetime.get("checkout") != 1 or not _choice(lifetime.get("state"), QUALIFIED) or not _text(lifetime.get("source")):
                return None
            if previous:
                baseline = _obj(_obj(prior_row.get("metrics")).get("lifecycle"))
                if (
                    any(prior_row.get(field) != row.get(field) for field in BINDING)
                    or not _choice(baseline.get("state"), QUALIFIED) or not _text(baseline.get("source"))
                    or not _num(baseline.get("checkout")) or baseline["checkout"] != 0
                    or window[1] < previous.astimezone(zone).date()
                ):
                    return None
            return {"kind": kind, "observed": observed, "source": source, "window": basis["window"]}
        metric = basis.get("metric")
        if prior_watch or not _choice(metric, OPPORTUNITY) or not _num(basis.get("value")) or not _text(basis.get("source")):
            return None
        observed, source = _metric(row, window, metric)
        if observed is not None and observed < basis["value"]:
            return {"kind": kind, "metric": metric, "observed": observed, "source": source, "window": basis["window"]}
        return None

    if kind == "first_clean_window":
        if window is None or not isinstance(condition, dict) or _dates(condition.get("window")) != window:
            return None
        change = _time(row.get("epoch_started_at"))
        source = "native verified epoch start"
        if event:
            if not _choice(event.get("event_type"), {"technical_change", "measurement_restored"}):
                return None
            change, source = _time(event.get("occurred_at")), event["source"]
        if change is None or change > as_of or (previous is not None and change <= previous):
            return None
        clean_date = _first_clean_date(change, zone)
        if window != (clean_date, clean_date) or clean_date < today:
            return None
        return {"kind": kind, "source": source, "event_id": event.get("id"), "window": basis["window"]}

    if kind not in ("material_credit", "technical_change") or not event:
        return None
    observed_at, occurred_at = _time(event["observed_at"]), _time(event["occurred_at"])
    if previous is not None and (observed_at <= previous or occurred_at <= previous):
        return None
    if kind == "technical_change":
        if not _choice(event.get("event_type"), TECHNICAL_EVENTS) or not _text(event.get("state")):
            return None
    else:
        credit_date = _date(event.get("report_date"))
        value = event.get("value")
        if (
            event.get("event_type") != "click_credit" or event.get("credit_type") != "click"
            or not _text(event.get("attribution_window")) or event.get("currency") != scope.get("currency")
            or not _num(value) or value <= 0 or credit_date is None or credit_date >= today
        ):
            return None
        if previous is not None and credit_date <= previous.astimezone(zone).date():
            return None  # an older report-day revision does not reset a paid WATCH
        purchases, _ = _metric(row, (credit_date, credit_date), "purchases")
        aggregate, _ = _metric(row, (credit_date, credit_date), "purchase_value")
        if purchases is None or purchases <= 0 or aggregate is None or value > aggregate or (
            purchases == 1 and not isclose(value, aggregate)
        ):
            return None
    return {"kind": kind, **{field: event[field] for field in ("id", "source", "observed_at")}}


def assess_watch(record: Any, row: Any, scope: Any, history: Any = None, *, events: Any = ()) -> dict:
    """Check one current WATCH against a separate native row and frozen prior anchor.

    `trigger_state` assesses this prospective contract. `prior_trigger_state`
    assesses the old frozen predicate, never a caller-entered state.
    """
    record, row, scope, history = map(_obj, (record, row, scope, history))
    result = {
        "ok": False, "errors": [], "trigger_state": "unknown", "prior_trigger_state": "unknown",
        "prior_watch": False, "expired": None, "verified_fact": None, "prior_observation": None,
    }
    errors = result["errors"]
    as_of = _time(scope.get("as_of"))
    try:
        zone = ZoneInfo(scope["timezone"])
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError):
        zone = None
    if not (_bound(row, scope) and row.get("current_paid_delivery") is True and as_of and zone and all(_text(scope.get(field)) for field in CONTEXT)):
        errors.append("WATCH requires a covered verified native ad/epoch, qualified scope and as_of")
        return result
    due = _time(record.get("due_at"))
    condition = record.get("condition")
    if not _text(record.get("question")) or not _condition_valid(condition) or due is None or due <= as_of:
        errors.append("WATCH requires a learning question, valid prospective condition and future due_at")
        return result
    prior = _obj(history.get("prior"))
    old = _obj(prior.get("watch") or prior.get("watch_contract"))
    previous = _time(prior.get("as_of"))
    disposition = history.get("prior_disposition")
    prior_watch = bool(old) or disposition in ("continue", "watch") or (
        disposition is None and prior.get("status") in ("deferred", "watch", "continue", "monitor")
    )
    result["prior_watch"] = prior_watch
    old_due = _time(old.get("due_at"))
    event_index = _source_events(events, row, as_of)
    meta = _obj(_obj(prior.get("observation")).get("meta"))
    old_binding_matches = all(prior.get(key) == row.get(key) for key in BINDING)
    old_context_matches = all(meta.get(field) == scope.get(field) for field in CONTEXT)
    if prior and (previous is None or previous >= as_of):
        errors.append("WATCH prior anchor must precede current as_of")
    if prior_watch and old and old_due and previous and previous < old_due:
        result["expired"] = as_of >= old_due
        verified_rebind = (
            history.get("verified_rebind") is True and old_context_matches
            and all(prior.get(key) == row.get(key) for key in BINDING if key != "epoch_id")
            and _text(prior.get("epoch_id")) and prior["epoch_id"] != row["epoch_id"]
        )
        if not (
            (old_binding_matches and old_context_matches) or verified_rebind
            or (_obj(record.get("basis")).get("kind") == "approved_retention" and history.get("main_retained") is True)
        ):
            errors.append("WATCH prior native identity, epoch or reporting context differs; do not carry its trigger")
        if old_binding_matches and old_context_matches:
            state, observation = _trigger(old.get("condition"), row, event_index, previous, as_of, old_due, zone)
            result.update(prior_trigger_state=state, prior_observation=observation)
            old_wait = _obj(old.get("wait_cost"))
            if old_wait.get("kind") == "observable_bound" and _obj(old_wait.get("condition")).get("op") in ("gte", "gt"):
                bound_state, bound_observation = _trigger(
                    old_wait.get("condition"), row, event_index, previous, as_of, old_due, zone, spend_bound=True,
                )
                result.update(prior_wait_bound_state=bound_state, prior_wait_bound_observation=bound_observation)
                if bound_state == "met":
                    result["prior_trigger_state"] = "met"
                elif bound_state == "unknown" and result["prior_trigger_state"] != "met":
                    result["prior_trigger_state"] = "unknown"
    elif prior_watch:
        resolution = _obj(record.get("legacy_resolution"))
        if (
            previous is None or _time(resolution.get("prior_as_of")) != previous
            or resolution.get("outcome") != "retired_unstructured" or not _text(resolution.get("rationale"))
        ):
            errors.append("legacy prior WATCH is unstructured/unknown and requires explicit retirement before a new bounded decision")

    # An in-flight contract may be re-read; updating its predicates or extending
    # its due time constitutes a renewal, even if the old condition was pending.
    carry = (
        prior_watch and bool(old) and result["expired"] is False
        and result["prior_trigger_state"] == "pending" and all(record.get(key) == old.get(key) for key in (
            "basis", "due_at", "condition", "wait_cost", "question",
        ))
    )
    opened = previous if carry else as_of
    result["trigger_state"], _ = _trigger(condition, row, event_index, opened, as_of, due, zone)
    if condition["kind"] == "metric":
        start, end = _dates(condition["window"])
        if start < opened.astimezone(zone).date() or end >= due.astimezone(zone).date():
            errors.append("WATCH condition must observe a prospective complete account-local window before due_at")
        epoch_started = _time(row.get("epoch_started_at"))
        if epoch_started and start < _first_clean_date(epoch_started, zone):
            errors.append("WATCH outcome condition cannot count a mixed native epoch boundary day as clean")

    wait = _obj(record.get("wait_cost"))
    if wait.get("kind") == "estimated_range":
        low, high = wait.get("lower"), wait.get("upper")
        if not (_num(low) and _num(high) and low <= high and wait.get("currency") == scope["currency"] and _text(wait.get("source"))):
            errors.append("WATCH wait_cost needs a sourced range in the sweep currency")
    elif wait.get("kind") == "observable_bound":
        limit = _obj(wait.get("condition"))
        dates = _dates(limit.get("window"))
        if (
            not _condition_valid(limit) or limit.get("kind") != "metric"
            or not _choice(limit.get("metric"), {"spend", "impressions"})
            or not _choice(limit.get("op"), {"gte", "gt"})
            or not dates or dates[0] < opened.astimezone(zone).date()
            or dates[1] >= due.astimezone(zone).date() or not _text(wait.get("source"))
        ):
            errors.append("WATCH wait_cost needs a prospective spend/impressions re-decision bound and source")
        else:
            bound_state, bound_observation = _trigger(
                limit, row, event_index, opened, as_of, due, zone, spend_bound=True,
            )
            result.update(wait_bound_state=bound_state, wait_bound_observation=bound_observation)
            if bound_state == "met":
                errors.append("WATCH wait_cost bound is already met at this observation; re-decide before continuing")
    else:
        errors.append("WATCH wait_cost requires an estimated range or observable bound")

    if carry:
        result["verified_fact"] = {"kind": "unchanged_in_flight_contract"}
    else:
        result["verified_fact"] = _fact(
            record.get("basis"), row, scope, event_index, as_of, zone, history,
            previous, prior_watch, condition,
        )
        if result["verified_fact"] is None:
            errors.append("WATCH requires decision-relevant verified evidence; repetition, date shifts, old credit or carts do not qualify")
    result["ok"] = not errors
    return result
