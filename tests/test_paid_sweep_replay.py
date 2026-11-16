"""Synthetic regression with an audit-sized population; no account or order data."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "account_review.py"
COUNT = "canonical_purchase_count"
VALUE = "canonical_purchase_value"


def fixture() -> dict:
    scope = {
        "platform": "meta", "account_id": "synthetic-account", "campaign_id": "synthetic-test",
        "currency": "USD", "timezone": "America/Chicago", "as_of": "2026-11-07T17:00:00Z",
        "lifecycle_start": "2026-10-29", "attribution": "synthetic unified 7dc + 1dv", "report_time": "impression",
    }
    key = {name: scope[name] for name in ("account_id", "campaign_id")}

    def manifest(source, grain, independent=False):
        return {
            **scope, "source_id": source, "grain": grain, "independent": independent,
            "retrieved_at": scope["as_of"], "complete": True, "pagination_complete": True,
            "start_date": "2026-10-29", "end_date": "2026-11-07",
            "query_scope_evidence": "synthetic full response with terminal pagination",
        }

    mapping = {
        "count_action_type": COUNT, "value_action_type": VALUE, "count_aliases": ["purchase_alias"],
        "missing_count_is_zero": True, "missing_value_for_zero_count_is_zero": True,
        "evidence": "synthetic documented canonical count and value mapping",
    }
    parents = [
        {**key, "parent_id": f"set-{i:02}", "configured_status": "ACTIVE", "effective_status": "ACTIVE", "daily_budget": 135, "currency": "USD"}
        for i in range(1, 16)
    ]
    positives = [
        (216.73, 1, 80), (324, 1, 103), (235, 1, 110), (280, 1, 120), (355, 2, 180), (295, 1, 110), (309, 2, 99),
        (210, 1, 400), (210, 3, 90), (255, 3, 670), (400, 5, 460), (160, 2, 180), (180, 2, 220), (55, 1, 180), (78, 1, 120),
    ]
    ads, full, days = [], [], []
    for index in range(1, 171):
        ad_id = f"ad-{index:03}"
        parent_id = "set-15" if index in (1, 2) else f"set-{(index - 3) % 14 + 1:02}"
        identity = {**key, "ad_id": ad_id, "parent_id": parent_id}
        status = "ACTIVE" if index <= 133 else "PAUSED"
        epoch_start = "2026-11-04T17:00:00Z" if index == 7 else None
        ads.append({
            **identity, "epoch_id": ad_id + ":v2" if epoch_start else ad_id + ":v1",
            "configured_status": status, "effective_status": status, "binding_verified": True,
            "lifecycle_start": scope["lifecycle_start"], "epoch_started_at": epoch_start,
        })
        if index <= len(positives):
            spend, purchases, value = positives[index - 1]
        elif index == 16:
            spend, purchases, value = 380, 0, 0
        elif 131 <= index <= 133:
            spend, purchases, value = 0, 0, 0
        else:
            spend, purchases, value = 2 + index % 40, 0, 0

        def metric(amount, count, worth):
            return {
                **identity, "spend": float(amount), "impressions": int(amount) * 10,
                "lpv": int(amount) // 4, "atc": int(count), "checkout": int(count),
                "actions": {COUNT: count, "purchase_alias": count} if count else {},
                "action_values": {VALUE: worth} if count else {}, "value_currency": "USD",
            }

        # Preserve a partial-day-only credit, a mixed V2 boundary day and a
        # recovery with two later credits without turning any into a cutoff.
        n = 7 if index <= 9 else 6
        spend_parts = [Decimal(str(spend)) - Decimal(n - 1)] + [Decimal(1)] * (n - 1) if spend >= n else [Decimal(str(spend))] + [Decimal(0)] * (n - 1)
        count_parts, value_parts = [0] * n, [0] * n
        if index == 1:
            spend_parts = list(map(Decimal, ("59.15", "0", "0", "0", "0", "100", "57.58")))
            count_parts[0], value_parts[0] = purchases, value
        elif index == 10:
            spend_parts = list(map(Decimal, ("160.52", "0", "0", "20", "40", "34.48")))
            count_parts[0], count_parts[4], count_parts[5] = 1, 1, 1
            value_parts[0], value_parts[4], value_parts[5] = 230, 220, 220
        elif index == 6:
            count_parts[-1], value_parts[-1] = purchases, value
        elif index == 7:
            count_parts[3], count_parts[5] = 1, 1
            value_parts[3], value_parts[5] = 45, 54
        else:
            count_parts[0], value_parts[0] = purchases, value
        day_rows = [
            {**metric(amount, count, worth), "date": (date(2026, 11, 1) + timedelta(days=day)).isoformat()}
            for day, (amount, count, worth) in enumerate(zip(spend_parts, count_parts, value_parts))
        ]
        aggregate = metric(spend, purchases, value)
        for name in ("impressions", "lpv", "atc", "checkout"):
            aggregate[name] = sum(row[name] for row in day_rows)
        full.append(aggregate)
        days.extend(day_rows)

    def totals(rows):
        return {
            "spend": float(sum(Decimal(str(r["spend"])) for r in rows)),
            **{name: sum(r[name] for r in rows) for name in ("impressions", "lpv", "atc", "checkout")},
            "purchases": sum(r["actions"].get(COUNT, 0) for r in rows),
            "purchase_value": sum(r["action_values"].get(VALUE, 0) for r in rows),
        }

    return {
        "scope": scope,
        "inventory": {"manifest": manifest("native", "native_inventory", True), "ads": ads, "parents": parents},
        "lifecycle": {"manifest": {**manifest("lifetime", "ad"), "mapping": mapping}, "rows": full},
        "ad_days": {"manifest": {**manifest("daily", "ad_day"), "mapping": mapping}, "rows": days},
        "controls": {"manifest": manifest("campaign-control", "campaign_and_parent", True), "totals": totals(full)},
    }


def run_sweep(payload, top=2):
    run = subprocess.run(
        [sys.executable, str(SCRIPT), "paid-sweep", "--input", "-", "--top", str(top)],
        input=json.dumps(payload), text=True, capture_output=True, check=False,
    )
    if not run.stdout:
        raise AssertionError(run.stderr)
    envelope = json.loads(run.stdout)
    return run.returncode, envelope["result"]


class FullPaidSweepReplayTests(unittest.TestCase):
    def test_inventory_and_both_candidate_lanes_survive_top_n(self):
        status, result = run_sweep(fixture())
        self.assertEqual(status, 0, result.get("coverage"))
        self.assertTrue(result["complete_for_decision"], result.get("coverage"))
        rows = {r["ad_id"]: r for r in result["entities"]}
        self.assertEqual(len(rows), 170)
        self.assertEqual(Counter(r["disposition"] for r in rows.values())['active_decision'], 133)
        active = [r for r in rows.values() if r["disposition"] == "active_decision"]
        positives = [r for r in active if r["metrics"]["lifecycle"]["purchases"] > 0]
        zero = [r for r in active if r["metrics"]["lifecycle"]["purchases"] == 0 and r["metrics"]["lifecycle"]["spend"] > 0]
        self.assertEqual((len(positives), len(zero), len(active) - len(positives) - len(zero)), (15, 115, 3))
        self.assertTrue({f"ad-{i:03}" for i in range(1, 8)} <= set(result["lanes"]["positive_purchase_by_cpa"]))
        self.assertEqual(len(result["summary"]["top"]["positive_purchase_by_cpa"]), 2)
        for i in range(1, 8):
            row = rows[f"ad-{i:03}"]["metrics"]["lifecycle"]
            self.assertIn(row["purchases"], (1, 2))
            self.assertLess(row["purchase_value"], row["spend"])
        self.assertIsNone(rows["ad-016"]["metrics"]["lifecycle"]["cpa"])
        self.assertEqual(rows["ad-006"]["metrics"]["partial_day"]["purchases"], 1)
        self.assertEqual(rows["ad-006"]["metrics"]["last_3_closed"]["purchases"], 0)
        self.assertEqual(rows["ad-007"]["metrics"]["current_epoch"]["purchases"], 1)
        self.assertGreater(rows["ad-008"]["metrics"]["lifecycle"]["roas"], 1)
        self.assertLess(rows["ad-009"]["metrics"]["lifecycle"]["roas"], 1)
        self.assertEqual(rows["ad-010"]["metrics"]["last_3_closed"]["purchase_value"], 440)
        self.assertAlmostEqual(rows["ad-010"]["metrics"]["last_3_closed"]["spend"], 94.48, places=2)
        self.assertNotEqual(rows["ad-134"]["disposition"], "active_decision")

    def test_equal_aggregate_does_not_certify_an_absent_active_id(self):
        payload = fixture()
        for name in ("lifecycle", "ad_days"):
            payload[name]["rows"] = [r for r in payload[name]["rows"] if r["ad_id"] != "ad-133"]
        _, result = run_sweep(payload)
        self.assertFalse(result["complete_for_decision"])
        self.assertEqual(result["coverage"]["sources"]["lifecycle"]["missing_ids"], ["ad-133"])
        self.assertTrue(result["control_reconciliation"]["by_dataset"]["lifecycle"]["campaign"]["exact"])
        row = next(r for r in result["entities"] if r["ad_id"] == "ad-133")
        self.assertIsNone(row["metrics"]["lifecycle"]["spend"])
        self.assertIsNone(row["current_paid_delivery"])

    def test_later_source_is_not_evidence_at_the_earlier_read(self):
        payload = fixture()
        payload["ad_days"]["manifest"]["retrieved_at"] = "2026-11-07T19:00:00Z"
        _, result = run_sweep(payload)
        self.assertFalse(result["complete_for_decision"])
        self.assertIn("ad_days:source_retrieved_after_as_of", result["coverage"]["sources"]["ad_days"]["issues"])


if __name__ == "__main__":
    unittest.main()
