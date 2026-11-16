#!/usr/bin/env python3
"""Build a read-only creative decision plan from a paid sweep and explicit judgments."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
import json
import math
from pathlib import Path
import sys
from typing import Any


BINDING = ("account_id", "campaign_id", "parent_id", "ad_id", "epoch_id")
SCOPE_COMPARISON = ("platform", "account_id", "campaign_id", "currency", "timezone", "attribution", "report_time", "lifecycle_start")
PERFORMANCE_FIELDS = ("spend", "impressions", "lpv", "atc", "checkout", "purchases", "purchase_value", "cpa", "roas")
WINDOWS = ("lifecycle", "last_7_closed", "last_3_closed", "partial_day", "current_epoch")
QUALIFIED = {"observed", "observed_with_unreported_dates"}
CHOICES = {"cut_candidate", "watch", "low_opportunity", "main_retained", "manual_paused", "historical", "zero_exposure", "unresolved"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _map(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _timestamp(value: Any) -> datetime | None:
    if not _text(value):
        return None
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return observed if observed.utcoffset() is not None else None


def _number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _same_number(left: Any, right: Any) -> bool:
    return (left is None and right is None) or (
        _number(left) and _number(right) and math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)
    )


def _list(container: dict, field: str) -> list:
    value = container.get(field, [])
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return value


def _bound(left: dict, right: dict) -> bool:
    return all(_text(left.get(key)) and left[key] == right.get(key) for key in BINDING)


def _window(row: dict, key: str) -> dict:
    return _map(_map(row.get("metrics")).get(key))


def _ids(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value) and len(value) == len(set(value))


def validate_performance_review(review: Any, row: dict) -> list[str]:
    """Validate the creative decision's numeric claims against its own source window."""
    if not isinstance(review, dict):
        return ["performance_review is required"]
    issues = []
    window = review.get("window")
    source = _window(row, window) if window in WINDOWS else {}
    observed = _map(review.get("observed"))
    if source.get("state") not in QUALIFIED or not _text(source.get("source")):
        issues.append("performance_review.window must identify a sourced, observed sweep window")
    if not isinstance(review.get("assessment"), str) or review["assessment"] not in {"adequate", "limited", "unresolved"}:
        issues.append("performance_review.assessment must be adequate, limited, or unresolved")
    for field in ("rationale", "counterevidence"):
        if not _text(review.get(field)):
            issues.append(f"performance_review.{field} is required")
    for field in PERFORMANCE_FIELDS:
        if field not in observed or field not in source or not _same_number(observed[field], source[field]):
            issues.append(f"performance_review.observed.{field} must match the chosen sweep window")
    if review.get("assessment") == "adequate" and (not _number(observed.get("spend")) or observed["spend"] <= 0):
        issues.append("adequate opportunity requires this ad's own positive observed spend")
    return issues


def _unwrap(raw: Any) -> dict:
    sweep = _map(raw)
    if sweep.get("ok") is True:
        sweep = _map(sweep.get("result"))
    if sweep.get("command") != "paid-sweep":
        raise ValueError("paid_sweep must be a paid-sweep result or CLI wrapper")
    return sweep


def _index(records: list, source: str) -> dict:
    index = {}
    for record in records:
        if not isinstance(record, dict) or not _text(record.get("ad_id")):
            raise ValueError(f"{source} requires nonempty ad_id on every row")
        ad_id = record["ad_id"]
        if ad_id in index:
            raise ValueError(f"{source} duplicates native ad_id {ad_id}")
        index[ad_id] = record
    return index


