#!/usr/bin/env python3
"""Validate the structural and semantic safety of a media decision packet.

The validator uses only the Python standard library. The bundled JSON Schema is
the human/tooling contract; this script enforces the decision-critical subset
plus cross-field rules that JSON Schema alone does not express clearly.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


LABELS = {"verified_fact", "derived_metric", "inference", "practitioner_heuristic", "assumption", "unknown"}
DECISIONS = {"act", "test", "hold", "monitor", "revert"}
OPERATING_CLASSES = {"read_only", "prepare", "execute", "monitor"}
RECONCILIATION = {"reconciled", "partially_reconciled", "unreconciled", "unavailable", "not_applicable"}
EXECUTION_STATES = {"validated_only", "accepted", "applied", "delivering", "outcome_measured", "commercially_validated", "partial_failure", "readback_mismatch", "unknown"}
THRESHOLD_ORIGINS = {"business_derived", "account_derived", "design_derived", "runtime_platform_derived", "proposed_governance"}
THRESHOLD_APPROVAL_STATES = {"approved", "proposed", "not_required", "unknown"}
CAPABILITY_MUTABILITY = {"read", "write", "mixed_dispatcher", "unknown"}
SCHEMA_VERSION = "1.4"
SUPPORTED_SCHEMA_VERSIONS = {"1.2", "1.3", SCHEMA_VERSION}
DIRECTIONAL_SCHEMA_VERSIONS = {"1.3", SCHEMA_VERSION}
EXPOSURE_DIRECTIONS = {"increase", "reduce", "rotate", "continue", "none"}
CLAIM_TYPES = {"operational", "descriptive", "profitability", "superiority", "inferiority", "causal"}
CONTINUATION_FIELDS = (
    "since_previous_review", "last_outcomes", "exposure_context",
    "cost_of_waiting", "cost_of_stopping", "next_information",
    "continuation_rationale", "next_review", "decision_trigger", "trigger_response",
)
PAID_DISPOSITIONS = {"continue", "reduce", "rotate", "no_paid_delivery", "unknown"}
CONTINUATION_BASES = {"economic_case", "test_information", "binding_or_lag", "approved_retention"}
LEDGER_FIELDS = ("spend", "platform_outcomes", "merchant_outcomes")
COMPARISON_FIELDS = ("currency", "timezone", "attribution", "report_time", "start_date")
ACTIVE_DELIVERY_STATUSES = {"ACTIVE", "ENABLED", "DELIVERING"}
CREATIVE_TEST_WINDOWS = {"lifecycle", "last_3_closed", "last_7_closed"}
CREATIVE_TEST_ISSUES = {"policy", "destination", "measurement", "owner_guardrail"}
_NO_SWEEP = object()


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_choice(value: Any, choices: set[str]) -> bool:
    return isinstance(value, str) and value in choices


def _is_finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _numbers_close(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)


def _require_object(parent: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def _require_list(parent: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return []
    return value


def _required_fields(obj: dict[str, Any], fields: list[str], prefix: str, errors: list[str]) -> None:
    for field in fields:
        if field not in obj:
            errors.append(f"{prefix}.{field} is required")


def _source_ids(obj: dict[str, Any], prefix: str, evidence_ids: set[str], errors: list[str], field: str = "source_ids") -> None:
    source_ids = obj.get(field)
    if not isinstance(source_ids, list) or not source_ids:
        errors.append(f"{prefix}.{field} must be a non-empty array of evidence IDs")
    elif any(not _is_nonempty_string(item) or item not in evidence_ids for item in source_ids):
        errors.append(f"{prefix}.{field} must reference existing evidence IDs")


def _normal_text(value: Any) -> str:
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def _aware_datetime(value: Any) -> datetime | None:
    if not _is_nonempty_string(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def _validate_directional_contract(
    plan: dict[str, Any], decision: dict[str, Any], evidence_ids: set[str], errors: list[str], executing: bool,
    structured_continuation: bool = False,
) -> None:
    """Validate an explicit decision, not silently infer a media action from metrics."""
    direction = plan.get("exposure_direction")
    claim_type = decision.get("claim_type")
    if not _is_choice(direction, EXPOSURE_DIRECTIONS):
        errors.append(f"plan.exposure_direction must be one of {sorted(EXPOSURE_DIRECTIONS)}")
    if not _is_choice(claim_type, CLAIM_TYPES):
        errors.append(f"decision.claim_type must be one of {sorted(CLAIM_TYPES)}")
    if claim_type == "causal" and decision.get("causal_claim") is not True:
        errors.append("decision.claim_type causal requires causal_claim true")
    basis = plan.get("decision_basis")
    if not isinstance(basis, dict):
        errors.append("plan.decision_basis must be an object")
    else:
        if not _is_choice(basis.get("kind"), {"qualitative_risk", "economics", "experiment", "diagnostic"}):
            errors.append("plan.decision_basis.kind is invalid")
        if not _is_nonempty_string(basis.get("rationale")):
            errors.append("plan.decision_basis.rationale must be a non-empty string")
        _source_ids(basis, "plan.decision_basis", evidence_ids, errors)
        if not isinstance(basis.get("counterevidence"), list) or any(
            not _is_nonempty_string(item) for item in basis.get("counterevidence", [])
        ):
            errors.append("plan.decision_basis.counterevidence must be an array of non-empty strings")
    if _is_choice(direction, {"increase", "reduce", "rotate"}) and plan.get("money_moving") is not True:
        errors.append("delivery-changing exposure_direction requires money_moving true")
    if _is_choice(direction, {"continue", "none"}) and plan.get("money_moving") is True:
        errors.append("continue/none cannot conceal a money-moving change; split the scoped decisions")
    if _is_choice(claim_type, {"superiority", "inferiority"}):
        sufficiency = decision.get("claim_sufficiency")
        if not isinstance(sufficiency, dict):
            errors.append("superiority/inferiority claim requires claim_sufficiency")
        else:
            if not _is_nonempty_string(sufficiency.get("method")) or sufficiency.get("result") != "supported":
                errors.append("claim_sufficiency requires a named method with supported result")
            _source_ids(sufficiency, "decision.claim_sufficiency", evidence_ids, errors)
    gates = plan.get("unresolved_gates")
    if not isinstance(gates, list):
        errors.append("plan.unresolved_gates must be an array (empty when no gate remains)")
    else:
        for index, gate in enumerate(gates):
            prefix = f"plan.unresolved_gates[{index}]"
            if not isinstance(gate, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for field in ("reason", "scope"):
                if not _is_nonempty_string(gate.get(field)):
                    errors.append(f"{prefix}.{field} must be a non-empty string")
            for field, allowed in (("blocked_directions", EXPOSURE_DIRECTIONS), ("blocked_claims", CLAIM_TYPES)):
                items = gate.get(field)
                if not isinstance(items, list) or any(not isinstance(item, str) or item not in allowed for item in items):
                    errors.append(f"{prefix}.{field} must be an array of valid values")
            blocked_directions = gate.get("blocked_directions")
            blocked_claims = gate.get("blocked_claims")
            blocked = (
                isinstance(blocked_directions, list) and direction in blocked_directions
            ) or (isinstance(blocked_claims, list) and claim_type in blocked_claims)
            if blocked:
                if executing or decision.get("state") in {"act", "test", "revert", "monitor"}:
                    errors.append(f"{prefix} blocks this decision; use hold/prepared-under-hold until the relevant gate closes")
    if (direction == "continue" and not structured_continuation) or "continuation" in plan:
        continuation = plan.get("continuation")
        if not isinstance(continuation, dict):
            errors.append("paid continuation requires plan.continuation")
        else:
            for field in CONTINUATION_FIELDS:
                if not _is_nonempty_string(continuation.get(field)):
                    errors.append(f"plan.continuation.{field} must be a non-empty string")
            texts = [_normal_text(continuation.get(field)) for field in CONTINUATION_FIELDS]
            if all(texts) and len(set(texts)) == 1:
                errors.append("plan.continuation cannot repeat the same placeholder in every field")


def _ledger_row(value: Any, prefix: str, errors: list[str], *, signed: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be an object")
        return {}
    for field in LEDGER_FIELDS:
        if field not in value:
            errors.append(f"{prefix}.{field} is required (null if unknown)")
        elif value[field] is not None and (
            not _is_finite_number(value[field]) or (not signed and value[field] < 0)
        ):
            errors.append(f"{prefix}.{field} must be a finite {'signed' if signed else 'nonnegative'} number or null")
    return value


def _validate_paid_continuation(
    record: Any, lifecycle: dict[str, Any], as_of: datetime, prefix: str,
    evidence_ids: set[str], errors: list[str], comparison_scope: dict[str, Any],
    binding_epoch: str | None, handoff_row: dict[str, Any],
) -> None:
    if not isinstance(record, dict):
        errors.append(f"{prefix} is required for active paid continuation, including HOLD")
        return
    _source_ids(record, prefix, evidence_ids, errors, "evidence_ids")
    if not _is_choice(record.get("basis"), CONTINUATION_BASES):
        errors.append(f"{prefix}.basis must be a sourced continuation basis; positive purchase alone is not a basis")
    text_fields = ("rationale", "expected_information", "cost_of_waiting", "cost_of_stopping", "exposure_context")
    texts = [_normal_text(record.get(field)) for field in text_fields]
    for field, normalized in zip(text_fields, texts):
        if not normalized:
            errors.append(f"{prefix}.{field} must be non-empty")
    if all(texts) and len(set(texts)) == 1:
        errors.append(f"{prefix} repeats one placeholder instead of separate continuation evidence")
    next_read = _aware_datetime(record.get("next_read_at"))
    if next_read is None or next_read <= as_of:
        errors.append(f"{prefix}.next_read_at must include a timezone and be later than audit as_of")
    trigger = record.get("trigger")
    if not isinstance(trigger, dict):
        errors.append(f"{prefix}.trigger is required")
        trigger = {}
    for field in ("condition", "response"):
        if not _is_nonempty_string(trigger.get(field)):
            errors.append(f"{prefix}.trigger.{field} must be non-empty")
    if not _is_choice(trigger.get("state"), {"pending", "met", "unknown"}):
        errors.append(f"{prefix}.trigger.state must be pending, met, or unknown")
    if trigger.get("state") == "met" and not _is_nonempty_string(trigger.get("reassessment")):
        errors.append(f"{prefix}.trigger.reassessment must resolve a met trigger before renewing continuation")

    current = _ledger_row(record.get("current"), f"{prefix}.current", errors)
    for field, sweep_field in (("spend", "spend"), ("platform_outcomes", "purchases")):
        observed = lifecycle.get(sweep_field)
        declared = current.get(field)
        if observed is None and declared is None:
            continue
        if not (_is_finite_number(observed) and _is_finite_number(declared) and _numbers_close(observed, declared)):
            errors.append(f"{prefix}.current.{field} does not match the supplied paid-sweep lifecycle")

    prior = record.get("prior")
    increment = record.get("increment")
    change_kind = record.get("change_kind")
    handoff_prior = handoff_row.get("prior")
    rebind = handoff_row.get("rebind")
    carried_prior = isinstance(rebind, dict) and rebind.get("disposition") == "carry" and rebind.get("to_epoch_id") == binding_epoch
    bound_prior = (
        isinstance(handoff_prior, dict)
        and _is_nonempty_string(binding_epoch)
        and (handoff_prior.get("epoch_id") == binding_epoch or carried_prior)
    )
    handoff_observation = handoff_row.get("observation")
    handoff_observation = handoff_observation if isinstance(handoff_observation, dict) else {}
    if not _is_choice(change_kind, {"first_read", "new_information", "unchanged", "attribution_revision"}):
        errors.append(f"{prefix}.change_kind is invalid")
    if "prior" not in record or "increment" not in record:
        errors.append(f"{prefix}.prior and increment are required (null only for first_read)")
    if prior is None:
        if increment is not None or change_kind != "first_read":
            errors.append(f"{prefix} needs a sourced prior observation and delta, or explicit first_read with null prior/increment")
        if bound_prior:
            errors.append(f"{prefix} cannot claim first_read when supplied decision_handoff has a same-epoch or carried prior")
    else:
        prior = _ledger_row(prior, f"{prefix}.prior", errors)
        increment = _ledger_row(increment, f"{prefix}.increment", errors, signed=True)
        _source_ids(prior, f"{prefix}.prior", evidence_ids, errors, "evidence_ids")
        previous_read = _aware_datetime(prior.get("as_of"))
        if previous_read is None or previous_read >= as_of:
            errors.append(f"{prefix}.prior.as_of must include a timezone and precede current audit as_of")
        for field in COMPARISON_FIELDS:
            if not _is_nonempty_string(prior.get(field)):
                errors.append(f"{prefix}.prior.{field} is required to establish comparable periods")
        comparable_platform = all(
            _is_nonempty_string(prior.get(field)) and prior.get(field) == comparison_scope.get(field)
            for field in COMPARISON_FIELDS
        )
        if bound_prior:
            source = handoff_prior.get("observation")
            source = source if isinstance(source, dict) else {}
            previous_platform = source.get("meta")
            previous_merchant = source.get("merchant")
            previous_platform = previous_platform if isinstance(previous_platform, dict) else {}
            previous_merchant = previous_merchant if isinstance(previous_merchant, dict) else {}
            prior_anchor = previous_platform.get("as_of") or handoff_prior.get("as_of")
            if previous_read != _aware_datetime(prior_anchor):
                errors.append(f"{prefix}.prior.as_of does not match the same-epoch supplied decision_handoff")
            for field, ledger, key in (
                ("spend", previous_platform, "spend"),
                ("platform_outcomes", previous_platform, "purchases"),
                ("merchant_outcomes", previous_merchant, "orders"),
            ):
                observed = ledger.get(key)
                declared = prior.get(field)
                if ledger and not (
                    observed is None and declared is None
                    or _is_finite_number(observed) and _is_finite_number(declared) and _numbers_close(observed, declared)
                ):
                    errors.append(f"{prefix}.prior.{field} does not match supplied decision_handoff observation")
            if previous_platform and any(prior.get(field) != previous_platform.get(field) for field in COMPARISON_FIELDS):
                errors.append(f"{prefix}.prior comparison scope does not match supplied decision_handoff observation")
        if change_kind == "first_read":
            errors.append(f"{prefix}.change_kind cannot be first_read when a prior observation exists")
        changed = False
        for field in LEDGER_FIELDS:
            now, before, delta = current.get(field), prior.get(field), increment.get(field)
            comparison = handoff_observation.get("merchant_change" if field == "merchant_outcomes" else "meta_change")
            comparison = comparison if isinstance(comparison, dict) else {}
            incompatible = (field != "merchant_outcomes" and not comparable_platform) or (
                bound_prior and comparison.get("state") in ("not_comparable", "unknown")
            )
            if incompatible:
                if delta is not None:
                    errors.append(f"{prefix}.increment.{field} must be null across incomparable scope or source observations")
                continue
            if _is_finite_number(now) and _is_finite_number(before):
                expected = now - before
                if not _is_finite_number(delta) or not _numbers_close(delta, expected):
                    errors.append(f"{prefix}.increment.{field} must equal current minus prior")
                if expected < 0 and not _numbers_close(expected, 0) and change_kind != "attribution_revision":
                    errors.append(f"{prefix}.increment.{field} is negative; identify and source a snapshot revision")
                if bound_prior and isinstance(comparison.get("deltas"), dict):
                    delta_key = {"spend": "spend", "platform_outcomes": "purchases", "merchant_outcomes": "orders"}[field]
                    handoff_delta = comparison["deltas"].get(delta_key)
                    if not _is_finite_number(handoff_delta) or not _numbers_close(handoff_delta, expected):
                        errors.append(f"{prefix}.increment.{field} does not match supplied decision_handoff delta")
                changed |= not _numbers_close(expected, 0)
            elif delta is not None:
                errors.append(f"{prefix}.increment.{field} must be null when either source value is unknown")
        if change_kind == "unchanged" and changed:
            errors.append(f"{prefix}.change_kind unchanged conflicts with the ledger delta")
        if change_kind == "attribution_revision" and not _is_nonempty_string(record.get("revision_explanation")):
            errors.append(f"{prefix}.revision_explanation is required for attribution_revision")
        previous_rationale = _normal_text(prior.get("rationale"))
        previous_next = _aware_datetime(prior.get("next_read_at"))
        if {"rationale", "next_read_at"} & prior.keys() and (not previous_rationale or previous_next is None):
            errors.append(f"{prefix}.prior.rationale and timezone-qualified next_read_at must travel together")
        if previous_read and previous_next and previous_next <= previous_read:
            errors.append(f"{prefix}.prior.next_read_at must be later than prior.as_of")
        if previous_rationale and previous_next and previous_rationale == _normal_text(record.get("rationale")):
            if trigger.get("state") == "met" or as_of >= previous_next or (next_read and next_read > previous_next):
                errors.append(f"{prefix} cannot renew an unchanged prior continuation rationale; resolve and reassess it")
        if bound_prior and _normal_text(handoff_prior.get("reason")) == _normal_text(record.get("rationale")):
            prior_review = handoff_prior.get("next_review")
            due = _aware_datetime(prior_review.get("at")) if isinstance(prior_review, dict) else None
            if due is not None and (as_of >= due or (next_read and next_read > due) or trigger.get("state") == "met"):
                errors.append(f"{prefix} cannot renew the same continuation reason from decision_handoff")
    if current.get("merchant_outcomes") is not None or (
        isinstance(prior, dict) and prior.get("merchant_outcomes") is not None
    ):
        _source_ids(record, prefix, evidence_ids, errors, "merchant_evidence_ids")


def _account_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if value == parsed.isoformat() else None


def _creative_history_rows(history: Any, scope: dict, as_of: datetime, errors: list[str]) -> dict:
    """Bind a separately supplied past packet to its own native snapshot, not text in this packet."""
    if history is None:
        return {}
    if not isinstance(history, dict):
        errors.append("creative history must contain its frozen packet and paid sweep")
        return {}
    packet, sweep = history.get("packet"), history.get("sweep")
    if isinstance(sweep, dict) and sweep.get("ok") is True:
        sweep = sweep.get("result")
    audit = packet.get("paid_audit") if isinstance(packet, dict) else None
    prior_scope = sweep.get("scope") if isinstance(sweep, dict) else None
    if not isinstance(audit, dict) or not isinstance(prior_scope, dict) or sweep.get("command") != "paid-sweep":
        errors.append("creative history requires the prior paid decision packet and its independent paid-sweep artifact")
        return {}
    earlier = _aware_datetime(prior_scope.get("as_of"))
    created = _aware_datetime(packet.get("created_at"))
    if (earlier is None or earlier >= as_of or _aware_datetime(audit.get("as_of")) != earlier
            or created is None or not earlier <= created <= as_of
            or audit.get("campaign_id") != scope.get("campaign_id")
            or any(prior_scope.get(k) != scope.get(k) for k in ("platform", "account_id", "campaign_id", "currency", "timezone", "attribution", "report_time"))):
        errors.append("creative history must be earlier and comparable on account, campaign, currency, time zone, attribution and report time")
        return {}
    coverage = sweep.get("coverage")
    inventory = coverage.get("inventory_manifest") if isinstance(coverage, dict) else None
    retrieved = _aware_datetime(inventory.get("retrieved_at")) if isinstance(inventory, dict) else None
    if (retrieved is None or retrieved > earlier or inventory.get("independent") is not True
            or inventory.get("complete") is not True or inventory.get("pagination_complete") is not True
            or not _is_nonempty_string(inventory.get("source_id"))):
        errors.append("creative history requires complete independent native inventory at its own as-of")
        return {}
    rows, decisions = sweep.get("entities"), audit.get("decisions")
    if not isinstance(rows, list) or not isinstance(decisions, list):
        errors.append("creative history needs the prior native rows and decision records")
        return {}
    native, paired = {}, {}
    for row in rows:
        if isinstance(row, dict) and _is_nonempty_string(row.get("ad_id")):
            if row["ad_id"] in native:
                errors.append("creative history contains duplicate native IDs")
            native[row["ad_id"]] = row
    for item in decisions:
        if not isinstance(item, dict) or not _is_nonempty_string(item.get("entity_id")):
            errors.append("creative history contains a decision with no exact ad ID")
            continue
        key = item["entity_id"]
        row = native.get(key, {})
        if (key in paired or not _is_nonempty_string(row.get("epoch_id")) or row.get("binding_verified") is not True
                or item.get("binding_epoch") != row["epoch_id"]
                or not _is_choice(item.get("disposition"), PAID_DISPOSITIONS)
                or any(row.get(k) != prior_scope.get(k) for k in ("account_id", "campaign_id"))):
            errors.append(f"creative history row {key} does not bind uniquely to its frozen verified native epoch")
            continue
        paired[key] = {"record": item, "row": row, "scope": prior_scope}
    return paired


def _creative_prior_context(frozen: dict, handoff_row: dict, row: dict, prefix: str, errors: list[str]) -> dict:
    """Prefer the saved decision contract; never accept a rewritten prior condition."""
    prior = handoff_row.get("prior")
    history = {"main_retained": handoff_row.get("main_retained") is True}
    if not frozen:
        if isinstance(prior, dict):
            errors.append(f"{prefix} requires separate --creative-history for a recurring paid creative WATCH")
        return history
    previous, prior_row, prior_scope = (frozen[k] for k in ("record", "row", "scope"))
    if (prior_row.get("parent_id") != row.get("parent_id")
            or prior_row.get("lifecycle_start") != row.get("lifecycle_start")):
        errors.append(f"{prefix} prior native parent/lifecycle does not match current binding")
        return history
    if prior_row.get("epoch_id") != row.get("epoch_id"):
        rebind = handoff_row.get("rebind")
        if (not isinstance(rebind, dict) or rebind.get("epoch_id") != prior_row.get("epoch_id")
                or rebind.get("to_epoch_id") != row.get("epoch_id")):
            errors.append(f"{prefix} prior epoch differs; require a verified handoff rebind, not a new first read")
        else:
            history["verified_rebind"] = True
        # Never use old-treatment metrics as a clean current-treatment observation.
    if isinstance(prior, dict) and _aware_datetime(prior.get("as_of")) != _aware_datetime(prior_scope.get("as_of")):
        errors.append(f"{prefix} frozen history is not the preceding handoff decision")
    prior_continuation = previous.get("continuation")
    prior_continuation = prior_continuation if isinstance(prior_continuation, dict) else {}
    metrics = prior_row.get("metrics")
    prior_metrics = metrics.get("lifecycle") if isinstance(metrics, dict) else None
    prior_metrics = prior_metrics if isinstance(prior_metrics, dict) else {}
    history.update(prior_row=prior_row, prior_disposition=previous.get("disposition"), prior={
        **(prior if isinstance(prior, dict) else {}), "as_of": prior_scope["as_of"],
        **{key: prior_row.get(key) for key in ("account_id", "campaign_id", "parent_id", "ad_id", "epoch_id")},
        "next_review": {"at": prior_continuation.get("next_read_at")},
        "watch": prior_continuation.get("watch_contract"),
        "observation": {
            **(prior["observation"] if isinstance(prior, dict) and isinstance(prior.get("observation"), dict) else {}),
            "meta": {**prior_metrics, **prior_scope, "start_date": prior_metrics.get("start_date") or prior_row.get("lifecycle_start")},
        },
    })
    return history


def _validate_creative_test_basis(
    basis: Any, row: dict[str, Any], rows: dict[str, dict[str, Any]], applications: Any,
    scope: dict[str, Any], as_of: datetime, evidence_ids: set[str], prefix: str, errors: list[str], *, events: list,
) -> None:
    if not isinstance(basis, dict):
        errors.append(f"{prefix} is required: a potential sibling allocation is a monitoring item, not a cut basis")
        return
    _source_ids(basis, prefix, evidence_ids, errors, "evidence_ids")
    if not _is_nonempty_string(basis.get("rationale")):
        errors.append(f"{prefix}.rationale must explain why this target's observed opportunity or independent issue warrants action")
    kind = basis.get("kind")
    if kind == "verified_independent_issue":
        if not _is_choice(basis.get("issue_type"), CREATIVE_TEST_ISSUES):
            errors.append(f"{prefix}.issue_type must be a verified policy, destination, measurement, or owner_guardrail issue")
        matched = [event for event in events if isinstance(event, dict)
                   and _is_nonempty_string(basis.get("event_id")) and event.get("id") == basis["event_id"]]
        event = matched[0] if len(matched) == 1 else {}
        observed_at = _aware_datetime(event.get("observed_at"))
        occurred_at = _aware_datetime(event.get("occurred_at"))
        if (not event or event.get("verified") is not True or event.get("state") != "confirmed"
                or event.get("event_type") != basis.get("issue_type") or not _is_nonempty_string(event.get("source"))
                or occurred_at is None or observed_at is None or not occurred_at <= observed_at <= as_of
                or any(event.get(k) != row.get(k) for k in ("account_id", "campaign_id", "parent_id", "ad_id", "epoch_id"))):
            errors.append(f"{prefix} requires an independently sourced confirmed issue event bound to this target and as-of; a hypothesis is not a blocker")
        return
    if kind == "observed_ad_performance":
        window = basis.get("metric_window")
        metrics = row.get("metrics")
        observed = metrics.get(window) if isinstance(metrics, dict) and _is_choice(window, CREATIVE_TEST_WINDOWS) else None
        spend = observed.get("spend") if isinstance(observed, dict) else None
        if row.get("current_paid_delivery") is not True or not _is_finite_number(spend) or spend <= 0:
            errors.append(f"{prefix}.metric_window must identify a qualified sweep window with this ad's own positive observed spend")
        return
    if kind != "observed_post_rotation":
        errors.append(f"{prefix}.kind must be observed_ad_performance, observed_post_rotation, or verified_independent_issue")
        return

    anchor_id = basis.get("anchor_ad_id")
    anchor = rows.get(anchor_id) if _is_nonempty_string(anchor_id) else None
    start, end = (_account_date(basis.get(field)) for field in ("window_start", "window_end"))
    try:
        tz = ZoneInfo(scope.get("timezone"))
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        errors.append(f"{prefix} requires a valid IANA paid-sweep timezone for the post-rotation window")
        return
    if not anchor or anchor_id == row.get("ad_id") or not _is_nonempty_string(row.get("parent_id")) or any(
        anchor.get(field) != row.get(field) for field in ("account_id", "campaign_id", "parent_id")
    ):
        errors.append(f"{prefix}.anchor_ad_id must bind a different ad in the same native parent")
        return
    verified_reads = []
    for item in applications if isinstance(applications, list) else []:
        if not isinstance(item, dict) or item.get("verified") is not True or item.get("native_status_matches_applied") is not True:
            continue
        application = item.get("record")
        if not isinstance(application, dict) or application.get("action") != "pause" or any(
            application.get(field) != anchor.get(field) for field in ("account_id", "campaign_id", "parent_id", "ad_id", "epoch_id")
        ):
            continue
        readback = application.get("readback")
        if not isinstance(readback, dict) or readback.get("independent") is not True or any(
            readback.get(field) != "PAUSED" for field in ("configured_status", "effective_status")
        ):
            continue
        read_at = _aware_datetime(readback.get("read_at"))
        if read_at is not None and read_at <= as_of:
            verified_reads.append(read_at)
    if not verified_reads:
        errors.append(f"{prefix} requires the sibling pause and its independent native read-back in the sweep handoff")
        return
    boundary = max(verified_reads).astimezone(tz).date()
    epoch_start = _aware_datetime(row.get("epoch_started_at"))
    if epoch_start is not None:
        boundary = max(boundary, epoch_start.astimezone(tz).date())
    if start is None or end is None or not boundary < start <= end < as_of.astimezone(tz).date():
        errors.append(f"{prefix} requires complete account days after the verified pause and target epoch boundary, excluding today's partial")
        return
    observations = row.get("ad_day_observations")
    if not isinstance(observations, list) or not any(
        isinstance(day, dict) and (observed_date := _account_date(day.get("date"))) is not None
        and start <= observed_date <= end and _is_finite_number(day.get("spend")) and day["spend"] > 0
        for day in observations
    ):
        errors.append(f"{prefix} requires this target's own positive observed spend in the post-rotation window")


def _validate_paid_audit(
    packet: dict[str, Any], sweep: Any, evidence_ids: set[str], errors: list[str], *, creative_test: bool = False,
    creative_history: Any = None,
) -> None:
    """Bind current paid decisions to the supplied sweep instead of trusting packet counters."""
    creative_test = creative_test or creative_history is not None
    raw = packet.get("paid_audit")
    version = packet.get("schema_version")
    plan = packet.get("plan")
    direction = plan.get("exposure_direction") if isinstance(plan, dict) else None
    if not creative_test and "paid_audit" not in packet and sweep is _NO_SWEEP and not (version == SCHEMA_VERSION and direction == "continue"):
        return
    if version != SCHEMA_VERSION or not isinstance(raw, dict):
        errors.append("a paid-sweep audit requires schema_version 1.4 and a paid_audit object")
        return
    if isinstance(sweep, dict) and sweep.get("ok") is True and isinstance(sweep.get("result"), dict):
        sweep = sweep["result"]
    if not isinstance(sweep, dict) or sweep.get("command") != "paid-sweep":
        errors.append("paid_audit requires the separately supplied paid-sweep JSON (--paid-sweep)")
        return

    audit = raw
    if "decision_context" in audit and audit["decision_context"] != "creative_test":
        errors.append("paid_audit.decision_context must be creative_test when provided")
    creative_test = creative_test or audit.get("decision_context") == "creative_test"
    _source_ids(audit, "paid_audit", evidence_ids, errors, "evidence_ids")
    as_of = _aware_datetime(audit.get("as_of"))
    sweep_scope = sweep.get("scope")
    packet_scope = packet.get("scope")
    if not isinstance(sweep_scope, dict) or not isinstance(packet_scope, dict):
        errors.append("paid_audit requires packet and paid-sweep scope objects")
        return
    if as_of is None or as_of != _aware_datetime(sweep_scope.get("as_of")):
        errors.append("paid_audit.as_of must match the timezone-qualified paid-sweep scope.as_of")
        return
    history_rows = _creative_history_rows(creative_history, sweep_scope, as_of, errors) if creative_test else {}
    events = sweep.get("creative_evidence_events", []) if creative_test else []
    if not isinstance(events, list):
        errors.append("paid-sweep creative_evidence_events must be an independently sourced list")
        events = []
    created_at = _aware_datetime(packet.get("created_at"))
    if created_at is None or created_at < as_of:
        errors.append("paid audit packet.created_at must include a timezone and cannot precede its sweep as_of")
    for field, packet_field in (("platform", "platforms"), ("account_id", "accounts")):
        wanted = sweep_scope.get(field)
        found = packet_scope.get(packet_field)
        if not _is_nonempty_string(wanted) or not isinstance(found, list) or found != [wanted]:
            errors.append(f"paid_audit packet scope.{packet_field} must match the one paid-sweep {field}")
    for field in ("currency", "timezone", "attribution", "report_time"):
        if not _is_nonempty_string(sweep_scope.get(field)) or sweep_scope.get(field) != packet_scope.get(field):
            errors.append(f"paid_audit paid-sweep scope.{field} must match packet scope")
    if not _is_nonempty_string(audit.get("campaign_id")) or audit["campaign_id"] != sweep_scope.get("campaign_id"):
        errors.append("paid_audit.campaign_id must match the supplied paid-sweep scope")

    coverage = sweep.get("coverage")
    expected = coverage.get("expected_active_ids") if isinstance(coverage, dict) else None
    if not isinstance(expected, list) or any(not _is_nonempty_string(item) for item in expected) or len(expected) != len(set(expected)):
        errors.append("paid-sweep coverage.expected_active_ids must be a unique native ID list")
        return
    inventory = coverage.get("inventory_manifest")
    if (not isinstance(inventory, dict) or inventory.get("independent") is not True
            or not _is_nonempty_string(inventory.get("source_id"))):
        errors.append("paid-sweep requires an independent native inventory manifest")
        inventory = {}
    retrieved_at = _aware_datetime(inventory.get("retrieved_at"))
    inventory_complete = (inventory.get("complete") is True and inventory.get("pagination_complete") is True
                          and retrieved_at is not None and retrieved_at <= as_of)
    entities = sweep.get("entities")
    if not isinstance(entities, list):
        errors.append("paid-sweep entities must include native active decision rows")
        return
    sweep_rows: dict[str, dict[str, Any]] = {}
    for item in entities:
        if not isinstance(item, dict) or not _is_nonempty_string(item.get("ad_id")):
            errors.append("paid-sweep contains an invalid native ad row")
            continue
        key = item["ad_id"]
        if key in sweep_rows:
            errors.append(f"paid-sweep contains a duplicate ad row: {key}")
        sweep_rows[key] = item
    active_ids = set(expected)
    active_rows = {key for key, item in sweep_rows.items() if item.get("disposition") == "active_decision"}
    handoff_rows: dict[str, dict[str, Any]] = {}
    handoff = sweep.get("decision_handoff")
    handoff_decisions = handoff.get("decisions") if isinstance(handoff, dict) else None
    if isinstance(handoff_decisions, list):
        for item in handoff_decisions:
            binding = item.get("binding") if isinstance(item, dict) else None
            if not isinstance(binding, dict) or not _is_nonempty_string(binding.get("ad_id")):
                errors.append("paid-sweep decision_handoff contains an invalid binding")
                continue
            key = binding["ad_id"]
            native_row = sweep_rows.get(key)
            if not native_row or any(
                binding.get(field) != native_row.get(field) for field in ("account_id", "campaign_id", "parent_id")
            ):
                errors.append(f"paid-sweep decision_handoff binding mismatch for {key}")
                continue
            if binding.get("epoch_id") != native_row.get("epoch_id"):
                # Old epochs remain in the handoff as history, never as a current anchor.
                prior = item.get("prior")
                if item.get("current") is not None or not isinstance(prior, dict) or any(
                    prior.get(field) != binding.get(field) for field in ("account_id", "campaign_id", "parent_id", "ad_id", "epoch_id")
                ):
                    errors.append(f"paid-sweep decision_handoff current epoch mismatch for {key}")
                continue
            if key in handoff_rows:
                errors.append(f"paid-sweep decision_handoff duplicates current binding for {key}")
            handoff_rows[key] = item
    complete = sweep.get("complete_for_decision")
    if not isinstance(complete, bool) or audit.get("complete_for_decision") is not complete:
        errors.append("paid_audit.complete_for_decision must match the supplied sweep, not a packet summary")
    if complete is True and active_rows != active_ids:
        errors.append("paid-sweep claims completeness without exact active decision ID equality")
    if complete is True and not inventory_complete:
        errors.append("paid-sweep claims completeness without a complete native inventory at as_of")

    mode = audit.get("coverage_mode")
    executing = packet.get("operating_class") == "execute"
    decision = packet.get("decision")
    decision_state = decision.get("state") if isinstance(decision, dict) else None
    execution = packet.get("execution")
    changes = execution.get("changes") if isinstance(execution, dict) else []
    changes = [item for item in changes if isinstance(item, dict)] if isinstance(changes, list) else []
    change_ad_ids = {item.get("entity_id") for item in changes if item.get("entity_type") == "ad" and _is_nonempty_string(item.get("entity_id"))}
    if mode == "full_sweep":
        required_ids = active_ids | active_rows
        history_incomplete = isinstance(handoff, dict) and handoff.get("complete_for_decision") is False
        if (complete is not True or sweep.get("audit_ready") is False or history_incomplete) and (
            executing or decision_state != "hold"
        ):
            errors.append("an incomplete paid-sweep must remain a hold; only isolated approved risk reduction may execute")
    elif mode == "isolated_risk_reduction":
        required_ids = change_ad_ids
        if not inventory_complete:
            errors.append("isolated_risk_reduction requires a complete native parent roster at as_of")
        if not executing or not _is_choice(direction, {"reduce", "rotate"}) or not required_ids or len(required_ids) != len(changes):
            errors.append("isolated_risk_reduction requires an approved execute packet scoped to exact ad-only reductions")
        if not required_ids <= active_ids:
            errors.append("isolated_risk_reduction targets must occur in the native expected active ID census")
        scoped = packet_scope.get("entities")
        if (
            not isinstance(scoped, list) or any(not _is_nonempty_string(item) for item in scoped)
            or set(scoped) != required_ids or len(scoped) != len(required_ids)
        ):
            errors.append("isolated_risk_reduction scope.entities must match all and only the changed ad IDs")
        target_parents = {
            sweep_rows[key]["parent_id"] for key in required_ids
            if key in sweep_rows and _is_nonempty_string(sweep_rows[key].get("parent_id"))
        }
        for key in sorted(active_ids | active_rows):
            sibling = sweep_rows.get(key, {})
            parent_id = sibling.get("parent_id")
            if not _is_nonempty_string(parent_id):
                errors.append(f"isolated_risk_reduction cannot resolve the native parent of active {key}")
            elif parent_id in target_parents and (
                not _is_choice(sibling.get("coverage_state"), {"observed", "sparse_no_delivery"})
                or sibling.get("binding_verified") is not True
                or not _is_choice(sibling.get("configured_status"), ACTIVE_DELIVERY_STATUSES)
                or not _is_choice(sibling.get("effective_status"), ACTIVE_DELIVERY_STATUSES)
                or not isinstance(sibling.get("current_paid_delivery"), bool)
            ):
                errors.append(f"isolated_risk_reduction cannot resolve active sibling/target {key} in selected parent {parent_id}")
    else:
        errors.append("paid_audit.coverage_mode must be full_sweep or isolated_risk_reduction")
        return

    records = audit.get("decisions")
    if not isinstance(records, list):
        errors.append("paid_audit.decisions must be an array")
        return
    decisions: dict[str, str] = {}
    for index, record in enumerate(records):
        prefix = f"paid_audit.decisions[{index}]"
        if not isinstance(record, dict) or not _is_nonempty_string(record.get("entity_id")):
            errors.append(f"{prefix}.entity_id must be a native ad ID")
            continue
        key = record["entity_id"]
        if key in decisions:
            errors.append(f"{prefix} duplicates native ad ID {key}")
        disposition = record.get("disposition")
        if not _is_choice(disposition, PAID_DISPOSITIONS):
            errors.append(f"{prefix}.disposition is invalid")
            continue
        decisions[key] = disposition
        _source_ids(record, prefix, evidence_ids, errors, "evidence_ids")
        row = sweep_rows.get(key, {})
        if row and any(row.get(field) != sweep_scope.get(field) for field in ("account_id", "campaign_id")):
            errors.append(f"{prefix} does not match the paid-sweep account/campaign binding")
        delivery = row.get("current_paid_delivery")
        if (delivery is not None and not isinstance(delivery, bool)) or (
            "observed_paid_delivery" not in record or record["observed_paid_delivery"] is not delivery
        ):
            errors.append(f"{prefix}.observed_paid_delivery must match paid-sweep true/false/null")
        if "binding_epoch" not in record or record["binding_epoch"] != row.get("epoch_id"):
            errors.append(f"{prefix}.binding_epoch must match the current native row (null only if unknown)")
        verified = row.get("binding_verified") is True and _is_nonempty_string(row.get("epoch_id"))
        covered = verified and _is_choice(row.get("coverage_state"), {"observed", "sparse_no_delivery"})
        if complete is True and key in required_ids and (not covered or delivery is None):
            errors.append(f"{prefix} cannot be decision-complete without covered, verified delivery and epoch")
        if delivery is True and disposition not in {"continue", "reduce", "rotate"}:
            errors.append(f"{prefix} active paid delivery requires explicit continuation or a reduction/rotation decision")
        if delivery is True and decision_state == "hold" and direction == "none":
            errors.append("paid HOLD/none cannot hide observed exposure; declare continue or a scoped reduction/rotation proposal")
        if disposition == "no_paid_delivery" and delivery is not False:
            errors.append(f"{prefix} cannot turn unknown or positive delivery into no_paid_delivery")
        if creative_test and delivery is True:
            try:
                from creative_review_plan import validate_performance_review
            except ModuleNotFoundError:
                from scripts.creative_review_plan import validate_performance_review
            performance = record.get("performance_review")
            errors.extend(f"{prefix}.performance_review: {message}" for message in validate_performance_review(performance, row))
            if isinstance(performance, dict) and performance.get("assessment") == "unresolved":
                errors.append(f"{prefix} paid risk has an unresolved decision; do not close the sweep with WATCH")
            if isinstance(performance, dict) and disposition in {"reduce", "rotate"}:
                action = record.get("action_review")
                basis = action.get("creative_test_basis") if isinstance(action, dict) else None
                if isinstance(basis, dict) and basis.get("kind") == "observed_ad_performance" and (
                    performance.get("assessment") != "adequate" or performance.get("window") != basis.get("metric_window")
                ):
                    errors.append(f"{prefix} performance CUT must use its own adequate observed basis and the same qualified window")
        if disposition == "continue":
            if delivery is not True:
                errors.append(f"{prefix} requires verified current paid delivery for a paid continue decision")
            metrics = row.get("metrics")
            lifecycle = metrics.get("lifecycle") if isinstance(metrics, dict) else None
            handoff_row = handoff_rows.get(key, {})
            history = _creative_prior_context(history_rows.get(key, {}), handoff_row, row, prefix, errors) if creative_test else {}
            anchored_handoff = {**handoff_row, "prior": history["prior"]} if "prior" in history else handoff_row
            _validate_paid_continuation(
                record.get("continuation"), lifecycle if isinstance(lifecycle, dict) else {},
                as_of, f"{prefix}.continuation", evidence_ids, errors,
                {**sweep_scope, "start_date": row.get("lifecycle_start")},
                row.get("epoch_id"), anchored_handoff,
            )
            if creative_test:
                try:
                    from creative_watch import assess_watch
                except ModuleNotFoundError:
                    from scripts.creative_watch import assess_watch
                continuation = record.get("continuation")
                continuation = continuation if isinstance(continuation, dict) else {}
                if not history_rows.get(key) and continuation.get("change_kind") != "first_read" and not history.get("main_retained"):
                    errors.append(f"{prefix} prior comparison cannot be proved without the preceding frozen creative history")
                if history_rows.get(key) and continuation.get("change_kind") == "first_read":
                    errors.append(f"{prefix} cannot erase frozen prior by declaring first_read")
                watch = continuation.get("watch_contract")
                result = assess_watch(watch, row, sweep_scope, history, events=events)
                errors.extend(f"{prefix}.continuation.watch_contract: {message}" for message in result["errors"])
                if isinstance(watch, dict) and _aware_datetime(watch.get("due_at")) != _aware_datetime(continuation.get("next_read_at")):
                    errors.append(f"{prefix}.continuation.watch_contract.due_at must match next_read_at")
                trigger = continuation.get("trigger")
                state = result.get("prior_trigger_state") if result.get("prior_watch") else result.get("trigger_state")
                if state is not None and (not isinstance(trigger, dict) or trigger.get("state") != state):
                    errors.append(f"{prefix}.continuation.trigger.state must match observed evidence ({state}), not a default")
        if disposition in {"reduce", "rotate"}:
            if not covered or row.get("disposition") != "active_decision":
                errors.append(f"{prefix} reduction/rotation requires independently covered target and current binding")
            if creative_test and (row.get("configured_status") not in ACTIVE_DELIVERY_STATUSES
                                  or row.get("effective_status") not in ACTIVE_DELIVERY_STATUSES):
                errors.append(f"{prefix} a paused or unresolved native status is not an active creative-test action target")
            review = record.get("action_review")
            if not isinstance(review, dict):
                errors.append(f"{prefix}.action_review is required for a reduction/rotation")
            else:
                for field in ("rationale", "parent_effect", "counterevidence"):
                    if not _is_nonempty_string(review.get(field)):
                        errors.append(f"{prefix}.action_review.{field} must be non-empty")
                next_read = _aware_datetime(review.get("next_read_at"))
                if next_read is None or next_read <= as_of:
                    errors.append(f"{prefix}.action_review.next_read_at must be after paid-sweep as_of")
                if creative_test or "creative_test_basis" in review:
                    _validate_creative_test_basis(
                        review.get("creative_test_basis"), row, sweep_rows,
                        handoff.get("applications") if isinstance(handoff, dict) else None,
                        sweep_scope, as_of, evidence_ids, f"{prefix}.action_review.creative_test_basis", errors,
                        events=events,
                    )
                if handoff_rows.get(key, {}).get("main_retained") is True:
                    _source_ids(review, f"{prefix}.action_review", evidence_ids, errors, "retention_override_evidence_ids")

    if set(decisions) != required_ids:
        missing = sorted(required_ids - set(decisions))
        extra = sorted(set(decisions) - required_ids)
        errors.append(f"paid_audit active decision ID coverage mismatch: missing={missing}, extra={extra}")
    remaining = handoff.get("remaining_proposals") if isinstance(handoff, dict) else None
    if creative_test and isinstance(remaining, list):
        for item in remaining:
            if not isinstance(item, dict) or item.get("remaining_reason") != "awaiting_approval":
                continue
            proposal = item.get("proposal")
            if not isinstance(proposal, dict) or proposal.get("action") != "pause":
                continue
            ad_id = proposal.get("ad_id")
            if _is_nonempty_string(ad_id) and ad_id in required_ids and decisions.get(ad_id) not in {"reduce", "rotate"}:
                errors.append(f"creative-test pause {ad_id} cannot remain awaiting approval without a current reduce/rotate decision")
    if direction == "continue" and "continue" not in decisions.values():
        errors.append("paid exposure_direction continue requires a current continuation decision")
    if executing:
        reduced = {key for key, disposition in decisions.items() if disposition in {"reduce", "rotate"}}
        if not _is_choice(direction, {"reduce", "rotate"}) or reduced != change_ad_ids:
            errors.append("paid_audit execute must bind all and only approved reduction/rotation ad changes")
        for change in changes:
            if change.get("account_id") != sweep_scope.get("account_id") or change.get("platform") != sweep_scope.get("platform"):
                errors.append("paid_audit execution changes must match the supplied paid-sweep platform and account")
            if change.get("entity_type") != "ad":
                parent = change.get("entity_id")
                children = {key for key in required_ids if sweep_rows.get(key, {}).get("parent_id") == parent}
                if mode != "full_sweep" or complete is not True or change.get("entity_type") not in {"ad_set", "ad_group"} or not children or not children <= reduced:
                    errors.append("paid_audit parent reduction requires complete coverage and all active children explicitly reduced")


def validate(packet: Any, *, paid_sweep: Any = _NO_SWEEP, creative_test: bool = False,
             creative_history: Any = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(packet, dict):
        return ["packet must be a JSON object"], []

    _required_fields(packet, ["schema_version", "created_at", "operating_class", "scope", "decision", "evidence", "metrics", "data_quality", "diagnosis", "plan", "unknowns"], "packet", errors)
    if not _is_choice(packet.get("schema_version"), SUPPORTED_SCHEMA_VERSIONS):
        errors.append(f"schema_version must be one of {sorted(SUPPORTED_SCHEMA_VERSIONS)}")
    directional = _is_choice(packet.get("schema_version"), DIRECTIONAL_SCHEMA_VERSIONS)
    audit_version = packet.get("schema_version") == SCHEMA_VERSION
    operating_class = packet.get("operating_class")
    if operating_class not in OPERATING_CLASSES:
        errors.append(f"operating_class must be one of {sorted(OPERATING_CLASSES)}")

    scope = _require_object(packet, "scope", errors)
    _required_fields(scope, ["platforms", "accounts", "markets", "currency", "timezone", "reporting_window", "business_outcome", "optimization_event", "attribution", "conversion_lag"], "scope", errors)
    for field in ("platforms", "accounts", "markets"):
        value = scope.get(field)
        if not isinstance(value, list) or not value or not all(_is_nonempty_string(item) for item in value):
            errors.append(f"scope.{field} must be a non-empty array of strings")
    for field in ("timezone", "reporting_window", "business_outcome"):
        if not _is_nonempty_string(scope.get(field)):
            errors.append(f"scope.{field} must be a non-empty string")
    for nullable_qualifier in ("currency", "optimization_event", "attribution", "conversion_lag"):
        if nullable_qualifier in scope and scope.get(nullable_qualifier) is None:
            warnings.append(f"scope.{nullable_qualifier} is unknown; state the decision impact")

    decision = _require_object(packet, "decision", errors)
    _required_fields(decision, ["state", "summary", "owner", "deadline", "confidence", "evidence_rung", "causal_claim"], "decision", errors)
    state = decision.get("state")
    if state not in DECISIONS:
        errors.append(f"decision.state must be one of {sorted(DECISIONS)}")
    if not _is_nonempty_string(decision.get("summary")):
        errors.append("decision.summary must be a non-empty string")
    if decision.get("confidence") not in {"low", "medium", "high"}:
        errors.append("decision.confidence must be low, medium, or high")
    rung = decision.get("evidence_rung")
    if isinstance(rung, bool) or not isinstance(rung, int) or not 1 <= rung <= 6:
        errors.append("decision.evidence_rung must be an integer from 1 to 6")
    if decision.get("causal_claim") is True and (not isinstance(rung, int) or rung < 3):
        errors.append("a causal claim requires evidence_rung >= 3")

    evidence = _require_list(packet, "evidence", errors)
    if not evidence:
        errors.append("evidence must contain at least one claim")
    evidence_ids: set[str] = set()
    for index, item in enumerate(evidence):
        prefix = f"evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _required_fields(item, ["id", "label", "claim", "source", "retrieved_at", "limitations"], prefix, errors)
        evidence_id = item.get("id")
        if not _is_nonempty_string(evidence_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif evidence_id in evidence_ids:
            errors.append(f"{prefix}.id duplicates {evidence_id}")
        else:
            evidence_ids.add(evidence_id)
        if item.get("label") not in LABELS:
            errors.append(f"{prefix}.label is invalid")
        for field in ("claim", "source"):
            if not _is_nonempty_string(item.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if not isinstance(item.get("limitations"), list):
            errors.append(f"{prefix}.limitations must be an array")

    metrics = _require_list(packet, "metrics", errors)
    metric_fields = ["name", "value", "unit", "source_id", "window", "timezone", "currency", "attribution", "conversion_definition", "count", "denominator", "evidence_label"]
    for index, metric in enumerate(metrics):
        prefix = f"metrics[{index}]"
        if not isinstance(metric, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _required_fields(metric, metric_fields, prefix, errors)
        for field in ("name", "unit", "source_id", "window", "timezone"):
            if not _is_nonempty_string(metric.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if metric.get("source_id") not in evidence_ids:
            errors.append(f"{prefix}.source_id must reference an evidence id")
        if metric.get("evidence_label") not in LABELS:
            errors.append(f"{prefix}.evidence_label is invalid")
        value = metric.get("value")
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{prefix}.value must be finite")
        unit = str(metric.get("unit", "")).lower()
        if any(token in unit for token in ("currency", "usd", "eur", "try", "gbp")) and not _is_nonempty_string(metric.get("currency")):
            errors.append(f"{prefix}.currency is required for monetary metrics")
        if unit in {"rate", "ratio", "percent", "%"} and metric.get("count") is None and metric.get("denominator") is None:
            warnings.append(f"{prefix} is a rate/ratio without count or denominator")

    data_quality = _require_object(packet, "data_quality", errors)
    _required_fields(data_quality, ["state", "reconciliation", "binding", "critical_issues"], "data_quality", errors)
    if data_quality.get("state") not in {"pass", "pass_with_limits", "fail"}:
        errors.append("data_quality.state is invalid")
    if data_quality.get("reconciliation") not in RECONCILIATION:
        errors.append("data_quality.reconciliation is invalid")
    if data_quality.get("binding") not in {"verified", "partial", "unverified", "not_applicable"}:
        errors.append("data_quality.binding is invalid")
    if not isinstance(data_quality.get("critical_issues"), list):
        errors.append("data_quality.critical_issues must be an array")

    capability_manifest = packet.get("capability_manifest")
    capability_modes: set[str] = set()
    capability_tools: dict[str, str] = {}
    if capability_manifest is not None:
        if not isinstance(capability_manifest, list) or not capability_manifest:
            errors.append("capability_manifest must be a non-empty array when supplied")
        else:
            seen_tools: set[str] = set()
            for index, item in enumerate(capability_manifest):
                prefix = f"capability_manifest[{index}]"
                if not isinstance(item, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                _required_fields(
                    item,
                    ["tool", "method", "mutability", "retrieved_at"],
                    prefix,
                    errors,
                )
                for field in ("tool", "method", "retrieved_at"):
                    if not _is_nonempty_string(item.get(field)):
                        errors.append(f"{prefix}.{field} must be a non-empty string")
                tool = item.get("tool")
                if _is_nonempty_string(tool):
                    if tool in seen_tools:
                        errors.append(f"{prefix}.tool duplicates {tool}")
                    seen_tools.add(tool)
                mutability = item.get("mutability")
                if mutability not in CAPABILITY_MUTABILITY:
                    errors.append(
                        f"{prefix}.mutability must be one of {sorted(CAPABILITY_MUTABILITY)}"
                    )
                else:
                    capability_modes.add(mutability)
                    if _is_nonempty_string(tool):
                        capability_tools[tool] = mutability

    diagnosis = _require_object(packet, "diagnosis", errors)
    _required_fields(diagnosis, ["observation", "leading_hypothesis", "alternatives", "confounds", "discriminator"], "diagnosis", errors)
    alternatives = diagnosis.get("alternatives")
    if not isinstance(alternatives, list) or len(alternatives) < 2:
        errors.append("diagnosis.alternatives must contain at least two competing hypotheses")
    for field in ("observation", "leading_hypothesis", "discriminator"):
        if not _is_nonempty_string(diagnosis.get(field)):
            errors.append(f"diagnosis.{field} must be a non-empty string")

    plan = _require_object(packet, "plan", errors)
    _required_fields(plan, ["action", "money_moving", "owner", "primary_metric", "guardrails", "monitoring_window", "decision_rule", "reversal_condition", "threshold_records"], "plan", errors)
    for field in ("action", "primary_metric", "monitoring_window", "decision_rule", "reversal_condition"):
        if not _is_nonempty_string(plan.get(field)):
            errors.append(f"plan.{field} must be a non-empty string")
    if not isinstance(plan.get("money_moving"), bool):
        errors.append("plan.money_moving must be boolean")
    if not isinstance(plan.get("guardrails"), list) or not plan.get("guardrails"):
        errors.append("plan.guardrails must be a non-empty array")

    threshold_records = _require_list(plan, "threshold_records", errors)
    for index, item in enumerate(threshold_records):
        prefix = f"plan.threshold_records[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        required = ["name", "rule", "origin", "source", "derivation", "scope", "approval_state", "approver"]
        _required_fields(item, required, prefix, errors)
        for field in ("name", "rule", "source", "derivation", "scope"):
            if not _is_nonempty_string(item.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if item.get("origin") not in THRESHOLD_ORIGINS:
            errors.append(f"{prefix}.origin must be one of {sorted(THRESHOLD_ORIGINS)}")
        approval_state = item.get("approval_state")
        if approval_state not in THRESHOLD_APPROVAL_STATES:
            errors.append(f"{prefix}.approval_state must be one of {sorted(THRESHOLD_APPROVAL_STATES)}")
        if approval_state == "approved" and not _is_nonempty_string(item.get("approver")):
            errors.append(f"{prefix}.approver is required when approval_state is approved")
        if (
            item.get("origin") == "proposed_governance"
            and plan.get("money_moving") is True
            and approval_state != "approved"
        ):
            errors.append(f"{prefix} cannot authorize a money-moving plan until owner approval")

    if directional:
        _validate_directional_contract(
            plan, decision, evidence_ids, errors, operating_class == "execute",
            structured_continuation=audit_version,
        )
    if not directional and plan.get("money_moving") is True and not threshold_records:
        errors.append("a money-moving plan requires at least one sourced threshold record")

    if state == "test":
        experiment = packet.get("experiment")
        if not isinstance(experiment, dict):
            errors.append("decision.state test requires experiment")
        else:
            required = ["hypothesis", "causal_rung", "arms", "assignment", "primary_metric", "guardrails", "sufficiency_method", "lag_window", "decision_rule"]
            _required_fields(experiment, required, "experiment", errors)
            if not isinstance(experiment.get("arms"), list) or len(experiment.get("arms", [])) < 2:
                errors.append("experiment.arms must contain at least two arms")

    economics = packet.get("economics")
    unsafe_reconciliation = data_quality.get("reconciliation") in {"unreconciled", "unavailable"}
    operational_reduction = (
        directional
        and _is_choice(plan.get("exposure_direction"), {"reduce", "rotate"})
        and decision.get("claim_type") == "operational"
        and isinstance(plan.get("decision_basis"), dict)
        and plan["decision_basis"].get("kind") == "qualitative_risk"
        and decision.get("causal_claim") is False
    )
    economics_required = (
        directional and (
            decision.get("claim_type") == "profitability"
            or (plan.get("exposure_direction") == "increase" and (
                state in {"act", "test", "revert"} or operating_class == "execute"
            ))
        )
    )
    if economics_required or (state == "act" and plan.get("money_moving") is True and not operational_reduction):
        if not isinstance(economics, dict):
            errors.append("money-moving act requires economics")
        elif directional:
            for field in ("acquisition_unit", "revenue_basis", "target_source", "marginal_implication"):
                if not _is_nonempty_string(economics.get(field)):
                    errors.append(f"economics.{field} must be a non-empty string")
            scenarios = economics.get("scenarios")
            if not isinstance(scenarios, list) or not scenarios or any(not isinstance(item, dict) or not item for item in scenarios):
                errors.append("economics.scenarios must contain at least one non-empty scenario object")
            if not isinstance(economics.get("capacity_constraints"), list):
                errors.append("economics.capacity_constraints must be an array")
        if directional:
            if data_quality.get("reconciliation") not in {"reconciled", "partially_reconciled"}:
                errors.append("directional increase/profitability or non-operational money-moving act requires reconciled/partially_reconciled outcomes")
            if data_quality.get("state") == "fail":
                errors.append("directional increase/profitability or non-operational money-moving act cannot proceed with failed data quality")
        else:
            if unsafe_reconciliation and not isinstance(plan.get("safety_exception"), dict):
                errors.append("money-moving act requires reconciled/partially_reconciled outcomes or a documented safety_exception")
            if data_quality.get("state") == "fail" and not isinstance(plan.get("safety_exception"), dict):
                errors.append("money-moving act cannot proceed with failed data quality without a documented safety_exception")
    if directional and operating_class == "execute":
        if data_quality.get("binding") != "verified":
            errors.append("directional execution requires verified target/delivered binding")
        if data_quality.get("state") == "fail" or data_quality.get("critical_issues"):
            errors.append("directional execution cannot proceed with critical data-quality issues")

    execution = packet.get("execution")
    if operating_class == "execute":
        if not isinstance(capability_manifest, list) or not capability_manifest:
            errors.append("operating_class execute requires capability_manifest")
        else:
            if "write" not in capability_modes:
                errors.append("execution capability_manifest requires an explicit write tool")
            if "read" not in capability_modes:
                errors.append("execution capability_manifest requires an independent read tool")
            if capability_modes & {"mixed_dispatcher", "unknown"}:
                errors.append(
                    "execution capability_manifest cannot rely on mixed_dispatcher or unknown mutability; resolve the underlying tools"
                )
        if not isinstance(execution, dict):
            errors.append("operating_class execute requires execution")
        else:
            _required_fields(execution, ["approval", "changes", "preflight", "readback", "rollback", "execution_state"], "execution", errors)
            approval = execution.get("approval")
            if not isinstance(approval, dict) or approval.get("status") != "approved":
                errors.append("execution requires explicit approved status")
            else:
                _required_fields(approval, ["status", "approved_by", "approved_at", "scope"], "execution.approval", errors)
                for field in ("approved_by", "approved_at", "scope"):
                    if not _is_nonempty_string(approval.get(field)):
                        errors.append(f"execution.approval.{field} must be a non-empty string")
            changes = execution.get("changes")
            if not isinstance(changes, list) or not changes:
                errors.append("execution.changes must be a non-empty array")
            else:
                required_change = ["platform", "account_id", "entity_type", "entity_id", "field", "current_value", "proposed_value", "absolute_delta", "percentage_delta", "financial_exposure"]
                for index, change in enumerate(changes):
                    prefix = f"execution.changes[{index}]"
                    if not isinstance(change, dict):
                        errors.append(f"{prefix} must be an object")
                        continue
                    _required_fields(change, required_change, prefix, errors)
                    for field in ("platform", "account_id", "entity_type", "entity_id", "field"):
                        if not _is_nonempty_string(change.get(field)):
                            errors.append(f"{prefix}.{field} must be a non-empty string")
                    if change.get("current_value") == change.get("proposed_value"):
                        errors.append(f"{prefix} current_value equals proposed_value")
                    current_value = change.get("current_value")
                    proposed_value = change.get("proposed_value")
                    absolute_delta = change.get("absolute_delta")
                    percentage_delta = change.get("percentage_delta")
                    current_numeric = _is_finite_number(current_value)
                    proposed_numeric = _is_finite_number(proposed_value)
                    if directional:
                        field_name = str(change.get("field", "")).strip().lower()
                        enables_delivery = "status" in field_name and str(proposed_value).strip().upper() in {"ACTIVE", "ENABLE", "ENABLED", "ON"}
                        budget_increase = "budget" in field_name and current_numeric and proposed_numeric and float(proposed_value) > float(current_value)
                        direction = plan.get("exposure_direction")
                        if (enables_delivery or budget_increase) and direction != "increase":
                            errors.append(f"{prefix} increases exposure but plan.exposure_direction is not increase")
                        if _is_choice(direction, {"reduce", "rotate"}) and not (
                            ("status" in field_name and str(proposed_value).strip().upper() in {"PAUSED", "DISABLED", "DISABLE", "OFF"})
                            or ("budget" in field_name and current_numeric and proposed_numeric and float(proposed_value) < float(current_value))
                        ):
                            errors.append(f"{prefix} is not a supported reduction/rotation field; split unrelated writes")
                        if _is_choice(direction, {"none", "continue"}) and ("status" in field_name or "budget" in field_name):
                            errors.append(f"{prefix} changes delivery; cannot use exposure_direction none/continue")
                    if current_numeric != proposed_numeric:
                        errors.append(
                            f"{prefix} current_value and proposed_value must both be numeric or both be non-numeric"
                        )
                    elif current_numeric and proposed_numeric:
                        expected_absolute = float(proposed_value) - float(current_value)
                        if not _is_finite_number(absolute_delta) or not _numbers_close(
                            float(absolute_delta), expected_absolute
                        ):
                            errors.append(
                                f"{prefix}.absolute_delta must equal proposed_value - current_value"
                            )
                        if float(current_value) == 0:
                            if percentage_delta is not None:
                                errors.append(
                                    f"{prefix}.percentage_delta must be null when current_value is zero"
                                )
                        else:
                            expected_percentage = (
                                expected_absolute / abs(float(current_value)) * 100
                            )
                            if not _is_finite_number(
                                percentage_delta
                            ) or not _numbers_close(
                                float(percentage_delta), expected_percentage
                            ):
                                errors.append(
                                    f"{prefix}.percentage_delta is inconsistent with current_value and proposed_value"
                                )
                    elif absolute_delta is not None or percentage_delta is not None:
                        errors.append(
                            f"{prefix} non-numeric changes require null absolute_delta and percentage_delta"
                        )
                    exposure = change.get("financial_exposure")
                    if not isinstance(exposure, dict):
                        errors.append(f"{prefix}.financial_exposure must be an object")
                    else:
                        _required_fields(
                            exposure,
                            [
                                "currency",
                                "model",
                                "period_count",
                                "budget_ceiling_per_period",
                                "maximum_incremental_amount",
                                "horizon",
                                "derivation",
                            ],
                            f"{prefix}.financial_exposure",
                            errors,
                        )
                        for field in ("currency", "horizon", "derivation"):
                            if not _is_nonempty_string(exposure.get(field)):
                                errors.append(
                                    f"{prefix}.financial_exposure.{field} must be a non-empty string"
                                )
                        exposure_model = exposure.get("model")
                        if directional:
                            semantics = exposure.get("amount_semantics")
                            if not _is_choice(semantics, {"nominal_reference", "verified_bound"}):
                                errors.append(f"{prefix}.financial_exposure.amount_semantics must be nominal_reference or verified_bound")
                            if semantics == "verified_bound" and not _is_nonempty_string(exposure.get("bound_evidence")):
                                errors.append(f"{prefix}.financial_exposure.verified_bound requires separate bound_evidence; budget times period is only a nominal reference")
                        if exposure_model not in {
                            "direct_amount_delta",
                            "amount_delta_times_periods",
                            "budget_ceiling_times_periods",
                            "bounded_other",
                        }:
                            errors.append(
                                f"{prefix}.financial_exposure.model is invalid"
                            )
                        exposure_amount = exposure.get(
                            "maximum_incremental_amount"
                        )
                        if not _is_finite_number(exposure_amount) or float(
                            exposure_amount
                        ) < 0:
                            errors.append(
                                f"{prefix}.financial_exposure.maximum_incremental_amount must be a finite number >= 0"
                            )
                        period_count = exposure.get("period_count")
                        if period_count is not None and (
                            not _is_finite_number(period_count)
                            or float(period_count) <= 0
                        ):
                            errors.append(
                                f"{prefix}.financial_exposure.period_count must be null or a finite number > 0"
                            )
                        budget_ceiling = exposure.get(
                            "budget_ceiling_per_period"
                        )
                        if budget_ceiling is not None and (
                            not _is_finite_number(budget_ceiling)
                            or float(budget_ceiling) < 0
                        ):
                            errors.append(
                                f"{prefix}.financial_exposure.budget_ceiling_per_period must be null or a finite number >= 0"
                            )
                        scope_currency = scope.get("currency")
                        if (
                            _is_nonempty_string(scope_currency)
                            and _is_nonempty_string(exposure.get("currency"))
                            and exposure["currency"] != scope_currency
                        ):
                            errors.append(
                                f"{prefix}.financial_exposure.currency must match scope.currency"
                            )
                        is_budget_field = _is_nonempty_string(
                            change.get("field")
                        ) and "budget" in change["field"].lower()
                        if is_budget_field and current_numeric and proposed_numeric:
                            positive_delta = max(
                                0.0,
                                float(proposed_value) - float(current_value),
                            )
                            expected_exposure: float | None = None
                            if exposure_model == "direct_amount_delta":
                                if period_count is not None:
                                    errors.append(
                                        f"{prefix}.financial_exposure.period_count must be null for direct_amount_delta"
                                    )
                                if budget_ceiling is not None:
                                    errors.append(
                                        f"{prefix}.financial_exposure.budget_ceiling_per_period must be null for direct_amount_delta"
                                    )
                                expected_exposure = positive_delta
                            elif exposure_model == "amount_delta_times_periods":
                                if period_count is None:
                                    errors.append(
                                        f"{prefix}.financial_exposure.period_count is required for amount_delta_times_periods"
                                    )
                                elif _is_finite_number(period_count) and float(
                                    period_count
                                ) > 0:
                                    expected_exposure = positive_delta * float(
                                        period_count
                                    )
                                if budget_ceiling is not None:
                                    errors.append(
                                        f"{prefix}.financial_exposure.budget_ceiling_per_period must be null for amount_delta_times_periods"
                                    )
                            elif exposure_model in {
                                "budget_ceiling_times_periods",
                                "bounded_other",
                            }:
                                errors.append(
                                    f"{prefix}.financial_exposure.model must use the numeric budget delta for a budget field"
                                )
                            if (
                                expected_exposure is not None
                                and _is_finite_number(exposure_amount)
                                and not _numbers_close(
                                    float(exposure_amount), expected_exposure
                                )
                            ):
                                errors.append(
                                    f"{prefix}.financial_exposure.maximum_incremental_amount does not reproduce from the budget delta and period_count"
                                )
                        elif exposure_model == "budget_ceiling_times_periods":
                            if period_count is None:
                                errors.append(
                                    f"{prefix}.financial_exposure.period_count is required for budget_ceiling_times_periods"
                                )
                            if budget_ceiling is None:
                                errors.append(
                                    f"{prefix}.financial_exposure.budget_ceiling_per_period is required for budget_ceiling_times_periods"
                                )
                            if (
                                _is_finite_number(period_count)
                                and float(period_count) > 0
                                and _is_finite_number(budget_ceiling)
                                and _is_finite_number(exposure_amount)
                                and not _numbers_close(
                                    float(exposure_amount),
                                    float(budget_ceiling) * float(period_count),
                                )
                            ):
                                errors.append(
                                    f"{prefix}.financial_exposure.maximum_incremental_amount does not reproduce from the budget ceiling and period_count"
                                )
                        elif exposure_model == "bounded_other" and (
                            period_count is not None or budget_ceiling is not None
                        ):
                            errors.append(
                                f"{prefix}.financial_exposure bounded_other requires null period_count and budget_ceiling_per_period"
                            )
                        field_name = (
                            str(change.get("field", "")).strip().lower()
                        )
                        proposed_text = str(proposed_value).strip().upper()
                        enables_delivery = "status" in field_name and proposed_text in {
                            "ACTIVE",
                            "ENABLE",
                            "ENABLED",
                            "ON",
                        }
                        if (
                            enables_delivery
                            and exposure_model != "budget_ceiling_times_periods"
                        ):
                            errors.append(
                                f"{prefix}.financial_exposure must use budget_ceiling_times_periods when a status change enables delivery"
                            )
            preflight = execution.get("preflight")
            if not isinstance(preflight, dict):
                errors.append("execution.preflight must be an object")
            else:
                _required_fields(preflight, ["fresh_state_at", "currency_checked", "timezone_checked", "experiment_impact", "dependencies_checked", "validation_result"], "execution.preflight", errors)
                for flag in ("currency_checked", "timezone_checked", "dependencies_checked"):
                    if preflight.get(flag) is not True:
                        errors.append(f"execution.preflight.{flag} must be true")
                for field in ("fresh_state_at", "experiment_impact", "validation_result"):
                    if not _is_nonempty_string(preflight.get(field)):
                        errors.append(f"execution.preflight.{field} must be a non-empty string")
            readback = execution.get("readback")
            if not isinstance(readback, dict):
                errors.append("execution.readback must be an object")
            else:
                _required_fields(
                    readback,
                    [
                        "tool",
                        "query",
                        "success_predicate",
                        "expected_state",
                        "observed_at",
                        "observed_state",
                    ],
                    "execution.readback",
                    errors,
                )
                for field in ("tool", "query", "success_predicate"):
                    if not _is_nonempty_string(readback.get(field)):
                        errors.append(f"execution.readback.{field} must be a non-empty string")
                readback_tool = readback.get("tool")
                if _is_nonempty_string(readback_tool) and capability_tools.get(
                    readback_tool
                ) != "read":
                    errors.append(
                        "execution.readback.tool must resolve to a read tool in capability_manifest"
                    )
                expected_state = readback.get("expected_state")
                if not isinstance(expected_state, dict) or not expected_state:
                    errors.append(
                        "execution.readback.expected_state must be a non-empty object"
                    )
            rollback = execution.get("rollback")
            if not isinstance(rollback, dict):
                errors.append("execution.rollback must be an object")
            else:
                _required_fields(rollback, ["exact_previous_state", "trigger", "authority", "verification_query"], "execution.rollback", errors)
                if not isinstance(rollback.get("exact_previous_state"), dict) or not rollback.get("exact_previous_state"):
                    errors.append("execution.rollback.exact_previous_state must be a non-empty object")
                for field in ("trigger", "authority", "verification_query"):
                    if not _is_nonempty_string(rollback.get(field)):
                        errors.append(f"execution.rollback.{field} must be a non-empty string")
            if execution.get("execution_state") not in EXECUTION_STATES:
                errors.append("execution.execution_state is invalid")
            execution_state = execution.get("execution_state")
            applied_states = {
                "applied",
                "delivering",
                "outcome_measured",
                "commercially_validated",
            }
            if execution_state in applied_states:
                observed_state = (
                    readback.get("observed_state")
                    if isinstance(readback, dict)
                    else None
                )
                observed_at = (
                    readback.get("observed_at")
                    if isinstance(readback, dict)
                    else None
                )
                expected_state = (
                    readback.get("expected_state")
                    if isinstance(readback, dict)
                    else None
                )
                if not isinstance(observed_state, dict) or not observed_state or not _is_nonempty_string(observed_at):
                    errors.append(
                        "applied-or-later execution state requires a non-empty observed read-back state and time"
                    )
                elif observed_state != expected_state:
                    errors.append(
                        "applied-or-later execution state requires observed_state to match expected_state"
                    )
            if execution_state == "readback_mismatch":
                observed_state = readback.get("observed_state") if isinstance(readback, dict) else None
                observed_at = readback.get("observed_at") if isinstance(readback, dict) else None
                expected_state = readback.get("expected_state") if isinstance(readback, dict) else None
                if not isinstance(observed_state, dict) or not observed_state or not _is_nonempty_string(observed_at):
                    errors.append(
                        "readback_mismatch requires a non-empty observed state and time"
                    )
                elif observed_state == expected_state:
                    errors.append(
                        "readback_mismatch requires observed_state to differ from expected_state"
                    )
    elif "execution" in packet:
        errors.append(
            "non-execute packets must not contain an execution block; paused drafts and other staged writes are execute-class"
        )

    unknowns = _require_list(packet, "unknowns", errors)
    for index, item in enumerate(unknowns):
        prefix = f"unknowns[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _required_fields(item, ["unknown", "decision_impact", "cheapest_evidence", "owner"], prefix, errors)
        for field in ("unknown", "decision_impact", "cheapest_evidence"):
            if not _is_nonempty_string(item.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")

    _validate_paid_audit(packet, paid_sweep, evidence_ids, errors, creative_test=creative_test, creative_history=creative_history)
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", help="Path to decision-packet JSON, or - for stdin")
    parser.add_argument("--paid-sweep", type=Path, help="Independent paid-sweep JSON required for a 1.4 paid_audit")
    parser.add_argument("--creative-test", action="store_true", help="Require measured creative-test decisions and evidence-bound paid WATCH")
    parser.add_argument("--creative-history", type=Path, help="Separately frozen preceding creative-review JSON: {packet, sweep}")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as validation failures")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.packet == "-" else Path(args.packet).read_text(encoding="utf-8")
        packet = json.loads(raw)
        paid_sweep = json.loads(args.paid_sweep.read_text(encoding="utf-8")) if args.paid_sweep else _NO_SWEEP
        creative_history = json.loads(args.creative_history.read_text(encoding="utf-8")) if args.creative_history else None
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)], "warnings": []}, ensure_ascii=False, indent=2))
        return 2
    errors, warnings = validate(packet, paid_sweep=paid_sweep, creative_test=args.creative_test, creative_history=creative_history)
    ok = not errors and not (args.strict and warnings)
    print(json.dumps({"ok": ok, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
