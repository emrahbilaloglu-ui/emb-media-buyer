from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "paid_decisions.py"
SPEC = importlib.util.spec_from_file_location("paid_decisions", SCRIPT)
assert SPEC and SPEC.loader
paid_decisions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paid_decisions)

AS_OF = "2026-11-07T16:00:00-06:00"
PRIOR = "2026-11-05T16:00:00-06:00"
BOUNDARY = "2026-11-06T13:14:00-06:00"
REVIEW = {
    "at": "2026-11-08T16:00:00-06:00",
    "condition": "Reassess if the next closed account day has new cost without checkout progress.",
    "source": "existing daily native and merchant read",
}


def binding(ad_id, parent_id="p1", epoch_id="e1"):
    return {"account_id": "account", "campaign_id": "test", "parent_id": parent_id, "ad_id": ad_id, "epoch_id": epoch_id}


def ad(ad_id, parent_id="p1", epoch_id="e1", status="ACTIVE", effective=None):
    return {
        **binding(ad_id, parent_id, epoch_id),
        "epoch_started_at": BOUNDARY if epoch_id == "e2" else "2026-10-29T00:00:00-05:00",
        "lifecycle_start": "2026-10-29", "binding_verified": True,
        "configured_status": status, "effective_status": effective or status,
    }


def payload(*ads):
    scope = {
        "platform": "meta", "account_id": "account", "campaign_id": "test", "as_of": AS_OF,
        "timezone": "America/Chicago", "currency": "USD", "attribution": "7dc_1dv", "report_time": "impression",
    }
    return {
        "scope": scope,
        "current_meta_source": "lifecycle-meta-read",
        "inventory": {
            "manifest": {**scope, "independent": True, "source_id": "native", "retrieved_at": AS_OF,
                         "complete": True, "pagination_complete": True},
            "ads": list(ads),
            "parents": [
                {"account_id": "account", "campaign_id": "test", "parent_id": parent_id, "daily_budget": 135,
                 "configured_status": "ACTIVE", "effective_status": "ACTIVE", "currency": "USD"}
                for parent_id in sorted({item["parent_id"] for item in ads})
            ],
        },
        "current_rows": [{
            **item, "metrics": {"lifecycle": {"start_date": "2026-10-29", "end_date": "2026-11-07",
                                               "spend": 216.73, "purchases": 1, "purchase_value": 200},
                                "current_epoch": {"start_date": "2026-11-07", "end_date": "2026-11-07", "spend": 22}},
        } for item in ads],
        "prior_decisions": [], "current_decisions": [], "proposals": [], "applications": [],
    }


def decision(bound, state="open", as_of=PRIOR, **extras):
    return {**bound, "status": state, "as_of": as_of, "reason": "Retain the earlier decision for the next read.",
            "next_review": REVIEW, **extras}


def proposal(bound, reason="awaiting_approval"):
    return {**bound, "action": "pause", "proposed_at": PRIOR, "remaining_reason": reason,
            "reason": "Exposure without repeat purchase or checkout progress.",
            "counterevidence": "One attributed purchase may have additional lag.", "next_review": REVIEW}


def application(bound):
    return {
        **bound, "action": "pause", "status": "applied_verified", "applied_at": "2026-11-07T15:00:00-06:00",
        "source": "mutation-receipt",
        "readback": {**bound, "configured_status": "PAUSED", "effective_status": "PAUSED",
                     "read_at": "2026-11-07T15:30:00-06:00", "source": "fresh-native-status", "independent": True},
        "before": {**bound, "configured_status": "ACTIVE", "effective_status": "ACTIVE",
                   "read_at": "2026-11-07T14:30:00-06:00", "source": "before-native-status"},
    }