def _first_proposal_wait(anchor: Any, row: dict, scope: dict, as_of: datetime, priors: dict, proposal: dict) -> dict:
    result = {"state": "unverified", "first_proposal_at": None, "wait_hours": None,
              "observed_platform_spend_delta": None, "currency": scope["currency"], "snapshot_source": None}
    if not isinstance(anchor, dict) or not _bound(anchor, row) or not _text(anchor.get("proposal_source")):
        return result
    proposed_at = _timestamp(anchor.get("proposed_at"))
    latest_proposal_at = _timestamp(proposal.get("proposed_at")) if proposal else None
    if proposed_at is None or proposed_at > as_of or (proposal and (latest_proposal_at is None or proposed_at > latest_proposal_at)):
        return result
    result.update(state="wait_only", first_proposal_at=anchor["proposed_at"], wait_hours=(as_of - proposed_at).total_seconds() / 3600,
                  proposal_source=anchor["proposal_source"])
    snapshot_at = _timestamp(anchor.get("snapshot_as_of", anchor.get("proposed_at")))
    prior = priors.get(snapshot_at) if snapshot_at is not None and snapshot_at <= proposed_at else None
    if prior is None or any(_map(prior.get("scope")).get(key) != scope.get(key) for key in SCOPE_COMPARISON):
        return result
    old = next((item for item in _list(prior, "entities") if _bound(item, row)), None)
    if (old is None or old.get("coverage_state") != "observed" or old.get("binding_verified") is not True
            or old.get("lifecycle_start") != row.get("lifecycle_start")):
        return result
    previous, current = _window(old, "lifecycle"), _window(row, "lifecycle")
    if (not _text(previous.get("source")) or previous.get("source") != anchor.get("snapshot_source")
            or not _number(previous.get("spend")) or not _number(current.get("spend"))):
        return result
    change = current["spend"] - previous["spend"]
    result.update(state="observed_delta" if change >= 0 else "snapshot_revision", snapshot_source=previous["source"],
                  observed_platform_spend_delta=max(0.0, change) if change >= 0 else None,
                  signed_spend_change=change, current_snapshot_source=current.get("source"))
    return result


def _manual_pause(record: Any, row: dict, as_of: datetime) -> bool:
    if not isinstance(record, dict) or not _bound(record, row) or record.get("actor_type") != "owner_manual":
        return False
    readback = _map(record.get("readback"))
    activity_source, read_source = record.get("source"), readback.get("source")
    changed, read = _timestamp(record.get("applied_at")), _timestamp(readback.get("read_at"))
    epoch_start = _timestamp(row.get("epoch_started_at"))
    return bool(_bound(readback, row) and _text(activity_source) and _text(read_source) and activity_source != read_source
                and changed is not None and read is not None and changed <= read <= as_of and readback.get("independent") is True
                and (epoch_start is None or epoch_start <= changed)
                and all(row.get(key) == readback.get(key) == "PAUSED" for key in ("configured_status", "effective_status")))


def _proposal_status(ad_id: str, remaining: dict, verified: dict, manual: bool) -> str:
    if manual:
        return "manual_pause_verified"
    if ad_id in verified:
        return "applied_verified"
    if ad_id in remaining:
        return remaining[ad_id].get("remaining_reason") or "unresolved"
    return "recommendation_only"


def _batch_effects(rows: dict, cuts: list, *, inventory_complete: bool) -> list:
    """Describe roster consequences after choices; never use them as a cut filter."""
    result = []
    for parent in sorted({rows[ad_id]["parent_id"] for ad_id in cuts}):
        target = sorted(ad_id for ad_id in cuts if rows[ad_id]["parent_id"] == parent)
        siblings = [row for row in rows.values() if row.get("parent_id") == parent and row.get("ad_id") not in target]
        eligible = sorted(row["ad_id"] for row in siblings if row.get("effective_status") in {"ACTIVE", "ENABLED", "DELIVERING"}
                          and row.get("coverage_state") in {"observed", "sparse_no_delivery"})
        uncertain = sorted(row["ad_id"] for row in siblings if row.get("disposition") != "historical" and row["ad_id"] not in eligible)
        topology = ("uncertain_inventory" if not inventory_complete else "uncertain" if uncertain
                    else "empty" if not eligible else "sole_remaining" if len(eligible) == 1 else "multiple_remaining")
        result.append({"parent_id": parent, "proposed_pause_ids": target, "remaining_eligible_ids": eligible,
                       "unresolved_sibling_ids": uncertain, "if_applied": topology,
                       "parent_status_or_budget_change": "not authorized by this plan", "redistribution": "not yet observed",
                       "replacement": "separate admission/QA and authorization; not a reason to omit this recommendation"})
    return result


