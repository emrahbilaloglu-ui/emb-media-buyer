from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_decision_packet.py"
SPEC = importlib.util.spec_from_file_location("validate_decision_packet", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def base_packet() -> dict:
    return {
        "schema_version": "1.2",
        "created_at": "2026-08-23T12:00:00+03:00",
        "operating_class": "read_only",
        "scope": {
            "platforms": ["meta"],
            "accounts": ["act_123"],
            "entities": ["campaign_1"],
            "markets": ["TR"],
            "currency": "TRY",
            "timezone": "Europe/Istanbul",
            "reporting_window": "2026-08-01/2026-08-21",
            "comparison_window": "2026-07-09/2026-07-29",
            "business_outcome": "settled_new_customer_order",
            "optimization_event": "purchase",
            "attribution": "account setting read at runtime",
            "conversion_lag": "7 days"
        },
        "decision": {
            "state": "hold",
            "summary": "Hold budget until order reconciliation is complete.",
            "owner": "media lead",
            "deadline": "2026-08-24",
            "confidence": "medium",
            "evidence_rung": 1,
            "causal_claim": False
        },
        "evidence": [
            {
                "id": "e1",
                "label": "verified_fact",
                "claim": "Platform and store totals are not reconciled.",
                "source": "matched platform/store export",
                "retrieved_at": "2026-08-23T11:30:00+03:00",
                "limitations": ["refund window incomplete"]
            }
        ],
        "metrics": [
            {
                "name": "platform_spend",
                "value": 1000,
                "unit": "TRY currency",
                "source_id": "e1",
                "window": "2026-08-01/2026-08-21",
                "timezone": "Europe/Istanbul",
                "currency": "TRY",
                "attribution": None,
                "conversion_definition": None,
                "count": None,
                "denominator": None,
                "evidence_label": "verified_fact"
            }
        ],
        "data_quality": {
            "state": "pass_with_limits",
            "reconciliation": "unreconciled",
            "binding": "verified",
            "critical_issues": ["order totals not aligned"]
        },
        "diagnosis": {
            "observation": "Platform value moved while store value did not.",
            "leading_hypothesis": "Attribution or definition mismatch.",
            "alternatives": ["refund lag", "currency or time-zone mismatch"],
            "confounds": ["incomplete refund window"],
            "discriminator": "Reconcile event/order IDs and value definitions."
        },
        "plan": {
            "action": "Reconcile before changing spend.",
            "money_moving": False,
            "owner": "analytics",
            "primary_metric": "matched settled orders",
            "guardrails": ["No budget mutation"],
            "monitoring_window": "after complete refund lag",
            "decision_rule": "Reassess only when the gap is explained.",
            "reversal_condition": "Not applicable; no live change.",
            "threshold_records": []
        },
        "unknowns": [
            {
                "unknown": "event-to-order gap",
                "decision_impact": "caps profitability confidence",
                "cheapest_evidence": "ID-level matched export",
                "owner": "analytics"
            }
        ]
    }


def valid_execute_packet() -> dict:
    packet = base_packet()
    packet["operating_class"] = "execute"
    packet["decision"]["state"] = "act"
    packet["plan"]["money_moving"] = True
    packet["plan"]["threshold_records"] = [
        {
            "name": "approved daily budget ceiling",
            "rule": "daily_budget must not exceed 120 TRY",
            "origin": "business_derived",
            "source": "approved finance downside budget",
            "derivation": "current 100 TRY plus approved 20 TRY staged exposure",
            "scope": "ad_set_101",
            "approval_state": "approved",
            "approver": "user",
        }
    ]
    packet["data_quality"]["state"] = "pass"
    packet["data_quality"]["reconciliation"] = "reconciled"
    packet["economics"] = {
        "acquisition_unit": "new customer",
        "revenue_basis": "settled net revenue",
        "target_source": "finance contribution model",
        "scenarios": [{"name": "base", "target_cpa": 250}],
        "marginal_implication": "The staged increase remains inside the approved downside exposure.",
        "capacity_constraints": ["daily fulfillment cap checked"]
    }
    packet["capability_manifest"] = [
        {
            "tool": "ads_update_entity",
            "endpoint": "/ad-set/update",
            "method": "POST",
            "mutability": "write",
            "permissions": "account-scoped write",
            "limits_or_latency": [],
            "retrieved_at": "2026-08-23T12:04:00+03:00",
        },
        {
            "tool": "ads_get_entity",
            "endpoint": "/ad-set/get",
            "method": "GET",
            "mutability": "read",
            "permissions": "account-scoped read",
            "limits_or_latency": [],
            "retrieved_at": "2026-08-23T12:04:00+03:00",
        },
    ]
    packet["execution"] = {
        "approval": {
            "status": "approved",
            "approved_by": "user",
            "approved_at": "2026-08-23T12:05:00+03:00",
            "scope": "Change only ad_set_101 daily_budget from 100 to 120 TRY."
        },
        "changes": [
            {
                "platform": "meta",
                "account_id": "act_123",
                "entity_type": "ad_set",
                "entity_id": "ad_set_101",
                "field": "daily_budget",
                "current_value": 100,
                "proposed_value": 120,
                "absolute_delta": 20,
                "percentage_delta": 20,
                "financial_exposure": {
                    "currency": "TRY",
                    "model": "amount_delta_times_periods",
                    "period_count": 1,
                    "budget_ceiling_per_period": None,
                    "maximum_incremental_amount": 20,
                    "horizon": "one approved active day",
                    "derivation": "max(0, 120 - 100) * 1 day",
                }
            }
        ],
        "preflight": {
            "fresh_state_at": "2026-08-23T12:06:00+03:00",
            "currency_checked": True,
            "timezone_checked": True,
            "experiment_impact": "no active experiment",
            "dependencies_checked": True,
            "validation_result": "target and field match approved scope"
        },
        "readback": {
            "tool": "ads_get_entity",
            "query": "read ad_set_101 daily_budget and status",
            "success_predicate": "daily_budget equals 120 TRY and all unapproved fields remain unchanged",
            "expected_state": {"daily_budget": 120, "status": "PAUSED"},
            "observed_at": None,
            "observed_state": None
        },
        "rollback": {
            "exact_previous_state": {"daily_budget": 100},
            "trigger": "approved contribution guardrail failure",
            "authority": "same-session approval covers rollback",
            "verification_query": "read ad_set_101 daily_budget and status"
        },
        "execution_state": "validated_only"
    }
    return packet


def directional_packet(*, execute: bool = False, direction: str = "none") -> dict:
    packet = valid_execute_packet() if execute else base_packet()
    packet["schema_version"] = "1.3"
    packet["decision"].update({"claim_type": "operational", "causal_claim": False})
    packet["plan"].update({
        "exposure_direction": direction,
        "money_moving": direction in {"increase", "reduce", "rotate"},
        "decision_basis": {
            "kind": "qualitative_risk",
            "rationale": "Owner requests a reversible allocation decision, not an inferiority claim.",
            "source_ids": ["e1"],
            "counterevidence": ["Late credit may arrive; sibling quality is not established."],
        },
        "unresolved_gates": [],
        "threshold_records": [],
    })
    packet["data_quality"]["critical_issues"] = []
    if execute:
        packet["execution"]["changes"][0]["financial_exposure"]["amount_semantics"] = "nominal_reference"
    return packet


def operational_pause_packet(*, direction: str = "rotate") -> dict:
    """Synthetic TRY contract fixture; ad_069 is not a historical account ID."""
    packet = directional_packet(execute=True, direction=direction)
    packet["scope"]["entities"] = ["ad_069"]
    packet["decision"]["summary"] = "Pause only the reviewed synthetic ad as a reversible operational allocation choice."
    packet["evidence"][0].update({
        "claim": "Reviewed synthetic ad_069 has 1000 TRY spend, an old attributed outcome and further spend; the owner authorizes its pause while business reconciliation remains unavailable.",
        "source": "synthetic TRY source-ad review and exact owner approval fixture",
        "limitations": ["Business economics unavailable; late credit and sibling performance remain uncertain."],
    })
    packet["plan"].update({
        "action": "Set only ad_069 status ACTIVE to PAUSED.",
        "owner": "media lead",
        "primary_metric": "source-ad delivery status and subsequent business outcomes",
        "guardrails": ["Preserve all adjacent ads, parent budgets, bids and targeting."],
        "monitoring_window": "Fresh independent status readback, then existing daily review.",
        "decision_rule": "Apply the exact approved source-level pause; make no inferiority or savings claim.",
        "reversal_condition": "Restore the captured ACTIVE state only under applicable rollback authority after review of new evidence or a scope error.",
    })
    packet["diagnosis"].update({
        "observation": "Source-ad spending continued after an old attributed outcome; business reconciliation is unavailable.",
        "leading_hypothesis": "The incumbent's current allocation no longer justifies its opportunity cost under the owner's reviewed test priorities.",
        "alternatives": ["Late attribution may add outcomes", "The old outcome may precede further useful learning"],
        "confounds": ["Incomplete attribution lag", "Unknown sibling response and business economics"],
        "discriminator": "Existing daily outcome review and source binding; none establishes causal inferiority.",
    })
    packet["unknowns"] = [{
        "unknown": "Business reconciliation, margin and sibling performance",
        "decision_impact": "Blocks profit/scale claims and leaves rotation performance uncertain.",
        "cheapest_evidence": "Matched order ledger and existing next daily source-level read.",
        "owner": "media lead",
    }]
    packet.pop("economics")
    packet["data_quality"].update({"state": "pass_with_limits", "reconciliation": "unavailable"})
    packet["plan"]["unresolved_gates"] = [{
        "reason": "Margin unknown; profitability and new exposure remain blocked.",
        "scope": "same account and source ad",
        "blocked_directions": ["increase"],
        "blocked_claims": ["profitability"],
    }]
    change = packet["execution"]["changes"][0]
    change.update({
        "entity_type": "ad", "entity_id": "ad_069", "field": "status",
        "current_value": "ACTIVE", "proposed_value": "PAUSED",
        "absolute_delta": None, "percentage_delta": None,
        "financial_exposure": {
            "currency": "TRY", "model": "bounded_other", "period_count": None,
            "budget_ceiling_per_period": None, "maximum_incremental_amount": 0,
            "amount_semantics": "nominal_reference", "horizon": "existing daily review",
            "derivation": "No new nominal budget; unchanged shared-set budget may route to siblings. No savings guaranteed.",
        },
    })
    packet["execution"]["approval"]["scope"] = "Pause only ad_069; fixed parent budget unchanged."
    packet["execution"]["readback"].update({
        "query": "Read ad_069 configured/effective status and verify adjacent fields against the captured baseline.",
        "success_predicate": "ad_069 status is PAUSED and all unapproved fields remain unchanged.",
        "expected_state": {"ad_069": "PAUSED"},
    })
    packet["execution"]["rollback"].update({
        "exact_previous_state": {"ad_069": "ACTIVE"},
        "trigger": "Wrong target, unexpected adjacent changes, or owner-authorized reversal after new evidence.",
        "verification_query": "Read ad_069 configured/effective status and unchanged adjacent fields.",
    })
    return packet


class ValidatorTests(unittest.TestCase):
    def test_valid_hold_packet(self) -> None:
        errors, warnings = validator.validate(base_packet())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_rejects_low_rung_causal_claim(self) -> None:
        packet = base_packet()
        packet["decision"]["causal_claim"] = True
        errors, _ = validator.validate(packet)
        self.assertTrue(any("causal claim" in item for item in errors))

    def test_rejects_money_move_without_economics(self) -> None:
        packet = base_packet()
        packet["decision"]["state"] = "act"
        packet["plan"]["money_moving"] = True
        errors, _ = validator.validate(packet)
        self.assertTrue(any("requires economics" in item for item in errors))
        self.assertTrue(any("reconciled" in item for item in errors))

    def test_execute_requires_approval_and_change_packet(self) -> None:
        packet = base_packet()
        packet["operating_class"] = "execute"
        errors, _ = validator.validate(packet)
        self.assertTrue(any("requires execution" in item for item in errors))

    def test_valid_execution_packet(self) -> None:
        errors, warnings = validator.validate(valid_execute_packet())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_execution_rejects_incomplete_approval(self) -> None:
        packet = valid_execute_packet()
        packet["execution"]["approval"]["approved_at"] = None
        errors, _ = validator.validate(packet)
        self.assertTrue(any("approved_at" in item for item in errors))

    def test_execution_requires_resolved_write_and_read_tools(self) -> None:
        packet = valid_execute_packet()
        del packet["capability_manifest"]
        errors, _ = validator.validate(packet)
        self.assertTrue(any("requires capability_manifest" in item for item in errors))

        packet = valid_execute_packet()
        packet["capability_manifest"][0]["mutability"] = "mixed_dispatcher"
        errors, _ = validator.validate(packet)
        self.assertTrue(any("resolve the underlying tools" in item for item in errors))
        self.assertTrue(any("explicit write tool" in item for item in errors))

    def test_applied_execution_requires_matching_independent_readback(self) -> None:
        packet = valid_execute_packet()
        packet["execution"]["execution_state"] = "applied"
        packet["execution"]["readback"]["observed_at"] = "2026-08-23T12:07:00+03:00"
        packet["execution"]["readback"]["observed_state"] = {
            "daily_budget": 120,
            "status": "PAUSED",
        }
        errors, _ = validator.validate(packet)
        self.assertEqual(errors, [])

        for observed_state in [
            {"daily_budget": 100, "status": "PAUSED"},
            {},
            {"success": True, "code": 0},
        ]:
            with self.subTest(observed_state=observed_state):
                packet = valid_execute_packet()
                packet["execution"]["execution_state"] = "applied"
                packet["execution"]["readback"]["observed_at"] = "2026-08-23T12:07:00+03:00"
                packet["execution"]["readback"]["observed_state"] = observed_state
                errors, _ = validator.validate(packet)
                self.assertTrue(any("read-back state" in item or "match expected_state" in item for item in errors))

        packet = valid_execute_packet()
        packet["execution"]["readback"]["tool"] = "ads_update_entity"
        errors, _ = validator.validate(packet)
        self.assertTrue(any("resolve to a read tool" in item for item in errors))

    def test_readback_mismatch_state_requires_a_real_mismatch(self) -> None:
        packet = valid_execute_packet()
        packet["execution"]["execution_state"] = "readback_mismatch"
        packet["execution"]["readback"]["observed_at"] = "2026-08-23T12:07:00+03:00"
        packet["execution"]["readback"]["observed_state"] = {
            "daily_budget": 100,
            "status": "PAUSED",
        }
        errors, _ = validator.validate(packet)
        self.assertEqual(errors, [])

        packet["execution"]["readback"]["observed_state"] = packet["execution"]["readback"]["expected_state"]
        errors, _ = validator.validate(packet)
        self.assertTrue(any("requires observed_state to differ" in item for item in errors))

    def test_execution_delta_arithmetic_is_verified(self) -> None:
        packet = valid_execute_packet()
        packet["execution"]["changes"][0]["proposed_value"] = 12000
        errors, _ = validator.validate(packet)
        self.assertTrue(any("absolute_delta" in item for item in errors))
        self.assertTrue(any("percentage_delta" in item for item in errors))

        packet = valid_execute_packet()
        change = packet["execution"]["changes"][0]
        change["proposed_value"] = 12000
        change["absolute_delta"] = 11900
        change["percentage_delta"] = 11900
        errors, _ = validator.validate(packet)
        self.assertTrue(any("does not reproduce" in item for item in errors))

        packet = valid_execute_packet()
        change = packet["execution"]["changes"][0]
        change.update(
            {
                "field": "name",
                "current_value": "old name",
                "proposed_value": "new name",
                "absolute_delta": None,
                "percentage_delta": None,
                "financial_exposure": {
                    "currency": "TRY",
                    "model": "bounded_other",
                    "period_count": None,
                    "budget_ceiling_per_period": None,
                    "maximum_incremental_amount": 0,
                    "horizon": "configuration write only",
                    "derivation": "name-only change does not alter a spend control",
                },
            }
        )
        errors, _ = validator.validate(packet)
        self.assertEqual(errors, [])

    def test_delivery_activation_exposure_uses_budget_ceiling(self) -> None:
        packet = valid_execute_packet()
        change = packet["execution"]["changes"][0]
        change.update(
            {
                "field": "status",
                "current_value": "DISABLED",
                "proposed_value": "ENABLED",
                "absolute_delta": None,
                "percentage_delta": None,
                "financial_exposure": {
                    "currency": "TRY",
                    "model": "budget_ceiling_times_periods",
                    "period_count": 2,
                    "budget_ceiling_per_period": 120,
                    "maximum_incremental_amount": 240,
                    "horizon": "two approved active days",
                    "derivation": "120 TRY daily ceiling * 2 days",
                },
            }
        )
        errors, _ = validator.validate(packet)
        self.assertEqual(errors, [])

        change["financial_exposure"]["maximum_incremental_amount"] = 20
        errors, _ = validator.validate(packet)
        self.assertTrue(any("budget ceiling" in item for item in errors))

        change["financial_exposure"] = {
            "currency": "TRY",
            "model": "bounded_other",
            "period_count": None,
            "budget_ceiling_per_period": None,
            "maximum_incremental_amount": 0,
            "horizon": "unknown",
            "derivation": "not calculated",
        }
        errors, _ = validator.validate(packet)
        self.assertTrue(any("enables delivery" in item for item in errors))

    def test_non_execute_packet_cannot_carry_a_staged_write(self) -> None:
        packet = valid_execute_packet()
        packet["operating_class"] = "prepare"
        del packet["capability_manifest"]
        errors, _ = validator.validate(packet)
        self.assertTrue(any("must not contain an execution block" in item for item in errors))

    def test_rate_warns_without_denominator(self) -> None:
        packet = base_packet()
        packet["metrics"][0]["unit"] = "rate"
        _, warnings = validator.validate(packet)
        self.assertTrue(any("without count or denominator" in item for item in warnings))

    def test_money_move_requires_sourced_threshold_record(self) -> None:
        packet = valid_execute_packet()
        packet["plan"]["threshold_records"] = []
        errors, _ = validator.validate(packet)
        self.assertTrue(any("sourced threshold record" in item for item in errors))

    def test_unapproved_governance_threshold_cannot_move_money(self) -> None:
        packet = valid_execute_packet()
        threshold = packet["plan"]["threshold_records"][0]
        threshold["origin"] = "proposed_governance"
        threshold["approval_state"] = "proposed"
        threshold["approver"] = None
        errors, _ = validator.validate(packet)
        self.assertTrue(any("owner approval" in item for item in errors))

    def test_approved_threshold_requires_named_approver(self) -> None:
        packet = valid_execute_packet()
        packet["plan"]["threshold_records"][0]["approver"] = None
        errors, _ = validator.validate(packet)
        self.assertTrue(any("approver is required" in item for item in errors))


class DirectionalContractTests(unittest.TestCase):
    def test_unknown_margin_operational_pause_needs_no_fake_threshold_or_exception(self) -> None:
        for direction in ("reduce", "rotate"):
            with self.subTest(direction=direction):
                packet = operational_pause_packet(direction=direction)
                errors, warnings = validator.validate(packet)
                self.assertEqual((errors, warnings), ([], []))
                self.assertNotIn("safety_exception", packet["plan"])
                self.assertEqual(packet["data_quality"]["reconciliation"], "unavailable")

    def test_operational_stop_does_not_prove_inferiority(self) -> None:
        packet = operational_pause_packet()
        packet["decision"]["claim_type"] = "inferiority"
        errors, _ = validator.validate(packet)
        self.assertTrue(any("claim_sufficiency" in item for item in errors))
        packet["decision"]["claim_sufficiency"] = {
            "method": "Two-arm design with commercial MDE", "result": "unknown", "source_ids": ["e1"],
        }
        errors, _ = validator.validate(packet)
        self.assertTrue(any("supported result" in item for item in errors))

    def test_unknown_margin_scale_is_blocked_even_with_safety_label(self) -> None:
        packet = directional_packet(execute=True, direction="increase")
        packet.pop("economics")
        packet["data_quality"]["reconciliation"] = "unavailable"
        packet["plan"]["safety_exception"] = {"reason": "ordinary growth"}
        errors, _ = validator.validate(packet)
        self.assertTrue(any("requires economics" in item for item in errors))
        self.assertTrue(any("reconciled" in item for item in errors))

    def test_empty_economics_does_not_qualify_increase(self) -> None:
        packet = directional_packet(execute=True, direction="increase")
        packet["economics"] = {}
        errors, _ = validator.validate(packet)
        self.assertTrue(any("economics.scenarios" in item for item in errors))
        self.assertTrue(any("economics.target_source" in item for item in errors))

    def test_profitability_claim_is_gated_even_in_read_only_or_monitor(self) -> None:
        for mode in ("read_only", "monitor", "prepare"):
            with self.subTest(mode=mode):
                packet = directional_packet()
                packet["operating_class"] = mode
                packet["decision"]["claim_type"] = "profitability"
                packet["data_quality"]["reconciliation"] = "not_applicable"
                errors, _ = validator.validate(packet)
                self.assertTrue(any("requires economics" in item for item in errors))
                self.assertTrue(any("reconciled/partially_reconciled" in item for item in errors))

    def test_supported_increase_passes_but_not_applicable_reconciliation_does_not(self) -> None:
        packet = directional_packet(execute=True, direction="increase")
        packet["plan"]["decision_basis"]["kind"] = "economics"
        self.assertEqual(validator.validate(packet), ([], []))
        packet["data_quality"]["reconciliation"] = "not_applicable"
        errors, _ = validator.validate(packet)
        self.assertTrue(any("reconciled/partially_reconciled" in item for item in errors))

    def test_prepared_increase_under_hold_does_not_assert_economic_readiness(self) -> None:
        packet = directional_packet(direction="increase")
        packet["operating_class"] = "prepare"
        packet["plan"]["unresolved_gates"] = [{
            "reason": "Margin not verified", "scope": "current account", "blocked_directions": ["increase"], "blocked_claims": ["profitability"],
        }]
        self.assertEqual(validator.validate(packet), ([], []))

    def test_malformed_new_categories_report_errors_instead_of_type_errors(self) -> None:
        for category in ("schema_version", "direction", "claim_type", "basis_kind", "semantics", "gate_directions"):
            for bad_value in ({}, []):
                with self.subTest(category=category, bad_value=bad_value):
                    packet = operational_pause_packet()
                    if category == "schema_version":
                        packet["schema_version"] = bad_value
                    elif category == "direction":
                        packet["plan"]["exposure_direction"] = bad_value
                    elif category == "claim_type":
                        packet["decision"]["claim_type"] = bad_value
                    elif category == "basis_kind":
                        packet["plan"]["decision_basis"]["kind"] = bad_value
                    elif category == "semantics":
                        packet["execution"]["changes"][0]["financial_exposure"]["amount_semantics"] = bad_value
                    else:
                        packet["plan"]["unresolved_gates"][0]["blocked_directions"] = [bad_value]
                    errors, _ = validator.validate(packet)
                    self.assertTrue(errors)

    def test_exposure_direction_cannot_disguise_budget_increase_or_activation(self) -> None:
        for direction in ("reduce", "rotate", "none", "continue"):
            with self.subTest(direction=direction):
                packet = directional_packet(execute=True, direction=direction)
                errors, _ = validator.validate(packet)
                self.assertTrue(any("increases exposure" in item for item in errors))
        for status in ("ACTIVE", "ENABLED", "ON"):
            with self.subTest(status=status):
                packet = operational_pause_packet()
                packet["execution"]["changes"][0].update({"current_value": "PAUSED", "proposed_value": status})
                errors, _ = validator.validate(packet)
                self.assertTrue(any("increases exposure" in item for item in errors))

    def test_operational_pause_still_needs_authority_and_binding(self) -> None:
        for invalid in ("approval", "binding", "critical_issue", "failed_quality"):
            with self.subTest(invalid=invalid):
                packet = operational_pause_packet()
                packet["plan"]["safety_exception"] = {"reason": "cannot bypass gates"}
                if invalid == "approval":
                    packet["execution"]["approval"]["status"] = "not_approved"
                elif invalid == "binding":
                    packet["data_quality"]["binding"] = "unverified"
                elif invalid == "failed_quality":
                    packet["data_quality"]["state"] = "fail"
                else:
                    packet["data_quality"]["critical_issues"] = ["target source identity unresolved"]
                errors, _ = validator.validate(packet)
                self.assertTrue(errors)

    def test_scoped_margin_hold_allows_risk_stop_but_identity_hold_blocks_it(self) -> None:
        packet = operational_pause_packet()
        errors, _ = validator.validate(packet)
        self.assertEqual(errors, [])
        packet["plan"]["unresolved_gates"].append({
            "reason": "Target identity is not resolved", "scope": "ad_069",
            "blocked_directions": ["rotate", "reduce"], "blocked_claims": [],
        })
        errors, _ = validator.validate(packet)
        self.assertTrue(any("blocks this decision" in item for item in errors))
        packet["decision"]["state"] = "hold"
        errors, _ = validator.validate(packet)
        self.assertTrue(any("blocks this decision" in item for item in errors))
        packet["operating_class"] = "prepare"
        packet.pop("execution")
        errors, _ = validator.validate(packet)
        self.assertEqual(errors, [])

    def test_current_approval_is_reusable_without_another_approval_field(self) -> None:
        packet = operational_pause_packet()
        packet["execution"]["approval"]["scope"] = "Standing authority covers exactly ad_069 pause after current review."
        errors, _ = validator.validate(packet)
        self.assertEqual(errors, [])

    def test_sourced_qualitative_basis_cannot_point_at_missing_evidence(self) -> None:
        packet = operational_pause_packet()
        packet["plan"]["decision_basis"]["source_ids"] = ["invented"]
        errors, _ = validator.validate(packet)
        self.assertTrue(any("existing evidence IDs" in item for item in errors))

    def test_non_delivery_config_write_can_use_none(self) -> None:
        packet = directional_packet(execute=True)
        packet["execution"]["changes"][0].update({
            "field": "name", "current_value": "old", "proposed_value": "new",
            "absolute_delta": None, "percentage_delta": None,
            "financial_exposure": {
                "currency": "TRY", "model": "bounded_other", "period_count": None,
                "budget_ceiling_per_period": None, "maximum_incremental_amount": 0,
                "amount_semantics": "nominal_reference", "horizon": "name write only",
                "derivation": "No budget/delivery field changes.",
            },
        })
        self.assertEqual(validator.validate(packet), ([], []))

    def test_paid_continuation_is_a_decision_but_small_read_has_no_continuation_form(self) -> None:
        packet = directional_packet()
        self.assertEqual(validator.validate(packet), ([], []))
        packet["decision"]["state"] = "monitor"
        packet["plan"]["exposure_direction"] = "continue"
        errors, _ = validator.validate(packet)
        self.assertTrue(any("plan.continuation" in item for item in errors))
        packet["plan"]["continuation"] = {
            "since_previous_review": "+19.43 spend, one new business order on 3 November; no new result after last read.",
            "last_outcomes": "Platform and store latest outcomes dated separately; attribution still maturing.",
            "exposure_context": "Existing daily cadence and approved test context; evergreen total unknown, nominal budget is not cash cap.",
            "cost_of_waiting": "Further spend and opportunity cost to untested sources.",
            "cost_of_stopping": "May lose further learning from a recent order; repeatability unproven.",
            "next_information": "Existing next daily read can show new settled outcomes and attribution backfill.",
            "continuation_rationale": "Fresh outcome supports one further reviewed interval, with no automatic immunity.",
            "next_review": "Existing daily review, not a new scheduler or stop date.",
            "decision_trigger": "Further exposure without new attributable or business outcomes changes the balance.",
            "trigger_response": "Re-decide pause versus justified continuation under current authority; never copy prior WATCH.",
        }
        self.assertEqual(validator.validate(packet), ([], []))
        del packet["plan"]["continuation"]["cost_of_waiting"]
        errors, _ = validator.validate(packet)
        self.assertTrue(any("cost_of_waiting" in item for item in errors))

    def test_nominal_budget_reference_is_not_a_verified_cash_bound(self) -> None:
        packet = directional_packet(execute=True, direction="increase")
        self.assertEqual(validator.validate(packet), ([], []))
        exposure = packet["execution"]["changes"][0]["financial_exposure"]
        exposure["amount_semantics"] = "verified_bound"
        errors, _ = validator.validate(packet)
        self.assertTrue(any("separate bound_evidence" in item for item in errors))

    def test_applied_pause_still_needs_matching_independent_readback(self) -> None:
        packet = operational_pause_packet()
        packet["execution"]["execution_state"] = "applied"
        packet["execution"]["readback"].update({
            "observed_at": "2026-11-04T14:39:45Z", "observed_state": {"ad_069": "ACTIVE"},
        })
        errors, _ = validator.validate(packet)
        self.assertTrue(any("match expected_state" in item for item in errors))

    def test_json_schema_accepts_both_versions_and_conditional_contracts(self) -> None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("optional jsonschema package not installed")
        schema_path = SCRIPT.parents[1] / "assets" / "schemas" / "decision-packet.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schema_validator = Draft202012Validator(schema)
        for packet in (base_packet(), valid_execute_packet(), directional_packet(), operational_pause_packet()):
            with self.subTest(version=packet["schema_version"], mode=packet["operating_class"]):
                self.assertEqual(list(schema_validator.iter_errors(packet)), [])
        packet = operational_pause_packet()
        packet["plan"].pop("decision_basis")
        self.assertTrue(list(schema_validator.iter_errors(packet)))
        packet = directional_packet(direction="continue")
        self.assertTrue(list(schema_validator.iter_errors(packet)))


def paid_audit_packet() -> tuple[dict, dict]:
    """Synthetic, local-only paired artifact for the independently scoped audit branch."""
    packet = directional_packet(direction="continue")
    packet["schema_version"] = "1.4"
    packet["created_at"] = "2026-11-07T15:10:00+03:00"
    packet["scope"]["entities"] = ["ad_069", "ad_zero"]
    packet["scope"]["report_time"] = "impression"
    packet["evidence"][0].update({
        "source": "synthetic independent paid-sweep and underlying ad/day observations",
        "claim": "ad_069 has observed paid delivery; ad_zero is active but has verified zero exposure.",
        "retrieved_at": "2026-11-07T15:00:00+03:00",
    })
    sweep = {
        "command": "paid-sweep",
        "scope": {
            "platform": "meta", "account_id": "act_123", "campaign_id": "campaign_1",
            "currency": "TRY", "timezone": "Europe/Istanbul", "as_of": "2026-11-07T15:00:00+03:00",
            "attribution": packet["scope"]["attribution"], "report_time": packet["scope"]["report_time"],
        },
        "coverage": {"expected_active_ids": ["ad_069", "ad_zero"], "inventory_manifest": {
            "independent": True, "source_id": "synthetic native inventory", "complete": True,
            "pagination_complete": True, "retrieved_at": "2026-11-07T15:00:00+03:00",
        }},
        "complete_for_decision": True,
        "entities": [
            {
                "ad_id": ad_id, "account_id": "act_123", "campaign_id": "campaign_1",
                "parent_id": "set_1", "epoch_id": "binding_1", "binding_verified": True,
                "lifecycle_start": "2026-11-01",
                "configured_status": "ACTIVE", "effective_status": "ACTIVE",
                "disposition": "active_decision", "coverage_state": "observed",
                "current_paid_delivery": paid,
                "metrics": {"lifecycle": {"spend": spend, "purchases": purchases}},
            }
            for ad_id, paid, spend, purchases in (("ad_069", True, 216.73, 1), ("ad_zero", False, 0, 0))
        ],
    }
    packet["paid_audit"] = {
        "campaign_id": "campaign_1", "as_of": sweep["scope"]["as_of"], "coverage_mode": "full_sweep",
        "complete_for_decision": True, "evidence_ids": ["e1"],
        "decisions": [
            {
                "entity_id": "ad_069", "binding_epoch": "binding_1", "observed_paid_delivery": True,
                "disposition": "continue", "evidence_ids": ["e1"],
                "continuation": {
                    "current": {"spend": 216.73, "platform_outcomes": 1, "merchant_outcomes": None},
                    "prior": None, "increment": None, "change_kind": "first_read",
                    "basis": "test_information", "evidence_ids": ["e1"],
                    "rationale": "Use one existing review interval to observe closure of the latest completed exposure cohort under the current test authorization.",
                    "expected_information": "Completed cohort joins can show whether the recent click credit has any independently matched merchant outcome.",
                    "cost_of_waiting": "Current allocation may keep buying impressions at unchanged parent budget.",
                    "cost_of_stopping": "Could remove the only currently bound source for this cohort before the next scheduled read.",
                    "exposure_context": "Existing test allocation; no change to set budget or cash cap.",
                    "next_read_at": "2026-11-08T15:00:00+03:00",
                    "trigger": {
                        "condition": "The completed cohort arrives without a matched outcome and further cost accumulates.",
                        "state": "pending", "response": "Reassess operational rotation against actual new evidence and current authority.",
                    },
                },
            },
            {
                "entity_id": "ad_zero", "binding_epoch": "binding_1", "observed_paid_delivery": False,
                "disposition": "no_paid_delivery", "evidence_ids": ["e1"],
            },
        ],
    }
    return packet, sweep


class PaidAuditContractTests(unittest.TestCase):
    def test_exact_legacy_placeholder_repro_is_rejected_without_breaking_small_hold(self) -> None:
        packet = directional_packet(direction="continue")
        packet["plan"]["continuation"] = {field: "generic placeholder" for field in validator.CONTINUATION_FIELDS}
        errors, _ = validator.validate(packet)
        self.assertTrue(any("same placeholder" in error for error in errors))
        small_hold = directional_packet()
        self.assertEqual(validator.validate(small_hold), ([], []))
        small_hold["schema_version"] = "1.4"
        self.assertEqual(validator.validate(small_hold), ([], []))

    def test_legacy_paid_hold_repro_requires_migrating_to_typed_audit(self) -> None:
        packet, sweep = paid_audit_packet()
        legacy = directional_packet()
        legacy["scope"]["entities"] = ["ad_069"]
        legacy["decision"]["summary"] = "The synthetic active ad continues to spend under HOLD."
        self.assertEqual(validator.validate(legacy), ([], []))  # free text is not a delivery contract
        errors, _ = validator.validate(legacy, paid_sweep=sweep)
        self.assertTrue(any("schema_version 1.4" in error for error in errors))

        packet["plan"]["exposure_direction"] = "none"
        row = packet["paid_audit"]["decisions"][0]
        row.pop("continuation")
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("HOLD/none" in error for error in errors))
        self.assertTrue(any("required for active paid continuation" in error for error in errors))

    def test_paid_hold_passes_only_with_bound_evidence_and_explicit_continuation(self) -> None:
        packet, sweep = paid_audit_packet()
        self.assertEqual(validator.validate(packet, paid_sweep=sweep), ([], []))
        self.assertEqual(validator.validate(packet, paid_sweep={"ok": True, "result": sweep}), ([], []))
        errors, _ = validator.validate(packet)
        self.assertTrue(any("separately supplied paid-sweep" in error for error in errors))
        record = packet["paid_audit"]["decisions"][0]
        record["observed_paid_delivery"] = False
        record["binding_epoch"] = "wrong_epoch"
        record["continuation"]["current"]["platform_outcomes"] = 9
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("observed_paid_delivery" in error for error in errors))
        self.assertTrue(any("binding_epoch" in error for error in errors))
        self.assertTrue(any("current.platform_outcomes" in error for error in errors))

    def test_purchase_positive_does_not_supply_keep_basis(self) -> None:
        packet, sweep = paid_audit_packet()
        continuation = packet["paid_audit"]["decisions"][0]["continuation"]
        self.assertEqual(continuation["current"]["platform_outcomes"], 1)
        continuation["basis"] = "positive_purchase"
        continuation["next_read_at"] = packet["paid_audit"]["as_of"]
        continuation["evidence_ids"] = ["invented"]
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        for expected in ("positive purchase alone", "later than audit as_of", "existing evidence IDs"):
            self.assertTrue(any(expected in error for error in errors), errors)

    def test_watch_reassessment_and_separate_ledger_deltas_are_enforced(self) -> None:
        packet, sweep = paid_audit_packet()
        continuation = packet["paid_audit"]["decisions"][0]["continuation"]
        continuation.update({
            "change_kind": "new_information",
            "prior": {
                "as_of": "2026-11-06T15:00:00+03:00", "spend": 59.15, "platform_outcomes": 1,
                "merchant_outcomes": None, "rationale": continuation["rationale"],
                "next_read_at": "2026-11-07T15:00:00+03:00", "evidence_ids": ["e1"],
                "currency": "TRY", "timezone": "Europe/Istanbul", "attribution": packet["scope"]["attribution"],
                "report_time": packet["scope"]["report_time"], "start_date": "2026-11-01",
            },
            "increment": {"spend": 157.58, "platform_outcomes": 0, "merchant_outcomes": 0},
        })
        continuation["trigger"]["state"] = "met"
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        for expected in ("unchanged prior", "met trigger", "merchant_outcomes must be null"):
            self.assertTrue(any(expected in error for error in errors), errors)

        continuation["rationale"] = "Source was rebound after the prior observation; use the new matched cohort to distinguish old-credit carryover from current delivery."
        continuation["trigger"]["reassessment"] = "Old credit remained flat after +157.58 TRY; new verified binding evidence supports one bounded read, not retention based on the old sale."
        continuation["increment"]["merchant_outcomes"] = None
        self.assertEqual(validator.validate(packet, paid_sweep=sweep), ([], []))
        continuation["increment"]["spend"] = 0
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("increment.spend must equal current minus prior" in error for error in errors))

    def test_incompatible_report_time_cannot_supply_an_increment(self) -> None:
        packet, sweep = paid_audit_packet()
        continuation = packet["paid_audit"]["decisions"][0]["continuation"]
        continuation.update({
            "change_kind": "new_information",
            "prior": {
                "as_of": "2026-11-06T15:00:00+03:00", "spend": 59.15, "platform_outcomes": 1,
                "merchant_outcomes": None, "evidence_ids": ["e1"],
                "currency": "TRY", "timezone": "Europe/Istanbul", "attribution": packet["scope"]["attribution"],
                "report_time": "conversion", "start_date": "2026-11-01",
            },
            "increment": {"spend": 157.58, "platform_outcomes": 0, "merchant_outcomes": None},
        })
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("incomparable scope" in error for error in errors))
        continuation["increment"].update(spend=None, platform_outcomes=None)
        self.assertEqual(validator.validate(packet, paid_sweep=sweep), ([], []))
        packet["scope"]["attribution"] = "different click window"
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("scope.attribution must match" in error for error in errors))

    def test_same_epoch_handoff_blocks_first_read_and_binds_prior(self) -> None:
        packet, sweep = paid_audit_packet()
        row = sweep["entities"][0]
        previous_meta = {
            "as_of": "2026-11-06T15:00:00+03:00", "spend": 59.15, "purchases": 1,
            "currency": "TRY", "timezone": "Europe/Istanbul", "attribution": packet["scope"]["attribution"],
            "report_time": "impression", "start_date": "2026-11-01",
        }
        sweep["decision_handoff"] = {"decisions": [{
            "binding": {field: row[field] for field in ("ad_id", "account_id", "campaign_id", "parent_id", "epoch_id")},
            "prior": {"epoch_id": row["epoch_id"], "as_of": previous_meta["as_of"], "observation": {"meta": previous_meta}},
            "observation": {"meta_change": {"state": "comparable", "deltas": {"spend": 157.58, "purchases": 0}}},
        }]}
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("cannot claim first_read" in error for error in errors))
        continuation = packet["paid_audit"]["decisions"][0]["continuation"]
        continuation.update({
            "change_kind": "new_information",
            "prior": {
                **{key: value for key, value in previous_meta.items() if key != "purchases"},
                "platform_outcomes": 1, "merchant_outcomes": None, "evidence_ids": ["e1"],
            },
            "increment": {"spend": 157.58, "platform_outcomes": 0, "merchant_outcomes": None},
        })
        self.assertEqual(validator.validate(packet, paid_sweep=sweep), ([], []))
        continuation["prior"]["as_of"] = "2026-11-06T14:00:00+03:00"
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("prior.as_of does not match" in error for error in errors))

    def test_independent_active_ids_cannot_be_hidden_by_packet_totals(self) -> None:
        packet, sweep = paid_audit_packet()
        packet["paid_audit"]["decisions"].pop()
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("coverage mismatch" in error and "ad_zero" in error for error in errors))
        sweep["entities"].pop()
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("without exact active decision ID equality" in error for error in errors))

    def test_carried_epoch_history_does_not_replace_current_binding_or_reopen_first_read(self) -> None:
        packet, sweep = paid_audit_packet()
        row = sweep["entities"][0]
        old = {key: row[key] for key in ("account_id", "campaign_id", "parent_id", "ad_id", "epoch_id")}
        row["epoch_id"] = "binding_2"
        current = {**old, "epoch_id": row["epoch_id"]}
        record = packet["paid_audit"]["decisions"][0]
        record["binding_epoch"] = row["epoch_id"]
        continuation = record["continuation"]
        previous = {
            "as_of": "2026-11-06T15:00:00+03:00", "spend": 59.15, "purchases": 1,
            "currency": "TRY", "timezone": "Europe/Istanbul", "attribution": packet["scope"]["attribution"],
            "report_time": "impression", "start_date": "2026-11-01",
        }
        prior = {**old, "as_of": previous["as_of"], "observation": {"meta": previous},
                 "reason": continuation["rationale"], "next_review": {"at": packet["paid_audit"]["as_of"]}}
        carry = {"disposition": "carry", "to_epoch_id": row["epoch_id"]}
        sweep["decision_handoff"] = {"complete_for_decision": True, "decisions": [
            {"binding": old, "status": "rebind", "current": None, "prior": prior, "rebind": carry},
            {"binding": current, "status": "open", "current": current, "prior": prior, "rebind": carry,
             "observation": {"meta_change": {"state": "comparable", "deltas": {"spend": 157.58, "purchases": 0}}}},
        ]}
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("cannot claim first_read" in error for error in errors))
        self.assertFalse(any("binding mismatch" in error for error in errors))
        continuation.update(
            change_kind="new_information",
            prior={**{key: value for key, value in previous.items() if key != "purchases"},
                   "platform_outcomes": 1, "merchant_outcomes": None, "evidence_ids": ["e1"]},
            increment={"spend": 157.58, "platform_outcomes": 0, "merchant_outcomes": None},
        )
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("same continuation reason from decision_handoff" in error for error in errors))
        continuation["rationale"] = "The verified new landing treatment warrants a dated clean-window read; prior ad-ID exposure remains on record."
        self.assertEqual(validator.validate(packet, paid_sweep=sweep), ([], []))
        sweep["decision_handoff"]["decisions"][0]["current"] = old
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("current epoch mismatch" in error for error in errors))

    def test_incomplete_sweep_blocks_general_execution_but_allows_independently_verified_isolated_pause(self) -> None:
        _, sweep = paid_audit_packet()
        sweep["entities"][1].update({
            "parent_id": "set_2", "coverage_state": "missing", "current_paid_delivery": None,
        })
        sweep["complete_for_decision"] = False
        packet = operational_pause_packet()
        packet["schema_version"] = "1.4"
        packet["created_at"] = "2026-11-07T15:10:00+03:00"
        packet["scope"]["report_time"] = sweep["scope"]["report_time"]
        packet["paid_audit"] = {
            "as_of": sweep["scope"]["as_of"], "campaign_id": "campaign_1", "coverage_mode": "isolated_risk_reduction",
            "complete_for_decision": False, "evidence_ids": ["e1"],
            "decisions": [{
                "entity_id": "ad_069", "binding_epoch": "binding_1", "observed_paid_delivery": True,
                "disposition": "rotate", "evidence_ids": ["e1"],
                "action_review": {
                    "rationale": "Exact approved and independently verified source-ad pause.",
                    "parent_effect": "Shared set unchanged; sibling spend is uncertain.",
                    "counterevidence": "One attributed purchase and potential later credit; no comparison result.",
                    "next_read_at": "2026-11-08T15:00:00+03:00",
                },
            }],
        }
        self.assertEqual(validator.validate(packet, paid_sweep=sweep), ([], []))
        sweep["coverage"]["inventory_manifest"]["pagination_complete"] = False
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("complete native parent roster" in error for error in errors))
        sweep["coverage"]["inventory_manifest"]["pagination_complete"] = True
        packet["paid_audit"]["coverage_mode"] = "full_sweep"
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("incomplete paid-sweep" in error for error in errors))
        packet["paid_audit"]["coverage_mode"] = "isolated_risk_reduction"
        sweep["entities"][1]["parent_id"] = "set_1"
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("active sibling/target ad_zero" in error for error in errors))
        sweep["entities"][1]["parent_id"] = "set_2"
        row = sweep["entities"][0]
        sweep["decision_handoff"] = {"decisions": [{
            "binding": {field: row[field] for field in ("ad_id", "account_id", "campaign_id", "parent_id", "epoch_id")},
            "main_retained": True,
        }]}
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("retention_override_evidence_ids" in error for error in errors))
        packet["evidence"].append({
            "id": "retention_override", "label": "verified_fact",
            "claim": "Synthetic owner explicitly overrides retention for this exact ad pause.",
            "source": "fixture exact scope approval", "retrieved_at": packet["created_at"], "limitations": [],
        })
        packet["paid_audit"]["decisions"][0]["action_review"]["retention_override_evidence_ids"] = ["retention_override"]
        self.assertEqual(validator.validate(packet, paid_sweep=sweep), ([], []))
        sweep["entities"][0]["binding_verified"] = False
        errors, _ = validator.validate(packet, paid_sweep=sweep)
        self.assertTrue(any("independently covered target" in error for error in errors))

    def test_paid_audit_shape_is_enforced_by_json_schema(self) -> None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("optional jsonschema package not installed")
        schema_path = SCRIPT.parents[1] / "assets" / "schemas" / "decision-packet.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schema_validator = Draft202012Validator(schema)
        packet, _ = paid_audit_packet()
        self.assertEqual(list(schema_validator.iter_errors(packet)), [])
        packet["paid_audit"]["decisions"][0].pop("continuation")
        self.assertTrue(list(schema_validator.iter_errors(packet)))


