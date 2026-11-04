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


if __name__ == "__main__":
    unittest.main()
