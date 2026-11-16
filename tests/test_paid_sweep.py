from __future__ import annotations

import copy
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

from test_account_review import account_review, review_payload


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location("paid_sweep", SCRIPTS / "paid_sweep.py")
assert SPEC and SPEC.loader
paid_sweep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paid_sweep)


def sweep_fixture(specs=None):
    scope = {
        "platform": "synthetic", "account_id": "acc", "campaign_id": "test", "currency": "USD",
        "timezone": "America/Chicago", "as_of": "2026-11-07T21:00:00+00:00", "lifecycle_start": "2026-10-29",
        "attribution": "7d click / 1d view", "report_time": "impression",
    }
    start = date.fromisoformat(scope["lifecycle_start"])
    end = date(2026, 11, 7)
    days = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]

    def manifest(source_id, **extra):
        return {**scope, "source_id": source_id, "retrieved_at": scope["as_of"], "complete": True,
                "pagination_complete": True, "query_scope_evidence": "all pages of a named independent synthetic query",
                "start_date": days[0], "end_date": days[-1], **extra}

    parent = {"account_id": "acc", "campaign_id": "test", "parent_id": "set1", "configured_status": "ACTIVE",
              "effective_status": "ACTIVE", "daily_budget": 135, "currency": "USD"}
    specs = specs or [("a", "ACTIVE", 210, 1, 400), ("b", "ACTIVE", 210, 3, 90),
                      ("c", "ACTIVE", 255, 0, 0), ("d", "ACTIVE", 0, 0, 0), ("e", "PAUSED", 20, 0, 0)]
    ads, full, daily = [], [], []
    for ad_id, status, spend, count, value in specs:
        ident = {"account_id": "acc", "campaign_id": "test", "parent_id": "set1", "ad_id": ad_id}
        ads.append({**ident, "epoch_id": f"epoch-{ad_id}", "binding_verified": True, "lifecycle_start": days[0],
                    "epoch_started_at": "2026-11-04T16:00:00+00:00", "configured_status": status,
                    "effective_status": status})
        each = spend // len(days)
        for day in days:
            daily.append({**ident, "date": day, "spend": each + (spend % len(days) if day == days[-1] else 0),
                          "impressions": 2 if spend else 0, "lpv": 1 if spend else 0, "atc": 0, "checkout": 0,
                          "actions": {"canonical": count, "omni_alias": count} if day == "2026-11-04" and count else {},
                          "action_values": {"canonical-value": value, "omni-value": value} if day == "2026-11-04" and count else {}})
        full.append({**ident, "spend": spend, "impressions": 2 * len(days) if spend else 0, "lpv": len(days) if spend else 0,
                     "atc": 0, "checkout": 0, "actions": {"canonical": count, "omni_alias": count} if count else {},
                     "action_values": {"canonical-value": value, "omni-value": value} if count else {}})
    mapping = {"count_action_type": "canonical", "value_action_type": "canonical-value", "evidence": "synthetic provider mapping",
               "count_aliases": ["omni_alias"], "value_currency": "USD", "missing_count_is_zero": True,
               "missing_value_for_zero_count_is_zero": True}
    totals = {key: sum(row[key] for row in full) for key in ("spend", "impressions", "lpv", "atc", "checkout")}
    totals.update(purchases=sum(row[3] for row in specs), purchase_value=sum(row[4] for row in specs))
    return {"scope": scope, "inventory": {"manifest": manifest("native_inventory", independent=True), "parents": [parent], "ads": ads},
            "lifecycle": {"manifest": manifest("lifecycle_read", grain="ad", mapping=copy.deepcopy(mapping)), "rows": full},
            "ad_days": {"manifest": manifest("daily_read", grain="ad_day", mapping=copy.deepcopy(mapping)), "rows": daily},
            "controls": {"manifest": manifest("independent_campaign_control", grain="campaign_and_parent", independent=True), "totals": totals}}


