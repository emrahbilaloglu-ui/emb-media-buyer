from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
