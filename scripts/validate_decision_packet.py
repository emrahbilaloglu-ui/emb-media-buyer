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
from pathlib import Path
from typing import Any


LABELS = {"verified_fact", "derived_metric", "inference", "practitioner_heuristic", "assumption", "unknown"}
DECISIONS = {"act", "test", "hold", "monitor", "revert"}
OPERATING_CLASSES = {"read_only", "prepare", "execute", "monitor"}
RECONCILIATION = {"reconciled", "partially_reconciled", "unreconciled", "unavailable", "not_applicable"}
EXECUTION_STATES = {"validated_only", "accepted", "applied", "delivering", "outcome_measured", "commercially_validated", "partial_failure", "readback_mismatch", "unknown"}
THRESHOLD_ORIGINS = {"business_derived", "account_derived", "design_derived", "runtime_platform_derived", "proposed_governance"}
THRESHOLD_APPROVAL_STATES = {"approved", "proposed", "not_required", "unknown"}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


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


def validate(packet: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(packet, dict):
        return ["packet must be a JSON object"], []

    _required_fields(packet, ["schema_version", "created_at", "operating_class", "scope", "decision", "evidence", "metrics", "data_quality", "diagnosis", "plan", "unknowns"], "packet", errors)
    if packet.get("schema_version") != "1.1":
        errors.append("schema_version must be 1.1")
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

    if plan.get("money_moving") is True and not threshold_records:
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
    if state == "act" and plan.get("money_moving") is True:
        if not isinstance(economics, dict):
            errors.append("money-moving act requires economics")
        if unsafe_reconciliation and not isinstance(plan.get("safety_exception"), dict):
            errors.append("money-moving act requires reconciled/partially_reconciled outcomes or a documented safety_exception")
        if data_quality.get("state") == "fail" and not isinstance(plan.get("safety_exception"), dict):
            errors.append("money-moving act cannot proceed with failed data quality without a documented safety_exception")

    execution = packet.get("execution")
    if operating_class == "execute":
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
                    for field in ("platform", "account_id", "entity_type", "entity_id", "field", "financial_exposure"):
                        if not _is_nonempty_string(change.get(field)):
                            errors.append(f"{prefix}.{field} must be a non-empty string")
                    if change.get("current_value") == change.get("proposed_value"):
                        errors.append(f"{prefix} current_value equals proposed_value")
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
                _required_fields(readback, ["query", "success_predicate", "observed_at", "observed_state"], "execution.readback", errors)
                for field in ("query", "success_predicate"):
                    if not _is_nonempty_string(readback.get(field)):
                        errors.append(f"execution.readback.{field} must be a non-empty string")
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
            if execution.get("execution_state") in {"applied", "delivering", "outcome_measured", "commercially_validated"}:
                if not isinstance(readback, dict) or readback.get("observed_state") is None or readback.get("observed_at") is None:
                    errors.append("applied-or-later execution state requires observed read-back state and time")
    elif isinstance(execution, dict) and execution.get("execution_state") not in {None, "validated_only", "unknown"}:
        warnings.append("a non-execute packet reports an applied execution state; verify operating_class")

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

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", help="Path to decision-packet JSON, or - for stdin")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as validation failures")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.packet == "-" else Path(args.packet).read_text(encoding="utf-8")
        packet = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)], "warnings": []}, ensure_ascii=False, indent=2))
        return 2
    errors, warnings = validate(packet)
    ok = not errors and not (args.strict and warnings)
    print(json.dumps({"ok": ok, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
