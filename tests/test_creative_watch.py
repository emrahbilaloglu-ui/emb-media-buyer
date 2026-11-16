from __future__ import annotations

from copy import deepcopy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "creative_watch.py"
SPEC = importlib.util.spec_from_file_location("creative_watch", SCRIPT)
assert SPEC and SPEC.loader
watch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(watch)


def window(start, end=None):
    return {"start_date": f"2026-11-{start:02}", "end_date": f"2026-11-{end or start:02}"}


def readout(day=16):
    scope = {
        "as_of": f"2026-11-{day:02}T06:00:00-06:00",
        "account_id": "acct", "campaign_id": "test", "currency": "USD", "timezone": "America/Chicago",
        "attribution": "unified 7dc/1dv", "report_time": "impression",
    }
    row = {
        "account_id": "acct", "campaign_id": "test", "parent_id": "parent", "ad_id": "ad",
        "epoch_id": "epoch", "binding_verified": True, "epoch_started_at": "2026-11-08T00:00:00-06:00",
        "coverage_state": "observed", "current_paid_delivery": True,
        "metrics": {
            "lifecycle": {**window(8, day), "state": "observed", "source": "native-full", "spend": 176.20, "checkout": 0},
            "ad_days_lifecycle": {**window(8, day), "state": "observed", "source": "native-days"},
        },
        "ad_day_observations": [
            {"date": f"2026-11-{date:02}", "spend": spend, "impressions": impressions, "lpv": lpv,
             "atc": 0, "checkout": 0, "purchases": 0, "purchase_value": 0}
            for date, spend, impressions, lpv in [(13, 50.0, 1000, 60), (14, 54.75, 1300, 82),
                                                  (15, 20.95, 200, 27), (16, 3.8, 33, 3)]
            if date <= day
        ],
    }
    return row, scope


def contract(day=16, *, basis=None):
    return {
        "question": "Will the next complete own delivery period show any checkout?",
        "due_at": f"2026-11-{day+1:02}T06:00:00-06:00",
        "condition": {"kind": "metric", "window": window(day), "metric": "checkout", "op": "eq",
                      "value": 0, "source": "predeclared decision protocol"},
        "wait_cost": {"kind": "estimated_range", "currency": "USD", "lower": 1, "upper": 7.5,
                      "source": "scope-specific own delivery estimate before next read"},
        "basis": basis or {"kind": "low_opportunity", "window": window(day-1), "metric": "impressions",
                           "value": 250, "source": "owner's synthetic test design for this window"},
    }


def past(row, scope, previous=15, *, old=None, disposition="watch"):
    prior_row, _ = readout(previous)
    return {
        "prior_row": prior_row,
        "prior_disposition": disposition,
        "prior": {
            **{field: row[field] for field in watch.BINDING},
            "as_of": f"2026-11-{previous:02}T05:59:00-06:00", "status": "deferred",
            "watch": old,
            "observation": {"meta": {field: scope[field] for field in watch.CONTEXT}},
        },
    }


def event(row, *, event_type="technical_change", event_id="event", observed_at="2026-11-16T05:30:00-06:00"):
    return {
        **{field: row[field] for field in watch.BINDING}, "id": event_id, "event_type": event_type,
        "source": "independent scoped QA", "observed_at": observed_at, "occurred_at": observed_at,
        "verified": True, "state": "measurement valid",
    }


