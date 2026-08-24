from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "media_math.py"
SPEC = importlib.util.spec_from_file_location("media_math", SCRIPT)
assert SPEC and SPEC.loader
media_math = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(media_math)


class MediaMathTests(unittest.TestCase):
    def test_commerce_economics(self) -> None:
        result = media_math.commerce({
            "currency": "USD",
            "expected_net_revenue_per_unit": 100,
            "variable_costs_per_unit": {"cogs": 40, "fulfillment": 10, "fees": 10},
            "desired_post_ad_contribution_per_unit": 10,
            "risk_reserve_per_unit": 5,
            "observed_cpa": 20,
        })
        self.assertAlmostEqual(result["derived"]["pre_ad_contribution_per_unit"], 40)
        self.assertAlmostEqual(result["derived"]["break_even_roas"], 2.5)
        self.assertAlmostEqual(result["derived"]["target_cpa"], 25)
        self.assertAlmostEqual(result["derived"]["target_roas"], 4)
        self.assertAlmostEqual(result["derived"]["observed_post_ad_contribution_per_unit"], 20)

    def test_leadgen_expected_value(self) -> None:
        result = media_math.leadgen({
            "currency": "USD",
            "p_qualified_given_lead": 0.5,
            "p_sale_given_qualified": 0.2,
            "expected_contribution_per_won_sale": 1000,
            "variable_sales_cost_per_lead": 10,
            "desired_post_ad_contribution_per_lead": 10,
            "risk_reserve_per_lead": 5,
        })
        self.assertAlmostEqual(result["derived"]["expected_win_rate_per_lead"], 0.1)
        self.assertAlmostEqual(result["derived"]["break_even_cpl"], 90)
        self.assertAlmostEqual(result["derived"]["target_cpl"], 75)

    def test_leadgen_generic_stage_chain(self) -> None:
        result = media_math.leadgen({
            "stage_probabilities": [
                {"name": "valid", "probability": 0.8},
                {"name": "qualified", "probability": 0.5},
                {"name": "show", "probability": 0.5},
                {"name": "win", "probability": 0.25}
            ],
            "expected_contribution_per_won_sale": 2000,
            "variable_sales_cost_per_lead": 10
        })
        self.assertAlmostEqual(result["derived"]["expected_win_rate_per_lead"], 0.05)
        self.assertAlmostEqual(result["derived"]["break_even_cpl"], 90)

    def test_discounted_cohort_economics(self) -> None:
        result = media_math.cohort({
            "currency": "USD",
            "periods": [
                {"period": "M0", "gross_contribution_per_acquired_unit": 40},
                {"period": "M1", "gross_contribution_per_acquired_unit": 33},
                {"period": "M2", "gross_contribution_per_acquired_unit": 24.2}
            ],
            "discount_rate_per_period": 0.1,
            "desired_post_ad_contribution_per_unit": 10,
            "risk_reserve_per_unit": 5,
            "observed_cac": 65
        })
        self.assertAlmostEqual(result["derived"]["discounted_gross_margin_ltv"], 90)
        self.assertAlmostEqual(result["derived"]["target_cac"], 75)
        self.assertEqual(result["derived"]["discounted_payback_period_first_reached"], "M1")

    def test_pacing_linear_assumption(self) -> None:
        result = media_math.pacing({
            "currency": "USD",
            "total_flight_budget": 1000,
            "actual_cumulative_spend": 550,
            "flight_start": "2026-08-01T00:00:00+00:00",
            "flight_end": "2026-08-11T00:00:00+00:00",
            "as_of": "2026-08-06T00:00:00+00:00",
        })
        self.assertAlmostEqual(result["derived"]["expected_cumulative_spend"], 500)
        self.assertAlmostEqual(result["derived"]["pace_ratio"], 1.1)
        self.assertTrue(result["assumptions"])

    def test_pacing_custom_curve(self) -> None:
        result = media_math.pacing({
            "total_flight_budget": 1000,
            "actual_cumulative_spend": 400,
            "flight_start": "2026-08-01T00:00:00+03:00",
            "flight_end": "2026-08-11T00:00:00+03:00",
            "as_of": "2026-08-06T00:00:00+03:00",
            "planned_curve": [
                {"elapsed_fraction": 0, "cumulative_spend_fraction": 0},
                {"elapsed_fraction": 0.5, "cumulative_spend_fraction": 0.4},
                {"elapsed_fraction": 1, "cumulative_spend_fraction": 1}
            ]
        })
        self.assertAlmostEqual(result["derived"]["expected_cumulative_spend"], 400)
        self.assertAlmostEqual(result["derived"]["pace_ratio"], 1)
        self.assertFalse(result["assumptions"])

    def test_marginal_is_descriptive(self) -> None:
        result = media_math.marginal({
            "observed_steps": [
                {"spend": 100, "pre_ad_business_contribution": 180},
                {"spend": 200, "pre_ad_business_contribution": 250},
                {"spend": 300, "pre_ad_business_contribution": 290}
            ]
        })
        self.assertAlmostEqual(result["intervals"][0]["incremental_post_ad_contribution"], -30)
        self.assertAlmostEqual(result["intervals"][1]["marginal_contribution_return_before_ad_cost"], 0.4)
        self.assertIn("not a causal response curve", result["interpretation_limits"][0])

    def test_noise_poisson_screening_band(self) -> None:
        result = media_math.noise({
            "event_count": 100,
            "confidence_level": 0.95,
            "observed_relative_change": 0.30,
        })
        self.assertAlmostEqual(result["derived"]["relative_standard_error"], 0.1)
        self.assertAlmostEqual(result["derived"]["approximate_ratio_band_lower"], 0.822015, places=5)
        self.assertAlmostEqual(result["derived"]["approximate_ratio_band_upper"], 1.216523, places=5)
        self.assertTrue(result["derived"]["outside_approximate_poisson_band"])
        self.assertIn("screening baseline", result["interpretation_limits"][0])

    def test_power_forward_and_inverse(self) -> None:
        forward = media_math.power({
            "minimum_detectable_relative_effect": 0.20,
            "alpha": 0.05,
            "power": 0.80,
            "sidedness": 2,
        })
        count = forward["derived"]["expected_event_count_per_arm"]
        self.assertAlmostEqual(count, 472.2, delta=0.5)
        self.assertEqual(forward["derived"]["required_event_count_per_arm_rounded_up"], 473)

        inverse = media_math.power({
            "expected_event_count_per_arm": count,
            "alpha": 0.05,
            "power": 0.80,
            "sidedness": 2,
        })
        self.assertAlmostEqual(inverse["derived"]["minimum_detectable_relative_effect"], 0.20)

    def test_power_duration_and_invalid_contract(self) -> None:
        result = media_math.power({
            "minimum_detectable_relative_effect": 0.50,
            "expected_events_per_arm_per_day": 5,
        })
        self.assertGreater(result["derived"]["approximate_required_days"], 18)
        self.assertLess(result["derived"]["approximate_required_days"], 20)
        with self.assertRaises(media_math.InputError):
            media_math.power({
                "minimum_detectable_relative_effect": 0.20,
                "expected_event_count_per_arm": 500,
            })

    def test_noise_and_power_reject_invalid_inputs(self) -> None:
        with self.assertRaises(media_math.InputError):
            media_math.noise({"event_count": 0})
        with self.assertRaises(media_math.InputError):
            media_math.power({"minimum_detectable_relative_effect": 0.20, "power": 0.5})

    def test_rejects_impossible_probability(self) -> None:
        with self.assertRaises(media_math.InputError):
            media_math.leadgen({
                "p_qualified_given_lead": 1.2,
                "p_sale_given_qualified": 0.1,
                "expected_contribution_per_won_sale": 100,
            })


if __name__ == "__main__":
    unittest.main()