def entities(result):
    return {row["ad_id"]: row for row in result["entities"]}


class PaidSweepTests(unittest.TestCase):
    def test_lifecycle_closed_windows_partial_and_clean_epoch_are_distinct(self):
        result = paid_sweep.sweep(sweep_fixture(), top=1)
        self.assertTrue(result["complete_for_decision"])
        by_id = entities(result)
        metrics = by_id["a"]["metrics"]
        self.assertEqual((metrics["lifecycle"]["spend"], metrics["last_7_closed"]["spend"],
                          metrics["last_3_closed"]["spend"], metrics["partial_day"]["spend"]), (210, 147, 63, 21))
        self.assertEqual(metrics["lifecycle"]["last_purchase_report_date"], "2026-11-04")
        self.assertEqual(metrics["lifecycle"]["spend_after_last_purchase_report_date"], 63)
        self.assertEqual(metrics["current_epoch"]["start_date"], "2026-11-05")
        self.assertEqual(metrics["current_epoch"]["purchases"], 0)
        self.assertEqual(metrics["lifecycle"]["purchases"], 1)
        self.assertEqual(result["lanes"]["paid_zero_purchase_by_spend"], ["c"])
        self.assertIsNone(by_id["c"]["metrics"]["lifecycle"]["cpa"])
        self.assertEqual(by_id["d"]["observation_state"], "OBSERVED_ZERO")
        self.assertEqual(by_id["e"]["disposition"], "historical")
        partial = by_id["a"]["ad_day_observations"][-1]
        self.assertEqual({key: partial[key] for key in ("date", "spend", "purchases", "purchase_value")},
                         {"date": "2026-11-07", "spend": 21, "purchases": 0, "purchase_value": 0})
        for key in ("impressions", "lpv", "atc", "checkout"):
            self.assertEqual(partial[key], by_id["a"]["metrics"]["partial_day"][key])
        self.assertEqual(result["coverage"]["expected_active_ids"], ["a", "b", "c", "d"])
        self.assertEqual(len(result["summary"]["top"]["positive_purchase_by_spend"]), 1)
        self.assertEqual(len(result["lanes"]["positive_purchase_by_spend"]), 2)

    def test_count_value_rank_conflict_does_not_choose_a_winner(self):
        result = paid_sweep.sweep(sweep_fixture())
        self.assertEqual(result["lanes"]["count_value_conflict_ids"], ["a", "b"])
        self.assertEqual(result["lanes"]["positive_purchase_by_attributed_value"], ["a", "b"])
        self.assertEqual(result["lanes"]["positive_purchase_by_low_roas"], ["b", "a"])
        self.assertEqual(entities(result)["b"]["metrics"]["lifecycle"]["purchase_value"], 90)
        self.assertNotIn("decision", entities(result)["a"])

    def test_missing_expected_zero_spend_ad_cannot_hide_behind_exact_controls(self):
        payload = sweep_fixture()
        for key in ("lifecycle", "ad_days"):
            payload[key]["rows"] = [row for row in payload[key]["rows"] if row["ad_id"] != "d"]
        result = paid_sweep.sweep(payload)
        self.assertTrue(result["control_reconciliation"]["by_dataset"]["lifecycle"]["campaign"]["exact"])
        self.assertFalse(result["complete_for_decision"])
        self.assertEqual(result["coverage"]["sources"]["lifecycle"]["missing_ids"], ["d"])
        self.assertEqual(entities(result)["d"]["observation_state"], "MISSING")
        self.assertIsNone(entities(result)["d"]["metrics"]["lifecycle"]["spend"])

    def test_sparse_requires_provider_semantics_exact_parent_controls_and_complete_pages(self):
        payload = sweep_fixture()
        for key in ("lifecycle", "ad_days"):
            payload[key]["rows"] = [row for row in payload[key]["rows"] if row["ad_id"] != "d"]
            payload[key]["manifest"]["sparse_no_delivery_evidence"] = "this query omits verified no-delivery cells"
        self.assertFalse(paid_sweep.sweep(payload)["complete_for_decision"])
        payload["controls"]["parents"] = [{"parent_id": "set1", "totals": dict(payload["controls"]["totals"])}]
        result = paid_sweep.sweep(payload)
        self.assertTrue(result["complete_for_decision"])
        self.assertEqual(entities(result)["d"]["observation_state"], "SPARSE_NO_DELIVERY")
        self.assertEqual(entities(result)["d"]["metrics"]["lifecycle"]["spend"], 0)
        self.assertEqual(result["coverage"]["sources"]["ad_days"]["sparse_no_delivery_ids"], ["d"])
        payload["ad_days"]["manifest"]["pagination_complete"] = False
        result = paid_sweep.sweep(payload)
        self.assertFalse(result["complete_for_decision"])
        self.assertNotEqual(entities(result)["d"]["observation_state"], "SPARSE_NO_DELIVERY")

    def test_unreported_ad_dates_never_become_observed_zeros(self):
        payload = sweep_fixture()
        payload["ad_days"]["rows"] = [row for row in payload["ad_days"]["rows"]
                                     if (row["ad_id"], row["date"]) != ("d", "2026-11-07")]
        result = paid_sweep.sweep(payload)
        self.assertTrue(result["complete_for_decision"])
        row = entities(result)["d"]["metrics"]["partial_day"]
        self.assertEqual(row["unreported_dates"], ["2026-11-07"])
        self.assertEqual(row["state"], "missing")
        self.assertIsNone(row["spend"])

    def test_duplicate_ad_day_even_at_exact_controls_is_not_complete(self):
        payload = sweep_fixture()
        zero = next(row for row in payload["ad_days"]["rows"] if row["ad_id"] == "d")
        payload["ad_days"]["rows"].append(copy.deepcopy(zero))
        result = paid_sweep.sweep(payload)
        self.assertTrue(result["control_reconciliation"]["by_dataset"]["ad_days"]["campaign"]["exact"])
        self.assertFalse(result["complete_for_decision"])
        self.assertEqual(result["coverage"]["sources"]["ad_days"]["duplicate_keys"],
                         [{"ad_id": "d", "date": zero["date"], "rows": 2}])
        self.assertIn("duplicate_grain_key", entities(result)["d"]["issues"])

    def test_native_parent_epoch_drift_and_unmapped_status_are_visible(self):
        payload = sweep_fixture()
        payload["lifecycle"]["rows"][0].update(parent_id="different", epoch_id="stale-creative")
        payload["inventory"]["ads"][1].update(configured_status="PAUSED", effective_status="IN_PROCESS")
        result = paid_sweep.sweep(payload)
        self.assertFalse(result["complete_for_decision"])
        self.assertIn("parent_drift", entities(result)["a"]["issues"])
        self.assertIn("snapshot_epoch_drift", entities(result)["a"]["issues"])
        self.assertIn("b", result["coverage"]["expected_active_ids"])
        self.assertIn("configured_effective_status_unresolved", entities(result)["b"]["issues"])

    def test_extra_metrics_only_id_is_preserved_but_never_a_live_candidate(self):
        payload = sweep_fixture()
        extra = {**payload["lifecycle"]["rows"][3], "ad_id": "extra"}
        payload["lifecycle"]["rows"].append(extra)
        result = paid_sweep.sweep(payload)
        self.assertFalse(result["complete_for_decision"])
        self.assertEqual(result["coverage"]["sources"]["lifecycle"]["extra_ids"], ["extra"])
        self.assertEqual(entities(result)["extra"]["disposition"], "unresolved")
        self.assertNotIn("extra", result["coverage"]["expected_active_ids"])

    def test_partial_day_credit_does_not_replace_the_closed_windows(self):
        payload = sweep_fixture()
        for row in payload["ad_days"]["rows"]:
            if row["ad_id"] == "a" and row["date"] == "2026-11-04":
                row.update(actions={}, action_values={})
            if row["ad_id"] == "a" and row["date"] == "2026-11-07":
                row.update(actions={"canonical": 1}, action_values={"canonical-value": 400})
        result = paid_sweep.sweep(payload)
        self.assertTrue(result["complete_for_decision"])
        metrics = entities(result)["a"]["metrics"]
        self.assertEqual(metrics["lifecycle"]["purchases"], 1)
        self.assertEqual(metrics["last_3_closed"]["purchases"], 0)
        self.assertEqual(metrics["last_7_closed"]["purchases"], 0)
        self.assertEqual(metrics["partial_day"]["purchases"], 1)
        self.assertTrue(result["windows"]["partial_day"]["partial"])

    def test_verified_current_binding_without_known_boundary_keeps_lifecycle(self):
        payload = sweep_fixture()
        payload["inventory"]["ads"][0]["epoch_started_at"] = None
        result = paid_sweep.sweep(payload)
        self.assertTrue(result["complete_for_decision"])
        metrics = entities(result)["a"]["metrics"]
        self.assertEqual(metrics["lifecycle"]["spend"], 210)
        self.assertEqual(metrics["current_epoch"]["state"], "epoch_start_unknown")
        self.assertIsNone(metrics["current_epoch"]["purchases"])

    def test_alias_missing_value_currency_and_valid_zero_are_different(self):
        payload = sweep_fixture()
        del payload["lifecycle"]["rows"][0]["actions"]["canonical"]
        payload["lifecycle"]["rows"][1]["value_currency"] = "EUR"
        result = paid_sweep.sweep(payload)
        self.assertFalse(result["complete_for_decision"])
        by_id = entities(result)
        self.assertIn("ALIAS_UNMAPPED", by_id["a"]["issues"])
        self.assertIsNone(by_id["a"]["metrics"]["lifecycle"]["purchases"])
        self.assertIn("VALUE_UNVERIFIED", by_id["b"]["issues"])
        self.assertEqual(by_id["b"]["metrics"]["lifecycle"]["purchases"], 3)
        self.assertIsNone(by_id["b"]["metrics"]["lifecycle"]["roas"])
        self.assertEqual(by_id["c"]["metrics"]["lifecycle"]["purchase_value"], 0)

    def test_scope_mismatch_does_not_pass_on_matching_totals(self):
        for key, different in (("currency", "EUR"), ("timezone", "UTC"), ("report_time", "conversion"),
                               ("attribution", "7d click"), ("start_date", "2026-11-01")):
            with self.subTest(key=key):
                payload = sweep_fixture()
                payload["ad_days"]["manifest"][key] = different
                result = paid_sweep.sweep(payload)
                self.assertFalse(result["complete_for_decision"])
                self.assertTrue(result["control_reconciliation"]["by_dataset"]["ad_days"]["campaign"]["exact"])

    def test_unqueried_daily_is_not_a_zero_or_an_unobserved_lifecycle(self):
        payload = sweep_fixture()
        payload["ad_days"]["manifest"].update(availability="unqueried", complete=False, pagination_complete=False)
        payload["ad_days"]["rows"] = []
        result = paid_sweep.sweep(payload)
        row = entities(result)["a"]
        self.assertFalse(result["complete_for_decision"])
        self.assertEqual(row["observation_state"], "UNQUERIED")
        self.assertEqual(row["metrics"]["lifecycle"]["spend"], 210)
        self.assertIsNone(row["metrics"]["last_3_closed"]["spend"])

    def test_residual_held_unallocated_with_scope_provenance(self):
        payload = sweep_fixture()
        payload["controls"]["totals"]["spend"] -= 0.75
        self.assertFalse(paid_sweep.sweep(payload)["complete_for_decision"])
        payload["controls"]["residual_policy"] = {"spend": {"absolute_tolerance": 0.75, "evidence": "separate partial-day reads",
                                                            "impact": "do not assign read-time drift to an entity"}}
        result = paid_sweep.sweep(payload)
        self.assertTrue(result["complete_for_decision"])
        self.assertEqual(result["control_reconciliation"]["by_dataset"]["lifecycle"]["campaign"]["metrics"]["spend"]["residual"], .75)
        self.assertFalse(result["control_reconciliation"]["residuals_allocated"])
        self.assertEqual(entities(result)["a"]["metrics"]["lifecycle"]["spend"], 210)

    def test_anonymous_campaign_shape_keeps_170_and_low_count_rows(self):
        specs = [(f"positive-{i:02}", "ACTIVE", 180 + i * 17, 1 + i % 2, 40 + i * 5) for i in range(15)]
        specs += [(f"zero-{i:03}", "ACTIVE", 3 + i, 0, 0) for i in range(115)]
        specs += [(f"unspent-{i}", "ACTIVE", 0, 0, 0) for i in range(3)]
        specs += [(f"historical-{i:02}", "PAUSED", 275, 2, 400) for i in range(37)]
        result = paid_sweep.sweep(sweep_fixture(specs), top=2)
        self.assertTrue(result["complete_for_decision"])
        self.assertEqual((len(result["entities"]), result["summary"]["active_decision_count"],
                          result["summary"]["historical_count"]), (170, 133, 37))
        self.assertEqual(len(result["lanes"]["positive_purchase_by_cpa"]), 15)
        self.assertTrue({f"positive-{i:02}" for i in range(7)} <= set(result["lanes"]["positive_purchase_by_cpa"]))
        self.assertEqual(len(result["lanes"]["paid_zero_purchase_by_spend"]), 115)
        self.assertEqual(len(result["lanes"]["zero_exposure_ids"]), 3)
        self.assertEqual(len(result["summary"]["top"]["positive_purchase_by_cpa"]), 2)

    def test_original_trend_repro_rejects_missing_id_despite_exact_aggregate(self):
        payload = review_payload()
        payload["scope"]["expected_active_entity_ids"] = ["observed_active", "omitted_active"]
        for key, period in zip(("current_entities", "prior_entities"), reversed(payload["periods"][-2:])):
            payload[key] = [{"id": "observed_active", "numerator": period["numerator"], "denominator": period["denominator"]}]
        with self.assertRaisesRegex(account_review.InputError, "omitted_active.*paid-sweep"):
            account_review.review(payload)
        payload["current_entities"].append({"id": "omitted_active", "numerator": 0, "denominator": 0})
        result = account_review.review(payload)
        self.assertEqual({row["id"] for row in result["entity_change_descriptors"]["entities"]}, {"observed_active", "omitted_active"})

    def test_cli_retains_census_and_reports_missing_handoff_decisions(self):
        payload = sweep_fixture()
        payload["decision_handoff"] = {"scope": {"account_id": "incorrect"}, "current_rows": []}
        process = subprocess.run([sys.executable, str(SCRIPTS / "account_review.py"), "paid-sweep", "--input", "-", "--top", "1"],
                                 input=json.dumps(payload), capture_output=True, text=True, check=True)
        wrapper = json.loads(process.stdout)
        self.assertTrue(wrapper["ok"])
        result = wrapper["result"]
        self.assertEqual(len(result["entities"]), 5)
        self.assertTrue(result["complete_for_decision"])
        self.assertTrue(result["decision_handoff"]["complete_for_decision"])
        self.assertEqual(result["decision_handoff"]["scope"]["account_id"], "acc")
        self.assertEqual(result["missing_current_decision_ids"], ["a", "b", "c", "d"])
        self.assertFalse(result["audit_ready"])


if __name__ == "__main__":
    unittest.main()