def _credit_sensitivity(row: dict, watch_result: dict | None, events: list) -> dict | None:
    fact = _map(_map(watch_result).get("verified_fact"))
    if fact.get("kind") != "material_credit":
        return None
    matched = [event for event in events if isinstance(event, dict) and event.get("id") == fact.get("id")]
    if len(matched) != 1:
        return None
    event = matched[0]
    lifetime = _window(row, "lifecycle")
    spend, total, amount = lifetime.get("spend"), lifetime.get("purchase_value"), event.get("value")
    if not all(_number(value) for value in (spend, total, amount)) or not spend > 0 or not 0 < amount <= total:
        return None
    return {"kind": "remove_one_verified_platform_credit_for_sensitivity_only", "source_event_id": event["id"],
            "reported_platform_purchase_value": total, "removed_platform_credit": amount,
            "sensitivity_roas_without_credit": (total - amount) / spend, "currency": event.get("currency")}


def build_plan(payload: dict, *, top: int | None = None) -> dict:
    """Project explicit assessments onto the whole expected census; never choose a disposition for paid rows."""
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be an object")
    if top is not None and (isinstance(top, bool) or not isinstance(top, int) or top < 0):
        raise ValueError("top must be a nonnegative integer")
    sweep = _unwrap(payload.get("paid_sweep"))
    try:
        from validate_decision_packet import (
            _creative_history_rows, _creative_prior_context, _validate_creative_test_basis, _validate_paid_continuation,
        )
        from creative_watch import assess_watch
    except ModuleNotFoundError:
        from scripts.validate_decision_packet import (
            _creative_history_rows, _creative_prior_context, _validate_creative_test_basis, _validate_paid_continuation,
        )
        from scripts.creative_watch import assess_watch
    scope = _map(sweep.get("scope"))
    as_of = _timestamp(scope.get("as_of"))
    if as_of is None or not all(_text(scope.get(field)) for field in SCOPE_COMPARISON):
        raise ValueError("paid_sweep.scope must supply the frozen as-of and comparison scope")
    coverage = _map(sweep.get("coverage"))
    expected, active = _list(coverage, "expected_ids"), _list(coverage, "expected_active_ids")
    if not _ids(expected) or (active and not _ids(active)) or not set(active) <= set(expected):
        raise ValueError("paid_sweep must supply unique expected and active ID sets")
    native = _index(_list(sweep, "entities"), "paid_sweep.entities")
    judgments = _index(_list(payload, "adjudications"), "adjudications")
    proposals = _index(_list(payload, "first_proposals"), "first_proposals")
    manuals = _index(_list(payload, "manual_pauses"), "manual_pauses")
    priors = {}
    for item in _list(payload, "prior_sweeps"):
        prior = _unwrap(item)
        observed = _timestamp(_map(prior.get("scope")).get("as_of"))
        if observed is None or observed >= as_of or observed in priors:
            raise ValueError("prior_sweeps requires unique strictly earlier timezone-qualified snapshots")
        priors[observed] = prior
    handoff = _map(sweep.get("decision_handoff"))
    histories = {}
    verified = {}
    remaining = {}
    for item in _list(handoff, "decisions"):
        binding = _map(_map(item).get("binding"))
        row = native.get(binding.get("ad_id"), {})
        if _bound(binding, row):
            histories[row["ad_id"]] = item
    for item in _list(handoff, "remaining_proposals"):
        proposal = _map(_map(item).get("proposal"))
        row = native.get(proposal.get("ad_id"), {})
        if _bound(proposal, row) and proposal.get("action") == "pause":
            remaining[row["ad_id"]] = item
    for item in _list(handoff, "applications"):
        record = _map(_map(item).get("record"))
        row = native.get(record.get("ad_id"), {})
        if _bound(record, row) and record.get("action") == "pause" and item.get("verified") is True and item.get("native_status_matches_applied") is True:
            verified[row["ad_id"]] = item

    issues = []
    history_errors: list[str] = []
    frozen_history = _creative_history_rows(payload.get("creative_history"), scope, as_of, history_errors)
    issues.extend({"reason": issue} for issue in history_errors)
    packet_evidence_ids = set(payload["evidence_ids"]) if _ids(payload.get("evidence_ids")) else set()
    events = _list(sweep, "creative_evidence_events")
    if sweep.get("complete_for_decision") is not True:
        issues.append({"reason": "paid_sweep_incomplete"})
    if handoff and handoff.get("complete_for_decision") is not True:
        issues.append({"reason": "decision_handoff_incomplete"})
    elif not handoff:
        issues.append({"reason": "decision_handoff_required"})
    if sweep.get("audit_ready") is False:
        issues.append({"reason": "paid_sweep_audit_ready_false"})
    if set(expected) != set(native) or set(active) != {key for key, row in native.items() if row.get("disposition") == "active_decision"}:
        issues.append({"reason": "native_expected_id_mismatch"})
    for collection, label in ((judgments, "adjudications"), (proposals, "first_proposals"), (manuals, "manual_pauses")):
        for ad_id in sorted(set(collection) - set(expected)):
            issues.append({"ad_id": ad_id, "reason": f"unexpected_{label}_id"})

    views = {}
    for item in _list(payload, "decision_views"):
        item = _map(item)
        ad_id = item.get("ad_id")
        row = native.get(ad_id, {}) if _text(ad_id) else {}
        if (not _bound(item, row) or _timestamp(item.get("observed_at")) != as_of
                or item.get("platform_snapshot_source") != _window(row, "lifecycle").get("source")
                or not _text(item.get("platform_snapshot_source")) or not _text(item.get("reviewer"))
                or not _text(item.get("rationale")) or item.get("disposition") not in ("cut_candidate", "watch")):
            issues.append({"ad_id": ad_id, "reason": "decision_view_not_same_bound_frozen_snapshot"})
            continue
        group = views.setdefault(ad_id, [])
        if any(other["reviewer"] == item["reviewer"] for other in group):
            issues.append({"ad_id": ad_id, "reason": "duplicate_decision_view_reviewer"})
            continue
        if group and item.get("merchant_snapshot_source") != group[0].get("merchant_snapshot_source"):
            issues.append({"ad_id": ad_id, "reason": "decision_view_merchant_scope_mismatch"})
            continue
        group.append(item)

    projected = []
    packet_rows = []
    cuts = []
    for ad_id in sorted(expected):
        row, judgment = native.get(ad_id, {}), judgments.get(ad_id, {})
        history = histories.get(ad_id, {})
        reason = judgment.get("rationale")
        chosen = judgment.get("disposition")
        delivery = row.get("current_paid_delivery")
        manual = _manual_pause(manuals.get(ad_id), row, as_of)
        paid = delivery is True
        retained = history.get("main_retained") is True
        group = views.get(ad_id, [])
        row_issues = []
        watch_result = None
        if not row or (ad_id in active and (row.get("binding_verified") is not True or row.get("coverage_state") not in {"observed", "sparse_no_delivery"} or not isinstance(delivery, bool))):
            row_issues.append("native_delivery_or_binding_unresolved")
        if judgment and (not _bound(judgment, row) or not _text(judgment.get("source"))
                         or _timestamp(judgment.get("observed_at")) != as_of):
            row_issues.append("adjudication_not_bound_to_current_id_epoch_and_asof")
        if ad_id in manuals and not manual:
            row_issues.append("manual_pause_not_independently_verified")
        decision = None
        if ad_id not in active and row.get("disposition") == "historical" and not row_issues:
            disposition = "manual_paused" if manual else "historical"
            if judgment and chosen != disposition:
                row_issues.append("historical_or_manual_paused_cannot_receive_active_disposition")
        elif not row_issues and ad_id in active and delivery is False and not judgment:
            disposition = "zero_exposure"
            row_issues.append("zero_exposure_requires_sourced_packet_projection")
        elif not row_issues and judgment and isinstance(chosen, str) and chosen in CHOICES:
            disposition = chosen
            if not _text(reason) or not _ids(judgment.get("evidence_ids")):
                row_issues.append("adjudication_requires_rationale_and_packet_evidence_ids")
            review = judgment.get("performance_review")
            if paid:
                if judgment.get("cut_assessed") is not True:
                    row_issues.append("own_performance_cut_assessment_required")
                row_issues.extend(validate_performance_review(review, row))
                if _map(review).get("assessment") == "unresolved":
                    row_issues.append("own_performance_assessment_unresolved")
            if disposition == "unresolved":
                row_issues.append("explicitly_unresolved")
            if disposition == "main_retained" and not retained:
                row_issues.append("main_retention_not_exactly_verified")
            if disposition == "cut_candidate" and retained:
                row_issues.append("main_retention_conflict_requires_separate_owner_review")
            if disposition == "cut_candidate":
                action = _map(judgment.get("action_review"))
                basis = _map(action.get("creative_test_basis"))
                next_read = _timestamp(action.get("next_read_at"))
                if (not all(_text(action.get(key)) for key in ("rationale", "parent_effect", "counterevidence"))
                        or next_read is None or next_read <= as_of or not _ids(basis.get("evidence_ids"))
                        or not _text(basis.get("rationale"))):
                    row_issues.append("cut_action_review_or_next_read_unresolved")
                if basis.get("kind") == "observed_ad_performance" and (not paid or _map(review).get("assessment") != "adequate"
                        or basis.get("metric_window") != _map(review).get("window")):
                    row_issues.append("cut_requires_adequate_own_observed_opportunity")
                if basis.get("kind") not in ("observed_ad_performance", "observed_post_rotation", "verified_independent_issue"):
                    row_issues.append("cut_requires_qualified_own_performance_or_independent_issue")
                _validate_creative_test_basis(basis, row, native, handoff.get("applications"), scope, as_of,
                                              packet_evidence_ids, "cut_action_review.creative_test_basis", row_issues, events=events)
                decision = {"disposition": "rotate" if judgment.get("packet_direction") == "rotate" else "reduce", "action_review": action}
            elif disposition in {"watch", "low_opportunity", "main_retained"} and paid:
                continuation = deepcopy(_map(judgment.get("continuation")))
                if disposition == "low_opportunity" and _map(review).get("assessment") != "limited":
                    row_issues.append("paid_low_opportunity_requires_limited_evidence_assessment")
                frozen = frozen_history.get(ad_id, {})
                prior_context = _creative_prior_context(frozen, history, row, "WATCH history", row_issues)
                if (frozen and continuation.get("change_kind") == "first_read") or (
                    not frozen and continuation.get("change_kind") != "first_read" and not retained
                ):
                    row_issues.append("watch_comparison_requires_same_frozen_prior")
                contract = _map(continuation.get("watch_contract"))
                watch_result = assess_watch(contract, row, scope, history=prior_context,
                                            events=events)
                if watch_result.get("ok") is not True:
                    row_issues.extend(watch_result.get("errors") or ["watch_contract_unresolved"])
                state = watch_result.get("prior_trigger_state") if watch_result.get("prior_watch") else watch_result.get("trigger_state")
                trigger = deepcopy(_map(continuation.get("trigger")))
                if "state" in trigger and trigger["state"] != state:
                    row_issues.append("watch_trigger_must_match_derived_observation")
                trigger["state"] = state
                continuation["trigger"] = trigger
                if "next_read_at" in continuation and _timestamp(continuation["next_read_at"]) != _timestamp(contract.get("due_at")):
                    row_issues.append("watch_due_at_must_match_next_read_at")
                continuation["next_read_at"] = contract.get("due_at")
                _validate_paid_continuation(continuation, _window(row, "lifecycle"), as_of, "WATCH continuation",
                                            packet_evidence_ids, row_issues, {**scope, "start_date": row.get("lifecycle_start")},
                                            row.get("epoch_id"), history)
                decision = {"disposition": "continue", "continuation": continuation}
            elif delivery is False and disposition in {"zero_exposure", "low_opportunity", "main_retained"}:
                decision = {"disposition": "no_paid_delivery"}
            else:
                row_issues.append("disposition_does_not_match_native_delivery_state")
        else:
            disposition = "unresolved"
            if not row_issues:
                row_issues.append("missing_explicit_adjudication" if not judgment else "invalid_adjudication_disposition")

        if len({item["disposition"] for item in group}) > 1:
            row_issues.append("same_snapshot_reviewer_disagreement_requires_resolution")
        awaiting = remaining.get(ad_id, {}).get("remaining_reason") == "awaiting_approval"
        if awaiting and (decision is None or decision["disposition"] not in {"reduce", "rotate"}):
            row_issues.append("awaiting_approval_proposal_missing_current_cut_review")
        proposal = _map(remaining.get(ad_id, {}).get("proposal"))
        wait = _first_proposal_wait(proposals.get(ad_id), row, scope, as_of, priors, proposal) if awaiting or ad_id in proposals else None
        if awaiting and (wait is None or wait["state"] != "observed_delta"):
            row_issues.append("first_proposal_exposure_unresolved")
        if row_issues:
            if disposition != "zero_exposure" or row_issues != ["zero_exposure_requires_sourced_packet_projection"]:
                disposition = "unresolved"
            issues.extend({"ad_id": ad_id, "reason": issue} for issue in row_issues)
        if disposition == "cut_candidate":
            cuts.append(ad_id)
        if decision is not None and not row_issues:
            packet_rows.append({"entity_id": ad_id, "binding_epoch": row.get("epoch_id"), "observed_paid_delivery": delivery,
                                "evidence_ids": judgment["evidence_ids"], **decision,
                                **({"performance_review": judgment["performance_review"]} if paid else {})})
        merchant_evidence = judgment.get("merchant_evidence")
        projected.append({"ad_id": ad_id, **{key: row.get(key) for key in BINDING if key != "ad_id"}, "disposition": disposition,
                          "requested_disposition": chosen, "proposal_status": _proposal_status(ad_id, remaining, verified, manual),
                          "configured_status": row.get("configured_status"), "effective_status": row.get("effective_status"),
                          "observed_paid_delivery": delivery, "rationale": reason, "performance_review": judgment.get("performance_review"),
                          "watch_evaluation": watch_result, "same_snapshot_views": group, "first_proposal_exposure": wait,
                          "merchant_evidence": merchant_evidence, "metrics": row.get("metrics"),
                          "platform_credit_sensitivity": _credit_sensitivity(row, watch_result, events),
                          "ad_day_observations": row.get("ad_day_observations"),
                          "epoch_boundary_day_excluded": row.get("epoch_boundary_day_excluded"), "issues": row_issues})

    ranked = [row for row in projected if row["ad_id"] in active and row["observed_paid_delivery"] is True
              and _number(_window(native[row["ad_id"]], "lifecycle").get("purchases"))]
    zero = [row for row in ranked if _window(row, "lifecycle")["purchases"] == 0]
    positive = [row for row in ranked if _window(row, "lifecycle")["purchases"] > 0]

    def order(records: list, *fields: tuple[str, str]) -> list:
        def descending(row: dict, window: str, field: str) -> float:
            value = _window(row, window).get(field)
            return -value if _number(value) else math.inf

        return [row["ad_id"] for row in sorted(records, key=lambda row: (
            *(descending(row, window, field) for window, field in fields), row["ad_id"]
        ))]

    lanes = {"zero_purchase_by_recent_and_lifecycle_spend": order(zero, ("last_3_closed", "spend"), ("lifecycle", "spend")),
             "positive_purchase_by_post_credit_and_recent_spend": order(positive, ("lifecycle", "spend_after_last_purchase_report_date"),
                                                                        ("last_3_closed", "spend"), ("lifecycle", "cpa")),
             "positive_purchase_by_lifecycle_cpa": order(positive, ("lifecycle", "cpa"))}
    evidence_ids = payload.get("evidence_ids")
    complete = not issues
    eligible = complete and _ids(evidence_ids) and set(active) == {item["entity_id"] for item in packet_rows}
    return {"command": "creative-review-plan", "scope": scope, "complete_for_decision": complete, "packet_eligible": eligible,
            "execution_authority": "not_granted_by_plan", "entities": projected, "candidate_lanes": lanes, "issues": issues,
            "parent_effects": _batch_effects(native, cuts, inventory_complete=sweep.get("complete_for_decision") is True
                                             and set(expected) == set(native)), "cut_recommendation_ids": sorted(cuts),
            "paid_audit": {"as_of": scope["as_of"], "campaign_id": scope["campaign_id"], "coverage_mode": "full_sweep",
                           "decision_context": "creative_test", "complete_for_decision": True, "evidence_ids": evidence_ids,
                           "decisions": packet_rows} if eligible else None,
            "summary": {"counts": dict(sorted(Counter(row["disposition"] for row in projected).items())),
                        "top": {name: ids[:top] for name, ids in lanes.items()}},
            "interpretation_limits": ["Review ordering is descriptive, never a cutoff, action, or authority.",
                                      "Platform and merchant evidence are separate; no deduplication or causal claim is implied.",
                                      "Packet eligibility means a projection is available; use the strict validator with the original sweep before relying on it."]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON input file, or - for stdin")
    parser.add_argument("--top", type=int, help="Summary limit; full lanes and ledger are never truncated")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        result = build_plan(json.loads(raw), top=args.top)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OSError) as error:
        parser.exit(2, f"creative_review_plan: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