class PaidDecisionTests(unittest.TestCase):
    def test_missing_native_page_cannot_prove_empty_parent(self):
        data = payload(ad("one"), ad("two"))
        data["inventory"]["manifest"]["pagination_complete"] = False
        data["proposals"] = [proposal(binding("one")), proposal(binding("two"))]
        result = paid_decisions.handoff(data)
        self.assertFalse(result["complete_for_decision"])
        self.assertEqual(result["parent_effects"][0]["if_entire_proposed_batch_applied"]["topology"], "uncertain_inventory")

    def test_open_decision_cannot_reuse_a_due_or_expired_review(self):
        data = payload(ad("one"))
        data["current_decisions"] = [decision(binding("one"), as_of=AS_OF, next_review={**REVIEW, "at": AS_OF})]
        with self.assertRaisesRegex(paid_decisions.InputError, "must follow its as_of"):
            paid_decisions.handoff(data)

    def test_prior_open_missing_current_is_unresolved_even_if_other_ad_applied(self):
        data = payload(ad("missing"), ad("applied", status="PAUSED"))
        data["prior_decisions"] = [decision(binding("missing"))]
        data["proposals"] = [proposal(binding("applied"))]
        data["applications"] = [application(binding("applied"))]
        result = paid_decisions.handoff(data)
        self.assertFalse(result["complete_for_decision"])
        states = {row["binding"]["ad_id"]: row["status"] for row in result["decisions"]}
        self.assertEqual(states, {"applied": "applied_verified", "missing": "unresolved"})
        self.assertEqual(result["decisions"][1]["open_age_seconds"], 172800)
        self.assertEqual(result["issues"][0]["reason"], "prior_open_decision_missing_current")

    def test_duplicate_account_ad_epoch_as_of_ignores_timestamp_offset_and_other_ids(self):
        data = payload(ad("a"))
        data["prior_decisions"] = [decision(binding("a")), decision(binding("a", "other"), as_of="2026-11-05T22:00:00Z")]
        with self.assertRaisesRegex(paid_decisions.InputError, "duplicate account/ad/epoch/as-of"):
            paid_decisions.handoff(data)

    def test_trigger_and_new_evidence_closure_retain_separate_ledger_deltas(self):
        data = payload(ad("trigger"), ad("closed"))
        meta = {**{k: data["scope"][k] for k in ("attribution", "report_time", "currency", "timezone")},
                "source": "prior-meta", "as_of": PRIOR, "start_date": "2026-10-29",
                "spend": 59.15, "purchases": 1, "purchase_value": 200}
        merchant = {"source": "prior-shop", "as_of": PRIOR, "start_date": "2026-10-29", "currency": "USD",
                    "timezone": "America/Chicago", "definition": "paid order", "binding_basis": "literal association",
                    "orders": 1, "value": 155}
        data["prior_decisions"] = [decision(binding(name), observation={"meta": meta, "merchant": merchant})
                                   for name in ("trigger", "closed")]
        data["current_decisions"] = [
            decision(binding("trigger"), "trigger_met", AS_OF,
                     trigger={"condition": "No repeat purchase in the next closed read", "source": "native window",
                              "detail": "Added cost without a new credited purchase", "observed_at": AS_OF}),
            decision(binding("closed"), "closed_new_evidence", AS_OF,
                     closure_evidence={"source": "paid sweep and merchant snapshots", "detail": "Repeat credited outcomes",
                                       "observed_at": AS_OF},
                     observation={"merchant": {**merchant, "as_of": AS_OF, "source": "current-shop", "orders": 2, "value": 400}}),
        ]
        data["current_rows"][1]["metrics"]["lifecycle"].update(purchases=3, purchase_value=640)
        result = paid_decisions.handoff(data)
        self.assertTrue(result["complete_for_decision"])
        closed, trigger = result["decisions"]
        self.assertEqual(closed["status"], "closed_new_evidence")
        self.assertEqual(closed["observation"]["meta_change"]["deltas"]["purchases"], 2)
        self.assertEqual(closed["observation"]["merchant_change"]["deltas"], {"orders": 1, "value": 245})
        self.assertEqual(trigger["status"], "trigger_met")
        self.assertEqual(trigger["observation"]["meta_change"]["deltas"]["spend"], 157.58)
        self.assertEqual(trigger["observation"]["meta_change"]["deltas"]["purchases"], 0)
        self.assertEqual(trigger["observation"]["merchant_change"]["state"], "unknown")
        data["current_decisions"][1]["closure_evidence"]["observed_at"] = PRIOR
        self.assertFalse(paid_decisions.handoff(data)["complete_for_decision"])

    def test_dated_changes_separate_revisions_partial_roll_forward_and_later_dates(self):
        data = payload(ad("a"))

        def day(date, spend, purchases, value):
            return {"date": date, "spend": spend, "purchases": purchases, "purchase_value": value}

        prior_days = [day("2026-11-03", 4, 0, 0), day("2026-11-04", 15, 0, 0), day("2026-11-05", 8, 0, 0)]
        meta = {**{k: data["scope"][k] for k in ("attribution", "report_time", "currency", "timezone")},
                "source": "prior-meta", "as_of": PRIOR, "start_date": "2026-10-29", "spend": 27,
                "purchases": 0, "purchase_value": 0, "ad_day_observations": prior_days}
        data["prior_decisions"] = [decision(binding("a"), observation={"meta": meta})]
        data["current_decisions"] = [decision(binding("a"), "deferred", AS_OF)]
        data["current_rows"][0]["ad_day_observations"] = [
            day("2026-11-02", 3, 0, 0), day("2026-11-04", 15, 1, 35), day("2026-11-05", 14, 1, 60),
            day("2026-11-06", 12, 0, 0), day("2026-11-07", 7, 1, None),
        ]
        original = copy.deepcopy(data)
        observations = paid_decisions.handoff(data)["decisions"][0]["observation"]
        changes = observations["meta_change"]["dated_report_changes"]
        self.assertEqual(changes["prior_closed_date_revisions"], [
            {"date": "2026-11-04", "deltas": {"spend": 0, "purchases": 1, "purchase_value": 35}, "state": "observed"},
        ])
        self.assertEqual(changes["prior_partial_date_roll_forward"]["deltas"]["spend"], 6)
        self.assertEqual(changes["later_report_dates"][1], {"date": "2026-11-07", "observation": {
            "spend": 7, "purchases": 1, "purchase_value": None,
        }, "partial_as_of": True})
        self.assertEqual(changes["missing_counterpart_dates"], [
            {"date": "2026-11-02", "missing_from": "prior"}, {"date": "2026-11-03", "missing_from": "current"},
        ])
        self.assertEqual(data, original)

    def test_only_independent_exact_fresh_settled_readback_removes_proposal(self):
        data = payload(ad("a", status="PAUSED"))
        data["proposals"] = [proposal(binding("a"), "in_process")]
        data["applications"] = [application(binding("a"))]
        data["current_decisions"] = [decision(binding("a"), "applied_verified", AS_OF)]
        settled = paid_decisions.handoff(data)
        self.assertEqual(settled["remaining_proposals"], [])
        self.assertEqual(settled["applications"][0]["authorization_evidence"]["recorded_status"], "unknown")
        for changes, expected_reason in (
            ({"effective_status": "IN_PROCESS"}, "readback_status_mismatch"),
            ({"effective_status": "ACTIVE"}, "readback_status_mismatch"),
            ({"epoch_id": "older"}, "readback_binding_mismatch"),
            ({"parent_id": "other"}, "readback_binding_mismatch"),
            ({"read_at": "2026-11-07T14:59:59-06:00"}, "readback_not_fresh_as_of"),
            ({"read_at": "2026-11-07T16:01:00-06:00"}, "readback_not_fresh_as_of"),
            ({"source": "mutation-receipt"}, "readback_not_independent"),
            ({"source": ""}, "readback_evidence_missing"),
        ):
            with self.subTest(changes=changes):
                invalid = copy.deepcopy(data)
                invalid["applications"][0]["readback"].update(changes)
                result = paid_decisions.handoff(invalid)
                self.assertFalse(result["complete_for_decision"])
                self.assertEqual(result["applications"][0]["reason"], expected_reason)
                self.assertEqual(result["remaining_proposals"][0]["remaining_reason"], "in_process")
                self.assertEqual(result["remaining_proposals"][0]["next_review"], REVIEW)
        data["applications"][0]["status"] = "accepted"
        data["current_decisions"][0]["status"] = "pending"
        result = paid_decisions.handoff(data)
        self.assertTrue(result["complete_for_decision"])
        self.assertFalse(result["applications"][0]["verified"])
        data["applications"][0]["authorization"] = {
            **binding("a"), "action": "pause", "status": "approved", "at": PRIOR, "source": "owner decision",
        }
        result = paid_decisions.handoff(data)
        self.assertFalse(result["applications"][0]["verified"])
        self.assertEqual(result["applications"][0]["authorization_evidence"]["recorded_status"], "approved")

    def test_batch_projection_includes_last_two_and_single_sibling(self):
        data = payload(ad("a", status="PAUSED"), ad("b"), ad("c", "p2"), ad("d", "p2"),
                       ad("e", "p3"), ad("f", "p3", effective="IN_PROCESS"))
        data["proposals"] = [proposal(binding("a")), proposal(binding("b")), proposal(binding("c", "p2")),
                             proposal(binding("e", "p3"))]
        data["applications"] = [application(binding("a"))]
        result = paid_decisions.handoff(data)
        first, second, uncertain = result["parent_effects"]
        self.assertEqual(first["before_projection"]["eligible_child_ids"], ["a", "b"])
        self.assertEqual(first["with_verified_applications"]["eligible_child_ids"], ["b"])
        self.assertEqual(first["if_entire_proposed_batch_applied"]["topology"], "empty")
        self.assertEqual(first["configured_status"], "ACTIVE")
        self.assertEqual(first["nominal_daily_budget"], 135)
        self.assertEqual(second["if_entire_proposed_batch_applied"]["sole_remaining_ad_id"], "d")
        self.assertEqual(second["if_entire_proposed_batch_applied"]["concentration"], "possible_on_sole_child")
        self.assertEqual(uncertain["if_entire_proposed_batch_applied"]["topology"], "uncertain")
        self.assertEqual(uncertain["if_entire_proposed_batch_applied"]["unknown_child_ids"], ["f"])
        self.assertEqual([item["proposal"]["ad_id"] for item in result["remaining_proposals"]], ["b", "c", "e"])

    def test_remaining_proposal_requires_typed_reason_and_review(self):
        data = payload(ad("a"))
        data["proposals"] = [proposal(binding("a"), "Something to look at")]
        data["proposals"][0].pop("next_review")
        result = paid_decisions.handoff(data)
        self.assertFalse(result["complete_for_decision"])
        self.assertEqual({item["reason"] for item in result["issues"]}, {
            "proposal_next_review_missing_or_untyped", "remaining_proposal_reason_missing_or_untyped",
        })

    def test_explicit_first_proposal_produces_a_carryable_open_snapshot(self):
        data = payload(ad("a"))
        data["proposals"] = [proposal(binding("a"))]
        result = paid_decisions.handoff(data)
        prior = result["decisions"][0]["current"]
        self.assertEqual(prior["status"], "open")
        self.assertEqual(prior["observation"]["meta"]["spend"], 216.73)
        later = "2026-11-08T16:00:00-06:00"
        data["scope"]["as_of"] = later
        data["inventory"]["manifest"].update(as_of=later, retrieved_at=later)
        data["prior_decisions"] = [prior]
        data["proposals"] = []
        next_result = paid_decisions.handoff(data)
        self.assertFalse(next_result["complete_for_decision"])
        self.assertEqual(next_result["decisions"][0]["status"], "unresolved")
        self.assertEqual(next_result["decisions"][0]["open_age_seconds"], 259200)

    def test_mixed_treatment_rebind_carries_and_preserves_whole_ad_metrics(self):
        target = binding("a", epoch_id="e2")
        old = binding("a")
        data = payload(ad("a", epoch_id="e2"))
        data["prior_decisions"] = [decision(old)]
        data["current_decisions"] = [decision(target, "rebind", AS_OF)]
        data["epoch_events"] = [{**target, "from_epoch_id": "e1", "kind": "treatment", "effective_at": BOUNDARY,
                                 "source": "creative change history"}]
        data["rebinds"] = [{**old, "to_epoch_id": "e2", "at": AS_OF, "disposition": "carry",
                            "source": "current decision table", "reason": "Preserve earlier exposure as counterevidence."}]
        result = paid_decisions.handoff(data)
        self.assertTrue(result["complete_for_decision"])
        epoch = result["epoch_context"][0]
        self.assertEqual(epoch["whole_ad_lifecycle"]["spend"], 216.73)
        self.assertEqual(epoch["current_binding_window"]["spend"], 22)
        self.assertEqual(epoch["mixed_treatment_date"], "2026-11-06")
        self.assertIsNone(epoch["first_delivery_at"])
        self.assertFalse(epoch["treatment_history_preserved"])
        self.assertEqual(result["decisions"][1]["prior"]["epoch_id"], "e1")
        self.assertEqual(result["decisions"][1]["open_age_seconds"], 172800)
        repeated = copy.deepcopy(data)
        later = "2026-11-08T16:00:00-06:00"
        repeated["scope"]["as_of"] = later
        repeated["inventory"]["manifest"].update(as_of=later, retrieved_at=later)
        repeated["prior_decisions"].append(result["decisions"][1]["current"])
        repeated["current_decisions"] = [decision(target, "deferred", later, next_review={**REVIEW, "at": "2026-11-09T16:00:00-06:00"})]
        next_result = paid_decisions.handoff(repeated)
        self.assertTrue(next_result["complete_for_decision"])
        self.assertEqual(next_result["decisions"][1]["prior"]["epoch_id"], "e2")
        self.assertEqual(next_result["decisions"][1]["open_age_seconds"], 259200)
        data.pop("rebinds")
        self.assertFalse(paid_decisions.handoff(data)["complete_for_decision"])

    def test_measurement_transition_can_close_without_erasing_economics(self):
        target = binding("a", epoch_id="e2")
        data = payload(ad("a", epoch_id="e2"))
        data["prior_decisions"] = [decision(binding("a"))]
        data["epoch_events"] = [{**target, "from_epoch_id": "e1", "kind": "measurement", "effective_at": BOUNDARY,
                                 "source": "tag history"}]
        data["rebinds"] = [{**binding("a"), "to_epoch_id": "e2", "at": AS_OF, "disposition": "close",
                            "source": "current decision table", "reason": "Old decision retired by explicit measurement review."}]
        result = paid_decisions.handoff(data)
        self.assertTrue(result["complete_for_decision"])
        self.assertTrue(result["epoch_context"][0]["treatment_history_preserved"])
        self.assertEqual(result["epoch_context"][0]["whole_ad_lifecycle"]["spend"], 216.73)
        self.assertIsNone(result["epoch_context"][0]["mixed_treatment_date"])
        self.assertEqual(result["decisions"][0]["rebind"]["disposition"], "close")

    def test_only_exact_promoted_source_retained_and_same_media_is_counterevidence(self):
        data = payload({**ad("a"), "media_hash": "sha256:example"}, ad("b"))
        data["proposals"] = [proposal(binding("a")), proposal(binding("b"))]
        data["main_retention"] = [
            {**binding("a"), "kind": "promoted_source", "binding_verified": True,
             "main_ad_id": "main-ad", "main_campaign_id": "main-campaign", "source": "exact lineage", "policy_source": "owner policy"},
            {**binding("b"), "kind": "candidate", "binding_verified": True},
        ]
        data["media_history"] = [{**binding("a"), "media_hash": "sha256:example", "source": "media history",
                                  "observed_at": PRIOR, "detail": "Older delivery on a distinct ad.",
                                  "prior_media_binding": {**binding("old"), "media_hash": "sha256:example", "binding_verified": True}}]
        result = paid_decisions.handoff(data)
        self.assertTrue(result["remaining_proposals"][0]["main_retention_conflict"])
        self.assertFalse(result["remaining_proposals"][1]["main_retention_conflict"])
        self.assertIsNone(result["decisions"][0]["prior"])
        self.assertEqual(result["epoch_context"][0]["same_media_counterevidence"][0]["prior_binding"]["ad_id"], "old")

    def test_passive_unknown_epoch_is_retained_and_unbound_extra_is_surfaced(self):
        old = {**ad("old", status="PAUSED"), "epoch_id": None, "binding_verified": False, "epoch_started_at": None}
        data = payload(old, ad("active"))
        result = paid_decisions.handoff(data)
        self.assertTrue(result["complete_for_decision"])
        old_epoch = next(item for item in result["epoch_context"] if item["binding"]["ad_id"] == "old")
        self.assertIsNone(old_epoch["binding"]["epoch_id"])
        self.assertIsNone(old_epoch["current_binding_window"])
        self.assertEqual(old_epoch["whole_ad_lifecycle"]["spend"], 216.73)
        data["current_rows"].append({"ad_id": "unbound-extra", "disposition": "unresolved"})
        result = paid_decisions.handoff(data)
        self.assertFalse(result["complete_for_decision"])
        self.assertEqual(result["issues"][0]["binding"]["ad_id"], "unbound-extra")
        self.assertEqual(result["issues"][0]["reason"], "sweep_row_identity_unresolved")

    def test_unverified_active_epoch_cannot_settle_its_application(self):
        data = payload({**ad("bad", status="PAUSED"), "binding_verified": False}, ad("active"))
        data["proposals"] = [proposal(binding("bad"))]
        data["applications"] = [application(binding("bad"))]
        result = paid_decisions.handoff(data)
        self.assertFalse(result["complete_for_decision"])
        self.assertEqual(result["applications"][0]["reason"], "native_binding_unverified")
        self.assertEqual(len(result["remaining_proposals"]), 1)

    def test_verified_binding_without_start_supports_whole_ad_decision(self):
        data = payload({**ad("a", status="PAUSED"), "epoch_started_at": None})
        data["proposals"] = [proposal(binding("a"))]
        data["applications"] = [application(binding("a"))]
        result = paid_decisions.handoff(data)
        self.assertTrue(result["complete_for_decision"])
        self.assertTrue(result["applications"][0]["verified"])
        self.assertIsNone(result["epoch_context"][0]["current_binding_window"])
        self.assertEqual(result["epoch_context"][0]["whole_ad_lifecycle"]["spend"], 216.73)
        data["inventory"]["ads"][0]["epoch_started_at"] = "2026-11-08T16:00:00-06:00"
        self.assertFalse(paid_decisions.handoff(data)["applications"][0]["verified"])


if __name__ == "__main__":
    unittest.main()
