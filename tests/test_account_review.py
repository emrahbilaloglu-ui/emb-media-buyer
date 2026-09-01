from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "account_review.py"
SPEC = importlib.util.spec_from_file_location("account_review", SCRIPT)
assert SPEC and SPEC.loader
account_review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(account_review)


def benchmark_payload() -> dict:
    return {
        "metric": {
            "name": "CPA",
            "unit": "USD_per_purchase",
            "direction": "lower_is_better",
            "value_mode": "ratio",
            "multiplier": 1,
        },
        "peer_group": {
            "advertiser_id": "adv_example",
            "objective": "WEB_CONVERSIONS",
            "grain": "campaign",
            "market": "US",
            "automation_mode": "regular",
            "bid_strategy": "maximum_delivery",
            "optimization_event": "PURCHASE",
            "attribution": "account_setting_snapshot",
            "window": "2026-08-01/2026-08-31",
            "timezone": "Europe/Istanbul",
            "metric_definition": "spend / attributed purchase count",
            "source": "TikTok integrated report snapshot",
            "report_latency": "retrieved after complete reporting lag",
            "eligibility_basis": "all campaigns with the required metric inputs and complete delivery window",
            "expected_entity_count": 4,
            "missing_or_ineligible_entities": [],
            "comparability_confirmed": True,
            "comparability_evidence": "same advertiser, objective, grain, event, attribution and complete window",
            "lag_state": "complete",
            "lag_basis": "all campaigns observed through the selected conversion lag",
        },
        "entities": [
            {"id": "a", "numerator": 100, "denominator": 10},
            {"id": "b", "numerator": 400, "denominator": 20},
            {"id": "c", "numerator": 900, "denominator": 30},
            {"id": "d", "numerator": 1600, "denominator": 40},
        ],
    }


def review_payload() -> dict:
    return {
        "metric": {
            "name": "CPA",
            "unit": "USD_per_purchase",
            "direction": "lower_is_better",
            "multiplier": 1,
        },
        "scope": {
            "advertiser_id": "adv_example",
            "objective": "WEB_CONVERSIONS",
            "business_outcome": "settled new-customer purchase",
            "grain": "account",
            "timezone": "Europe/Istanbul",
            "source": "TikTok report snapshot",
            "metric_definition": "total spend / total attributed purchases",
            "report_latency": "retrieved after the selected conversion lag",
            "comparability_confirmed": True,
            "comparability_evidence": "equal complete weeks with unchanged metric definitions",
            "lag_state": "complete",
            "lag_basis": "both weeks observed through the selected conversion lag",
        },
        "periods": [
            {
                "label": "W1",
                "start": "2026-08-03T00:00:00+03:00",
                "end": "2026-08-10T00:00:00+03:00",
                "numerator": 600,
                "denominator": 6,
            },
            {
                "label": "W2",
                "start": "2026-08-10T00:00:00+03:00",
                "end": "2026-08-17T00:00:00+03:00",
                "numerator": 700,
                "denominator": 7,
            },
            {
                "label": "W3",
                "start": "2026-08-17T00:00:00+03:00",
                "end": "2026-08-24T00:00:00+03:00",
                "numerator": 800,
                "denominator": 8,
            },
            {
                "label": "W4",
                "start": "2026-08-24T00:00:00+03:00",
                "end": "2026-08-31T00:00:00+03:00",
                "numerator": 900,
                "denominator": 10,
            },
        ],
    }


