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
        "schema_version": "1.1",
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
                "financial_exposure": "+20 TRY per active day"
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
            "query": "read ad_set_101 daily_budget and status",
            "success_predicate": "daily_budget equals 120 TRY and all unapproved fields remain unchanged",
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