class CreativeTestRotationTests(unittest.TestCase):
    @staticmethod
    def qualify(record, row, assessment="adequate"):
        metrics = row["metrics"]["lifecycle"]
        metrics.update(state="observed", source="synthetic lifecycle report")
        for key, value in {"impressions": 450, "lpv": 45, "atc": 2, "checkout": 1, "purchase_value": 80,
                           "cpa": None, "roas": None}.items():
            metrics.setdefault(key, value)
        record["performance_review"] = {
            "window": "lifecycle", "assessment": assessment,
            "observed": {key: metrics[key] for key in ("spend", "impressions", "lpv", "atc", "checkout", "purchases", "purchase_value", "cpa", "roas")},
            "rationale": "Exact source has its own observed exposure.",
            "counterevidence": "Result can backfill; no causal ranking follows.",
        }

    @classmethod
    def qualified_watch(cls, packet, sweep):
        record = next(record for record in packet["paid_audit"]["decisions"] if record["entity_id"] == "ad_069")
        row = next(row for row in sweep["entities"] if row["ad_id"] == "ad_069")
        cls.qualify(record, row)
        row["metrics"]["last_3_closed"] = {"start_date": "2026-11-04", "end_date": "2026-11-06", "checkout": 1,
                                              "state": "observed", "source": "synthetic daily report"}
        condition = {"kind": "metric", "window": {"start_date": "2026-11-07", "end_date": "2026-11-07"},
                     "metric": "checkout", "op": "eq", "value": 0, "source": "synthetic daily report"}
        record["continuation"]["watch_contract"] = {
            "basis": {"kind": "first_checkout", "window": {"start_date": "2026-11-04", "end_date": "2026-11-06"}},
            "question": "Does the first checkout repeat in the next completed exposure window?",
            "due_at": record["continuation"]["next_read_at"], "condition": condition,
            "wait_cost": {"kind": "estimated_range", "currency": "TRY", "lower": 5, "upper": 45,
                          "source": "Synthetic pacing scenario; not a spend cap"},
        }
        return record, row

    @staticmethod
    def rotation_packet(ad_id="ad_zero"):
        packet, sweep = paid_audit_packet()
        packet["plan"].update(exposure_direction="rotate", money_moving=True)
        packet["decision"]["state"] = "act"
        record = next(row for row in packet["paid_audit"]["decisions"] if row["entity_id"] == ad_id)
        record.pop("continuation", None)
        record.update(disposition="rotate", action_review={
            "rationale": "Assess this exact test creative for an approval-gated rotation.",
            "counterevidence": "Other creatives in the set may receive the allocation.",
            "parent_effect": "The parent budget remains unchanged.",
            "next_read_at": "2026-11-08T15:00:00+03:00",
        })
        row = next(item for item in sweep["entities"] if item["ad_id"] == ad_id)
        if ad_id == "ad_zero":
            CreativeTestRotationTests.qualified_watch(packet, sweep)
        else:
            CreativeTestRotationTests.qualify(record, row)
        return packet, sweep, record, row

    @classmethod
    def post_rotation_packet(cls):
        packet, sweep, record, row = cls.rotation_packet()
        packet["scope"]["timezone"] = sweep["scope"]["timezone"] = "America/Chicago"
        row["current_paid_delivery"] = record["observed_paid_delivery"] = True
        row["metrics"]["lifecycle"].update(spend=12.5, purchases=0)
        cls.qualify(record, row)
        row["ad_day_observations"] = [{"date": "2026-11-05", "spend": 12.5, "purchases": 0}]
        anchor = {
            **{key: row[key] for key in ("account_id", "campaign_id", "parent_id", "epoch_id")},
            "ad_id": "paused_sibling",
        }
        sweep["entities"].append({
            **anchor, "binding_verified": True, "configured_status": "PAUSED", "effective_status": "PAUSED",
            "disposition": "historical", "coverage_state": "observed", "current_paid_delivery": False,
        })
        application = {
            "verified": True, "native_status_matches_applied": True,
            "record": {
                **anchor, "action": "pause", "status": "applied_verified",
                "applied_at": "2026-11-05T03:15:00Z", "source": "synthetic mutation journal",
                "readback": {
                    **anchor, "read_at": "2026-11-05T03:20:00Z", "independent": True,
                    "configured_status": "PAUSED", "effective_status": "PAUSED",
                    "source": "synthetic independent Meta status read",
                },
            },
        }
        sweep["decision_handoff"] = {"applications": [application]}
        basis = {
            "kind": "observed_post_rotation", "anchor_ad_id": anchor["ad_id"],
            "window_start": "2026-11-05", "window_end": "2026-11-06",
            "rationale": "The target spent in a closed account day after its sibling was verified paused.",
            "evidence_ids": ["e1"],
        }
        record["action_review"]["creative_test_basis"] = basis
        return packet, sweep, row, application, basis

    def assert_creative_test_basis_error(self, packet, sweep, **options):
        errors, _ = validator.validate(packet, paid_sweep=sweep, **options)
        self.assertTrue(any("creative_test_basis" in error for error in errors), errors)

    def test_creative_test_requires_a_basis_without_changing_ordinary_review(self) -> None:
        packet, sweep, _, _ = self.rotation_packet()
        self.assertEqual(validator.validate(packet, paid_sweep=sweep), ([], []))
        self.assert_creative_test_basis_error(packet, sweep, creative_test=True)
        packet["paid_audit"]["decision_context"] = "creative_test"
        self.assert_creative_test_basis_error(packet, sweep)

    def test_previous_pause_cannot_remain_awaiting_approval_for_current_watch(self) -> None:
        packet, sweep = paid_audit_packet()
        self.qualified_watch(packet, sweep)
        pending = {"remaining_reason": "awaiting_approval", "proposal": {"ad_id": "ad_069", "action": "pause"}}
        sweep["decision_handoff"] = {"remaining_proposals": [pending]}
        errors, _ = validator.validate(packet, paid_sweep=sweep, creative_test=True)
        self.assertTrue(any("ad_069 cannot remain awaiting approval" in error for error in errors), errors)
        pending["remaining_reason"] = "rejected"
        self.assertEqual(validator.validate(packet, paid_sweep=sweep, creative_test=True), ([], []))

    def test_own_performance_basis_requires_positive_sourced_spend_and_evidence(self) -> None:
        packet, sweep, record, row = self.rotation_packet("ad_069")
        row["metrics"]["lifecycle"].update(state="observed", source="synthetic lifecycle report")
        basis = {
            "kind": "observed_ad_performance", "metric_window": "lifecycle",
            "rationale": "The ad's own sourced lifecycle includes paid exposure and one credit.",
            "evidence_ids": ["e1"],
        }
        record["action_review"]["creative_test_basis"] = basis
        self.assertEqual(validator.validate(packet, paid_sweep=sweep, creative_test=True), ([], []))
        for window in ("last_3_closed", "partial_day"):
            with self.subTest(window=window):
                basis["metric_window"] = window
                self.assert_creative_test_basis_error(packet, sweep, creative_test=True)
        basis["metric_window"] = "lifecycle"
        row["metrics"]["lifecycle"]["spend"] = 0
        self.assert_creative_test_basis_error(packet, sweep, creative_test=True)
        row["metrics"]["lifecycle"]["spend"] = 216.73
        basis["evidence_ids"] = ["unbound"]
        self.assert_creative_test_basis_error(packet, sweep, creative_test=True)
        basis["evidence_ids"] = ["e1"]
        basis["rationale"] = " "
        self.assert_creative_test_basis_error(packet, sweep, creative_test=True)

    def test_verified_destination_issue_allows_rotation_without_paid_delivery(self) -> None:
        packet, sweep, record, row = self.rotation_packet()
        packet["paid_audit"]["decision_context"] = "creative_test"
        packet["evidence"][0]["claim"] = "An independent request verifies a broken destination for ad_zero."
        basis = {
            "kind": "verified_independent_issue", "issue_type": "destination", "event_id": "destination-read-1",
            "rationale": "The exact ad destination independently returned an invalid redirect.",
            "evidence_ids": ["e1"],
        }
        record["action_review"]["creative_test_basis"] = basis
        self.assert_creative_test_basis_error(packet, sweep)
        sweep["creative_evidence_events"] = [{
            **{key: row[key] for key in ("account_id", "campaign_id", "parent_id", "ad_id", "epoch_id")},
            "id": "destination-read-1", "event_type": "destination", "state": "confirmed", "verified": True,
            "source": "independent synthetic destination read", "observed_at": sweep["scope"]["as_of"],
            "occurred_at": sweep["scope"]["as_of"],
        }]
        self.assertEqual(validator.validate(packet, paid_sweep=sweep), ([], []))
        sweep["creative_evidence_events"][0]["observed_at"] = "2026-11-08T15:00:00+03:00"
        self.assert_creative_test_basis_error(packet, sweep)
        sweep["creative_evidence_events"][0]["observed_at"] = sweep["scope"]["as_of"]
        basis["issue_type"] = "anticipated_budget_concentration"
        self.assert_creative_test_basis_error(packet, sweep)

    def test_post_rotation_requires_verified_same_parent_pause_and_independent_readback(self) -> None:
        packet, sweep, _, _, _ = self.post_rotation_packet()
        self.assertEqual(validator.validate(packet, paid_sweep=sweep, creative_test=True), ([], []))

        for layer, field, value in (
            ("application", "verified", False),
            ("application", "native_status_matches_applied", False),
            ("record", "action", "activate"),
            ("record", "parent_id", "other_set"),
            ("readback", "independent", False),
            ("readback", "effective_status", "ACTIVE"),
            ("readback", "read_at", None),
        ):
            with self.subTest(layer=layer, field=field):
                packet, sweep, _, application, _ = self.post_rotation_packet()
                records = {"application": application, "record": application["record"],
                           "readback": application["record"]["readback"]}
                records[layer][field] = value
                self.assert_creative_test_basis_error(packet, sweep, creative_test=True)

        packet, sweep, _, _, _ = self.post_rotation_packet()
        sweep["decision_handoff"]["applications"].clear()
        self.assert_creative_test_basis_error(packet, sweep, creative_test=True)

    def test_post_rotation_excludes_pause_day_partial_day_and_zero_spend(self) -> None:
        # The UTC Nov 5 readback occurred on Nov 4 in Chicago.
        for start, end, report_day, spend in (
            ("2026-11-04", "2026-11-06", "2026-11-04", 12.5),
            ("2026-11-05", "2026-11-07", "2026-11-07", 12.5),
            ("2026-11-05", "2026-11-06", "2026-11-04", 12.5),
            ("2026-11-05", "2026-11-06", "2026-11-05", 0),
        ):
            with self.subTest(start=start, end=end, report_day=report_day, spend=spend):
                packet, sweep, row, _, basis = self.post_rotation_packet()
                basis.update(window_start=start, window_end=end)
                row["ad_day_observations"] = [{"date": report_day, "spend": spend, "purchases": 0}]
                self.assert_creative_test_basis_error(packet, sweep, creative_test=True)


if __name__ == "__main__":
    unittest.main()