class AccountReviewTests(unittest.TestCase):
    def test_benchmark_quantiles_and_direction(self) -> None:
        result = account_review.benchmark(benchmark_payload())
        self.assertAlmostEqual(result["distribution"]["p25"], 17.5)
        self.assertAlmostEqual(result["distribution"]["p50"], 25)
        self.assertAlmostEqual(result["distribution"]["p75"], 32.5)
        by_id = {item["id"]: item for item in result["entities"]}
        self.assertAlmostEqual(by_id["a"]["performance_percentile_midrank"], 87.5)
        self.assertAlmostEqual(by_id["d"]["performance_percentile_midrank"], 12.5)
        self.assertIn("do not establish profitability", result["interpretation_limits"][0])

    def test_benchmark_rejects_unqualified_peer_group(self) -> None:
        payload = benchmark_payload()
        payload["peer_group"]["comparability_confirmed"] = False
        with self.assertRaisesRegex(account_review.InputError, "comparability_confirmed"):
            account_review.benchmark(payload)

        payload = benchmark_payload()
        payload["entities"][0]["denominator"] = 0
        with self.assertRaisesRegex(account_review.InputError, "denominator must be > 0"):
            account_review.benchmark(payload)

        payload = benchmark_payload()
        payload["peer_group"]["expected_entity_count"] = 5
        with self.assertRaisesRegex(account_review.InputError, "must equal eligible"):
            account_review.benchmark(payload)

    def test_benchmark_direct_multiplier_higher_is_better_and_n2(self) -> None:
        payload = benchmark_payload()
        payload["metric"].update(
            {
                "direction": "higher_is_better",
                "value_mode": "direct",
                "multiplier": 100,
            }
        )
        payload["peer_group"]["expected_entity_count"] = 2
        payload["entities"] = [
            {"id": "a", "value": 0.10},
            {"id": "b", "value": 0.20},
        ]
        result = account_review.benchmark(payload)
        self.assertAlmostEqual(result["distribution"]["p25"], 12.5)
        self.assertAlmostEqual(result["distribution"]["p50"], 15)
        self.assertAlmostEqual(result["distribution"]["p75"], 17.5)
        by_id = {item["id"]: item for item in result["entities"]}
        self.assertAlmostEqual(by_id["a"]["performance_percentile_midrank"], 25)
        self.assertAlmostEqual(by_id["b"]["performance_percentile_midrank"], 75)

    def test_benchmark_ties_have_midrank_without_false_resolution(self) -> None:
        payload = benchmark_payload()
        payload["peer_group"]["expected_entity_count"] = 3
        payload["entities"] = [
            {"id": "a", "numerator": 100, "denominator": 10},
            {"id": "b", "numerator": 100, "denominator": 10},
            {"id": "c", "numerator": 100, "denominator": 10},
        ]
        result = account_review.benchmark(payload)
        self.assertEqual(result["distribution"]["distinct_value_count"], 1)
        self.assertEqual(result["distribution"]["p25"], 10)
        for item in result["entities"]:
            self.assertEqual(item["tie_count"], 3)
            self.assertEqual(item["performance_percentile_midrank"], 50)

    def test_funnel_arithmetic_and_baseline(self) -> None:
        result = account_review.funnel(
            {
                "context": {
                    "funnel_name": "settled commerce",
                    "source": "advertiser analytics and order ledger",
                    "window": "2026-08-24/2026-08-31",
                    "timezone": "Europe/Istanbul",
                    "identity_unit": "unique session progressing to unique settled order",
                    "deduplication_state": "verified at each stage",
                    "count_semantics": "unique_entities",
                    "stage_chain_expected_nonincreasing": True,
                    "lag_state": "complete",
                    "lag_basis": "orders settled through the refund lag",
                },
                "stages": [
                    {"name": "session", "count": 1000},
                    {"name": "checkout", "count": 100},
                    {"name": "settled_order", "count": 40},
                ],
                "comparison": {
                    "window": "2026-08-17/2026-08-24",
                    "comparability_confirmed": True,
                    "comparability_evidence": "same source, market, offer and complete seven-day window",
                    "lag_state": "complete",
                    "lag_basis": "orders settled through the same refund lag",
                    "stages": [
                        {"name": "session", "count": 800},
                        {"name": "checkout", "count": 80},
                        {"name": "settled_order", "count": 24},
                    ],
                },
            }
        )
        self.assertAlmostEqual(result["overall_first_to_last_rate"], 0.04)
        transition = result["comparison"]["transitions"][1]
        self.assertAlmostEqual(transition["current_rate"], 0.4)
        self.assertAlmostEqual(transition["comparison_rate"], 0.3)
        self.assertAlmostEqual(transition["absolute_rate_change"], 0.1)

    def test_funnel_rejects_false_nested_chain(self) -> None:
        with self.assertRaisesRegex(account_review.InputError, "exceeds"):
            account_review.funnel(
                {
                    "context": {
                        "funnel_name": "invalid",
                        "source": "example",
                        "window": "example",
                        "timezone": "UTC",
                        "identity_unit": "example user",
                        "deduplication_state": "asserted for test input",
                        "count_semantics": "unique_entities",
                        "stage_chain_expected_nonincreasing": True,
                        "lag_state": "not_applicable",
                        "lag_basis": "delivery-only stages",
                    },
                    "stages": [
                        {"name": "upstream", "count": 10},
                        {"name": "downstream", "count": 11},
                    ],
                }
            )

    def test_funnel_allows_nonnested_events_and_preserves_zero_denominator(self) -> None:
        result = account_review.funnel(
            {
                "context": {
                    "funnel_name": "event stream",
                    "source": "event log",
                    "window": "2026-08-01/2026-08-02",
                    "timezone": "UTC",
                    "identity_unit": "events",
                    "deduplication_state": "not deduplicated",
                    "count_semantics": "events",
                    "stage_chain_expected_nonincreasing": False,
                    "lag_state": "not_applicable",
                    "lag_basis": "delivery events",
                },
                "stages": [
                    {"name": "upstream", "count": 0},
                    {"name": "downstream", "count": 5},
                ],
            }
        )
        self.assertIsNone(result["transitions"][0]["stage_to_previous_rate"])
        self.assertIsNone(result["overall_first_to_last_rate"])
        self.assertEqual(result["transitions"][0]["count_difference"], 5)

    def test_review_uses_ratio_of_sums_and_descriptive_slope(self) -> None:
        result = account_review.review(review_payload())
        self.assertAlmostEqual(result["periods"][-1]["metric_value"], 90)
        self.assertAlmostEqual(result["current_vs_prior"]["prior_value"], 100)
        self.assertAlmostEqual(
            result["current_vs_prior"]["directional_improvement_in_metric_units"],
            10,
        )
        self.assertLess(
            result["multi_period_description"]["descriptive_slope_per_period"],
            0,
        )

    def test_review_higher_is_better_and_unequal_periods_are_explicit(self) -> None:
        payload = review_payload()
        payload["metric"]["direction"] = "higher_is_better"
        payload["periods"][2]["start"] = "2026-08-18T00:00:00+03:00"
        payload["periods"][3]["numerator"] = 1100
        result = account_review.review(payload)
        self.assertEqual(result["periods"][2]["duration_seconds"], 6 * 24 * 60 * 60)
        self.assertEqual(result["periods"][3]["duration_seconds"], 7 * 24 * 60 * 60)
        self.assertEqual(
            result["current_vs_prior"]["directional_improvement_in_metric_units"],
            10,
        )

    def test_review_zero_denominator_remains_unknown(self) -> None:
        payload = review_payload()
        payload["periods"][-1]["denominator"] = 0
        result = account_review.review(payload)
        self.assertIsNone(result["periods"][-1]["metric_value"])
        self.assertIsNone(result["current_vs_prior"]["absolute_change"])
        self.assertIsNone(result["current_vs_prior"]["relative_change"])
        self.assertIsNone(
            result["current_vs_prior"]["directional_improvement_in_metric_units"]
        )

    def test_review_entity_coverage_is_reconciled_not_assumed(self) -> None:
        payload = review_payload()
        payload["current_entities"] = [
            {"id": "a", "numerator": 500, "denominator": 6},
            {"id": "b", "numerator": 300, "denominator": 3},
        ]
        payload["prior_entities"] = [
            {"id": "a", "numerator": 500, "denominator": 5},
            {"id": "c", "numerator": 300, "denominator": 3},
        ]
        result = account_review.review(payload)
        coverage = result["entity_change_descriptors"]["coverage_reconciliation"]
        self.assertEqual(coverage["current_numerator_difference_to_period"], -100)
        self.assertEqual(coverage["current_denominator_difference_to_period"], -1)
        self.assertEqual(len(result["entity_change_descriptors"]["entities"]), 3)

    def test_review_rejects_open_comparability_or_partial_entity_rows(self) -> None:
        payload = review_payload()
        payload["scope"]["comparability_confirmed"] = False
        with self.assertRaisesRegex(account_review.InputError, "comparability_confirmed"):
            account_review.review(payload)

        payload = review_payload()
        payload["current_entities"] = []
        with self.assertRaisesRegex(account_review.InputError, "supplied together"):
            account_review.review(payload)

        payload = review_payload()
        payload["periods"][2]["start"] = "2026-08-16T00:00:00+03:00"
        with self.assertRaisesRegex(account_review.InputError, "must not overlap"):
            account_review.review(payload)


if __name__ == "__main__":
    unittest.main()