class CreativeWatchTests(unittest.TestCase):
    def test_first_low_opportunity_at_bounded_spend_is_allowed_without_universal_cut_threshold(self):
        row, scope = readout()
        result = watch.assess_watch(contract(), row, scope)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["verified_fact"]["observed"], 200)
        self.assertEqual(result["trigger_state"], "pending")
        record = contract()
        record["basis"]["window"] = window(13, 15)
        self.assertFalse(watch.assess_watch(record, row, scope)["ok"])
        record = contract()
        record["basis"].pop("source")
        self.assertFalse(watch.assess_watch(record, row, scope)["ok"])

    def test_mechanical_frozen_trigger_rejects_paraphrase_or_generic_reassessment(self):
        row, scope = readout()
        old = contract(15)
        prior = past(row, scope, old=old)
        proposal = contract()
        proposal["question"] += " Current review applies the same control."
        proposal["trigger"] = {"state": "pending", "reassessment": "Continue, then check again."}
        result = watch.assess_watch(proposal, row, scope, prior)
        self.assertEqual(result["prior_trigger_state"], "met")
        self.assertTrue(result["expired"])
        self.assertEqual(result["prior_observation"]["observed"], 0)
        self.assertFalse(result["ok"])

    def test_unobserved_funnel_field_is_unknown_even_when_positive_spend_exists(self):
        row, scope = readout()
        row["ad_day_observations"][2].pop("checkout")
        result = watch.assess_watch(contract(), row, scope, past(row, scope, old=contract(15)))
        self.assertEqual(result["prior_trigger_state"], "unknown")
        self.assertTrue(result["expired"])
        self.assertFalse(result["ok"])

    def test_first_real_checkout_after_previous_cut_is_a_limited_counterexample(self):
        row, scope = readout()
        row["ad_day_observations"][2]["checkout"] = 1
        row["metrics"]["lifecycle"]["checkout"] = 1
        proposal = contract(basis={"kind": "first_checkout", "window": window(15)})
        result = watch.assess_watch(proposal, row, scope, past(row, scope, disposition="reduce"))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["verified_fact"]["kind"], "first_checkout")
        self.assertFalse(watch.assess_watch(proposal, row, scope, past(row, scope, old=contract(15)))["ok"])
        row["metrics"]["lifecycle"]["checkout"] = 2
        self.assertFalse(watch.assess_watch(proposal, row, scope)["ok"])

    def test_first_clean_day_after_bound_mixed_day_is_valid_only_until_observation(self):
        row, scope = readout()
        row["epoch_started_at"] = "2026-11-15T09:00:00-06:00"
        proposal = contract(basis={"kind": "first_clean_window", "window": window(16)})
        self.assertTrue(watch.assess_watch(proposal, row, scope)["ok"])
        later, later_scope = readout(17)
        later["epoch_started_at"] = row["epoch_started_at"]
        moved = contract(17, basis={"kind": "first_clean_window", "window": window(17)})
        outcome = watch.assess_watch(moved, later, later_scope, past(later, later_scope, previous=16, old=proposal))
        self.assertFalse(outcome["ok"])
        self.assertTrue(outcome["expired"])

    def test_technical_event_needs_source_verified_exact_identity_and_new_observation(self):
        row, scope = readout()
        proposal = contract(basis={"kind": "technical_change", "event_id": "event"})
        old = contract(15)
        old["condition"] = {"kind": "technical_event", "event_type": "technical_change",
                            "expected_state": "measurement valid", "source": "independent scoped QA"}
        prior = past(row, scope, old=old)
        self.assertFalse(watch.assess_watch(proposal, row, scope, prior)["ok"])
        new = event(row)
        outcome = watch.assess_watch(proposal, row, scope, prior, events=[new])
        self.assertTrue(outcome["ok"], outcome)
        self.assertEqual(outcome["prior_trigger_state"], "met")
        for modified in ({**new, "ad_id": "another"}, {**new, "verified": False},
                         {**new, "observed_at": "2026-11-16T07:00:00-06:00"},
                         {**new, "occurred_at": "2026-11-14T06:00:00-06:00"}):
            with self.subTest(modified=modified):
                self.assertFalse(watch.assess_watch(proposal, row, scope, prior, events=[modified])["ok"])

    def test_real_click_credit_remains_counterevidence_but_old_revision_does_not_renew(self):
        row, scope = readout()
        row["ad_day_observations"][2].update(purchases=1, purchase_value=1850.0)
        credit = event(row, event_type="click_credit")
        credit.update(credit_type="click", report_date="2026-11-15", value=1850, currency="USD", attribution_window="7d click")
        proposal = contract(basis={"kind": "material_credit", "event_id": "event"})
        result = watch.assess_watch(proposal, row, scope, events=[credit])
        self.assertTrue(result["ok"], result)
        self.assertFalse(watch.assess_watch(proposal, row, scope, past(row, scope, old=contract(15)), events=[credit])["ok"])
        self.assertFalse(watch.assess_watch(proposal, row, scope, events=[{**credit, "credit_type": "view"}])["ok"])
        self.assertFalse(watch.assess_watch(proposal, row, scope, events=[{**credit, "value": 2000}])["ok"])

    def test_unstructured_legacy_requires_explicit_retirement_and_new_bound_fact(self):
        row, scope = readout()
        prior = past(row, scope, old=None)
        prior["prior"]["watch"] = "platform stage might improve next day"
        proposal = contract(basis={"kind": "technical_change", "event_id": "event"})
        new = event(row)
        result = watch.assess_watch(proposal, row, scope, prior, events=[new])
        self.assertFalse(result["ok"])
        self.assertEqual(result["prior_trigger_state"], "unknown")
        proposal["legacy_resolution"] = {
            "prior_as_of": prior["prior"]["as_of"], "outcome": "retired_unstructured",
            "rationale": "No prospective predicate was frozen; earlier stage hypothesis is unresolved.",
        }
        outcome = watch.assess_watch(proposal, row, scope, prior, events=[new])
        self.assertTrue(outcome["ok"], outcome)
        self.assertEqual(outcome["prior_trigger_state"], "unknown")
        self.assertFalse(watch.assess_watch(proposal, row, scope, prior)["ok"])

    def test_exact_verified_retention_is_not_a_purchase_growth_or_renewal_heuristic(self):
        row, scope = readout()
        proposal = contract(basis={"kind": "approved_retention"})
        prior = past(row, scope, old=contract(15))
        self.assertFalse(watch.assess_watch(proposal, row, scope, prior)["ok"])
        prior["main_retained"] = True
        self.assertTrue(watch.assess_watch(proposal, row, scope, prior)["ok"])

    def test_in_flight_reread_preserves_same_deadline_but_moved_deadline_needs_fresh_fact(self):
        row, scope = readout()
        scope["as_of"] = "2026-11-16T05:45:00-06:00"
        record = contract(15)
        record["condition"].update(op="gte", value=2)
        prior = past(row, scope, old=deepcopy(record))
        result = watch.assess_watch(record, row, scope, prior)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["prior_trigger_state"], "pending")
        record["due_at"] = "2026-11-17T06:00:00-06:00"
        self.assertFalse(watch.assess_watch(record, row, scope, prior)["ok"])

    def test_wait_cost_spend_bound_can_trigger_on_partial_day_but_is_not_a_pause_authorization(self):
        row, scope = readout()
        old = contract(15)
        old["due_at"] = "2026-11-17T06:00:00-06:00"
        old["condition"].update(window=window(16), op="gte", value=2)
        old["wait_cost"] = {
            "kind": "observable_bound", "source": "owner-specific exposure review",
            "condition": {"kind": "metric", "window": window(16), "metric": "spend", "op": "gte",
                          "value": 3, "source": "frozen prospective test bound"},
        }
        result = watch.assess_watch(deepcopy(old), row, scope, past(row, scope, old=old))
        self.assertEqual(result["prior_wait_bound_state"], "met")
        self.assertEqual(result["prior_trigger_state"], "met")
        self.assertEqual(result["prior_wait_bound_observation"]["observed"], 3.8)
        self.assertFalse(result["ok"])
        first = contract()
        first["wait_cost"] = deepcopy(old["wait_cost"])
        result = watch.assess_watch(first, row, scope)
        self.assertFalse(result["ok"])
        self.assertEqual(result["wait_bound_state"], "met")

    def test_mixed_epoch_boundary_cannot_be_measured_as_clean_prospective_outcome(self):
        row, scope = readout()
        row["epoch_started_at"] = "2026-11-16T01:00:00-06:00"
        candidate = contract()
        self.assertFalse(watch.assess_watch(candidate, row, scope)["ok"])
        candidate["condition"]["window"] = window(17)
        candidate["due_at"] = "2026-11-18T06:00:00-06:00"
        self.assertTrue(watch.assess_watch(candidate, row, scope)["ok"])

    def test_cross_scope_or_epoch_drift_cannot_resolve_frozen_condition(self):
        row, scope = readout()
        prior = past(row, scope, old=contract(15))
        for mutation in (
            {"epoch_id": "epoch_other"},
            {"observation": {"meta": {**prior["prior"]["observation"]["meta"], "report_time": "conversion"}}},
        ):
            with self.subTest(mutation=mutation):
                bad = deepcopy(prior)
                bad["prior"].update(mutation)
                result = watch.assess_watch(contract(), row, scope, bad)
                self.assertFalse(result["ok"])
                self.assertEqual(result["prior_trigger_state"], "unknown")

    def test_verified_rebind_can_support_new_clean_watch_without_reusing_prior_trigger(self):
        row, scope = readout()
        row["epoch_started_at"] = "2026-11-15T14:00:00-06:00"
        prior = past(row, scope, old=contract(15))
        prior["prior"]["epoch_id"] = "earlier_epoch"
        current = contract(basis={"kind": "first_clean_window", "window": window(16)})
        self.assertFalse(watch.assess_watch(current, row, scope, prior)["ok"])
        prior["verified_rebind"] = True
        result = watch.assess_watch(current, row, scope, prior)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["prior_trigger_state"], "unknown")
        prior["prior"]["ad_id"] = "unrelated_ad"
        self.assertFalse(watch.assess_watch(current, row, scope, prior)["ok"])


if __name__ == "__main__":
    unittest.main()
