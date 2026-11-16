from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from creative_review_plan import BINDING, PERFORMANCE_FIELDS, build_plan
from paid_sweep import sweep
from validate_decision_packet import validate
from test_validate_decision_packet import directional_packet


def casebook():
    return json.loads((ROOT / "tests" / "fixtures" / "creative_review_casebook.json").read_text())


def synthetic_sweep(book, *, first=False):
    as_of = "2026-11-14T14:00:00Z" if first else book["as_of"]
    days, columns = book["days"][:3] if first else book["days"], book["daily_columns"]
    scope = {"platform":"synthetic", "account_id":"test-account", "campaign_id":"test-campaign", "currency":"USD",
             "timezone":"America/Chicago", "as_of":as_of, "attribution":"7d click / 1d view", "report_time":"impression", "lifecycle_start":days[0]}
    cases = [item for item in book["cases"] if not first or item["id"] in {"old-credit-awaiting", "unproductive-incumbent"}]
    mapping = {"count_action_type":"canonical", "value_action_type":"canonical-value", "evidence":"synthetic action mapping",
               "value_currency":"USD", "missing_count_is_zero":True, "missing_value_for_zero_count_is_zero":True}

    def manifest(source, **extra):
        return {**scope, "source_id":source, "retrieved_at":as_of, "complete":True, "pagination_complete":True,
                "query_scope_evidence":"independent synthetic full scoped read", "start_date":days[0], "end_date":days[-1], **extra}

    parents = [{"account_id":scope["account_id"], "campaign_id":scope["campaign_id"], "parent_id": parent,
                "configured_status":"ACTIVE", "effective_status":"ACTIVE", "daily_budget":100, "currency":"USD"}
               for parent in sorted({case["parent"] for case in cases})]
    ads, full, daily = [], [], []
    controls = dict.fromkeys(columns, 0)

    def to_row(fields, totals, **extra):
        return {**fields, **dict((key, totals[key]) for key in columns[:5]), **extra,
                "actions":{"canonical":totals["purchases"]} if totals["purchases"] else {},
                "action_values":{"canonical-value":totals["purchase_value"]} if totals["purchase_value"] else {}}

    for case in cases:
        fields = {"account_id":scope["account_id"], "campaign_id":scope["campaign_id"], "parent_id":case["parent"], "ad_id":case["id"]}
        status = case.get("status", "ACTIVE")
        lifecycle = case.get("lifecycle_start", days[0])
        ads.append({**fields, "epoch_id":f"epoch-{case['id']}", "binding_verified":True, "lifecycle_start":lifecycle,
                    "epoch_started_at":case.get("epoch_started_at", f"{lifecycle}T08:00:00Z"), "configured_status":status, "effective_status":status})
        totals = dict.fromkeys(columns, 0)
        for day, values in zip((day for day in days if day >= lifecycle), case["daily"]):
            parts = dict(zip(columns, values))
            daily.append(to_row(fields, parts, date=day))
            for key, value in parts.items():
                totals[key] += value
                controls[key] += value
        full.append(to_row(fields, totals))
    suffix = "prior" if first else "current"
    return sweep({"scope":scope, "inventory":{"manifest":manifest(f"inventory-{suffix}", independent=True), "parents":parents, "ads":ads},
                  "lifecycle":{"manifest":manifest(f"lifecycle-{suffix}", grain="ad", mapping=mapping), "rows":full},
                  "ad_days":{"manifest":manifest(f"days-{suffix}", grain="ad_day", mapping=mapping), "rows":daily},
                  "controls":{"manifest":manifest(f"campaign-{suffix}", grain="campaign_and_parent", independent=True), "totals":controls}})


def sample_payload(*, resolve_disagreement=False):
    book = casebook()
    snapshot = synthetic_sweep(book)
    prior = synthetic_sweep(book, first=True)
    as_of = snapshot["scope"]["as_of"]
    next_read = "2026-11-17T21:00:00Z"
    prior_as_of = prior["scope"]["as_of"]
    epoch_by_id = {row["ad_id"]:row for row in snapshot["entities"]}

    def binding(ad_id):
        return {key:epoch_by_id[ad_id][key] for key in BINDING}

    first_proposal = {**binding("old-credit-awaiting"), "action":"pause", "proposed_at":prior_as_of, "proposal_source":"synthetic original review",
                      "snapshot_source":"lifecycle-prior"}
    snapshot["decision_handoff"] = {"complete_for_decision":True, "decisions":[{"binding":binding("proven-main"), "main_retained":True}],
                                    "remaining_proposals":[{"proposal":first_proposal, "remaining_reason":"awaiting_approval"}]}
    snapshot["creative_evidence_events"] = [{**binding("high-value"), "id":"verified-click-credit", "event_type":"click_credit", "source":"native click credit fixture",
                                             "verified":True, "observed_at":"2026-11-16T12:00:00Z", "occurred_at":"2026-11-14T16:00:00Z",
                                             "report_date":"2026-11-14", "state":"observed", "value":1735, "currency":"USD", "credit_type":"click",
                                             "attribution_window":"explicit 7d click"}]
    plan = {"paid_sweep":snapshot, "adjudications":[], "first_proposals":[first_proposal], "prior_sweeps":[prior], "evidence_ids":["frozen-census"]}
    plan["manual_pauses"] = [{**binding("existing-manual"), "actor_type":"owner_manual", "source":"activity log fixture", "applied_at":"2026-11-15T14:00:00Z",
                              "readback":{**binding("existing-manual"), "source":"independent native object fixture", "independent":True,
                                          "read_at":"2026-11-15T14:05:00Z", "configured_status":"PAUSED", "effective_status":"PAUSED"}}]
    if not resolve_disagreement:
        plan["decision_views"] = [{**binding("review-disagreement"), "reviewer":reviewer, "observed_at":as_of,
                                  "platform_snapshot_source":"lifecycle-current", "merchant_snapshot_source":"separate synthetic merchant snapshot",
                                  "disposition":disposition, "rationale":rationale}
                                  for reviewer,disposition,rationale in [
            ("operator-a","cut_candidate","Clean earlier windows accumulated spend without checkout or purchase."),
            ("operator-b","watch","Large verified old click credit changes exposure tradeoff but needs a bounded look.")]]
    for case in book["cases"]:
        ad_id, intent = case["id"], case["intent"]
        if intent == "manual_paused" or (intent == "disagreement" and not resolve_disagreement):
            continue
        row = epoch_by_id[ad_id]
        is_cut = intent in {"cut_candidate", "disagreement"}
        window = "partial_day" if ad_id == "new-partial" else ("last_3_closed" if intent != "linked_credit" else "lifecycle")
        read = row["metrics"][window]
        disposition = "cut_candidate" if is_cut else intent if intent in {"low_opportunity", "main_retained", "zero_exposure"} else "watch"
        rationale = "Own comparable delivery and weak downstream progression support operational rotation." if is_cut else "Resolve bounded next observation using this ad's own measured opportunity."
        judge = {**binding(ad_id), "source":"explicit synthetic reviewer", "observed_at":as_of, "disposition":disposition,
                 "cut_assessed":True, "rationale":rationale, "evidence_ids":["frozen-census"],
                 "performance_review":{"window":window,"observed":{key:read[key] for key in PERFORMANCE_FIELDS},
                                       "assessment":"limited" if intent == "low_opportunity" else "adequate", "rationale":rationale,
                                       "counterevidence":"Do not infer lost orders or causal creative inferiority from sparse attribution."}}
        if "merchant_evidence" in case:
            judge["merchant_evidence"] = case["merchant_evidence"]
        if is_cut:
            judge["action_review"] = {"rationale":rationale, "counterevidence":"Old clicks or intermediate actions are retained but did not repeat in the relevant window.",
                                      "parent_effect":"Batch topology only; verify against native read before any mutation.", "next_read_at":next_read,
                                      "creative_test_basis":{"kind":"observed_ad_performance", "metric_window":window, "rationale":rationale, "evidence_ids":["frozen-census"]}}
        elif intent != "zero_exposure":
            date_window = {"start_date":"2026-11-16", "end_date":"2026-11-16"}
            observed_window = {"start_date":"2026-11-15", "end_date":"2026-11-15"} if ad_id != "new-partial" else date_window
            condition_window = date_window if ad_id != "new-partial" else {"start_date":"2026-11-17", "end_date":"2026-11-17"}
            due = next_read if ad_id != "new-partial" else "2026-11-18T21:00:00Z"
            basis = ({"kind":"first_checkout", "window":observed_window} if intent == "first_checkout" else
                     {"kind":"first_clean_window", "window":date_window} if intent == "first_clean_window" else
                     {"kind":"material_credit", "event_id":"verified-click-credit"} if intent == "linked_credit" else
                     {"kind":"approved_retention"} if intent == "main_retained" else
                     {"kind":"low_opportunity", "window":observed_window, "metric":"spend", "value":12,
                      "source":f"fixture-specific documented design for {ad_id}; not a universal cutoff"})
            condition = {"kind":"metric", "window":condition_window, "metric":"purchases", "op":"eq", "value":0, "source":"account-local next read plan fixture"}
            judge["continuation"] = {"basis":"approved_retention" if intent == "main_retained" else "test_information", "rationale":rationale,
                                     "expected_information":"Observe the next complete day's checkout and purchase progression.",
                                     "cost_of_waiting":"Expected additional own delivery is estimated from the current pace.",
                                     "cost_of_stopping":"Could forgo evaluation of still scarce or recently changed own delivery.",
                                     "exposure_context":"Parent budget remains unchanged; forecast is not a hard cap.",
                                     "evidence_ids":["frozen-census"], "change_kind":"first_read", "prior":None, "increment":None,
                                     "current":{"spend":row["metrics"]["lifecycle"]["spend"], "platform_outcomes":row["metrics"]["lifecycle"]["purchases"],
                                                "merchant_outcomes":None},
                                     "trigger":{"condition":"Read this ad's purchase count on the defined complete day.",
                                                "response":"Reassess operational rotation if no purchase; do not write without approval."},
                                     "watch_contract":{"basis":basis, "question":"Does qualified activity progress by the next completed account-local read?",
                                                        "due_at":due, "condition":condition,
                                                        "wait_cost":{"kind":"estimated_range", "currency":"USD", "lower":0, "upper":45, "source":"synthetic current pacing estimate; no hard cap"}}}
        plan["adjudications"].append(judge)
    return plan


def by_id(result):
    return {row["ad_id"]:row for row in result["entities"]}


def history_attachment(payload, prior_ad_id, continuation=None):
    old = payload["prior_sweeps"][0]
    row = by_id(old)[prior_ad_id]
    as_of = old["scope"]["as_of"]
    record = {"entity_id": prior_ad_id, "binding_epoch": row["epoch_id"], "disposition":"reduce"}
    if continuation:
        record.update(disposition="continue", continuation=continuation)
    return {"sweep":old, "packet":{"created_at":as_of, "paid_audit":{"as_of":as_of, "campaign_id":old["scope"]["campaign_id"], "decisions":[record]}}}


def final_packet(result):
    packet = directional_packet(direction="reduce")
    scope = result["scope"]
    packet.update(schema_version="1.4", created_at=scope["as_of"], paid_audit=result["paid_audit"], metrics=[])
    packet["scope"].update(platforms=[scope["platform"]], accounts=[scope["account_id"]], entities=[scope["campaign_id"]],
                           **{key:scope[key] for key in ("currency", "timezone", "attribution", "report_time")})
    packet["evidence"][0].update(id="frozen-census", retrieved_at=scope["as_of"], source="independent synthetic frozen census", claim="Synthetic entity rechecks use the exact frozen scope and read time.")
    packet["plan"]["decision_basis"]["source_ids"] = ["frozen-census"]
    return packet


class CreativeReviewPlanTests(unittest.TestCase):
    def test_no_fallback_for_unreviewed_paid_or_disagreeing_row_and_top_is_display_only(self):
        payload = sample_payload()
        payload["adjudications"] = [row for row in payload["adjudications"] if row["ad_id"] != "unproductive-incumbent"]
        result = build_plan(payload, top=1)
        rows = by_id(result)
        self.assertEqual(len(rows), 14)
        self.assertEqual(rows["unproductive-incumbent"]["issues"], ["missing_explicit_adjudication"])
        self.assertEqual(rows["unproductive-incumbent"]["disposition"], "unresolved")
        self.assertIn("unproductive-incumbent", result["candidate_lanes"]["zero_purchase_by_recent_and_lifecycle_spend"])
        self.assertEqual(len(result["summary"]["top"]["zero_purchase_by_recent_and_lifecycle_spend"]), 1)
        self.assertEqual({view["disposition"] for view in rows["review-disagreement"]["same_snapshot_views"]}, {"watch", "cut_candidate"})
        self.assertEqual(rows["review-disagreement"]["disposition"], "unresolved")
        self.assertFalse(result["packet_eligible"])
        self.assertIsNone(result["paid_audit"])

    def test_cuts_waiting_exposure_and_batch_effect_are_separate(self):
        result = build_plan(sample_payload())
        rows = by_id(result)
        self.assertEqual(set(result["cut_recommendation_ids"]), {"unproductive-incumbent","old-credit-awaiting","cart-heavy-stall","old-winner-declining"})
        self.assertEqual(rows["old-credit-awaiting"]["proposal_status"], "awaiting_approval")
        self.assertEqual(rows["old-credit-awaiting"]["first_proposal_exposure"]["wait_hours"], 48)
        self.assertEqual(rows["old-credit-awaiting"]["first_proposal_exposure"]["observed_platform_spend_delta"], 163)
        alpha = next(row for row in result["parent_effects"] if row["parent_id"] == "alpha")
        self.assertEqual(alpha["proposed_pause_ids"], ["old-credit-awaiting","unproductive-incumbent"])
        self.assertEqual(alpha["remaining_eligible_ids"], ["first-checkout"])
        self.assertEqual(alpha["redistribution"], "not yet observed")
        self.assertEqual(result["execution_authority"], "not_granted_by_plan")

    def test_bounded_watches_keep_real_checkout_limited_opportunity_and_mixed_day_distinct(self):
        rows = by_id(build_plan(sample_payload()))
        self.assertEqual(rows["first-checkout"]["watch_evaluation"]["verified_fact"]["kind"], "first_checkout")
        self.assertEqual(rows["mixed-treatment-day"]["watch_evaluation"]["verified_fact"]["kind"], "first_clean_window")
        self.assertEqual(rows["mixed-treatment-day"]["metrics"]["current_epoch"]["start_date"], "2026-11-16")
        for ad_id in ("limited-opportunity-a","limited-opportunity-b","new-partial"):
            self.assertEqual(rows[ad_id]["disposition"], "low_opportunity", rows[ad_id]["issues"])
        self.assertEqual(rows["observed-zero"]["disposition"], "zero_exposure")
        large = rows["high-value"]
        self.assertEqual(large["watch_evaluation"]["verified_fact"]["kind"], "material_credit")
        self.assertEqual(large["metrics"]["lifecycle"]["purchase_value"], 1925)
        self.assertEqual(large["merchant_evidence"]["value"], 1735)
        self.assertAlmostEqual(large["platform_credit_sensitivity"]["sensitivity_roas_without_credit"], 190 / 503)

    def test_bad_bindings_and_manual_activity_without_independent_read_cannot_export(self):
        payload = sample_payload(resolve_disagreement=True)
        wrong = next(row for row in payload["adjudications"] if row["ad_id"] == "unproductive-incumbent")
        wrong["epoch_id"] = "stale-epoch"
        another = next(row for row in payload["adjudications"] if row["ad_id"] == "cart-heavy-stall")
        another["ad_id"] = "outside-census"
        payload["manual_pauses"][0]["readback"]["independent"] = False
        result = build_plan(payload)
        rows = by_id(result)
        self.assertNotIn("unproductive-incumbent", result["cut_recommendation_ids"])
        self.assertIn("adjudication_not_bound_to_current_id_epoch_and_asof", rows["unproductive-incumbent"]["issues"])
        self.assertEqual(rows["cart-heavy-stall"]["disposition"], "unresolved")
        self.assertEqual(rows["existing-manual"]["disposition"], "unresolved")
        self.assertFalse(result["packet_eligible"])

    def test_exact_main_retention_and_manual_historical_projection(self):
        payload = sample_payload(resolve_disagreement=True)
        result = build_plan(payload)
        rows = by_id(result)
        self.assertTrue(result["packet_eligible"], result["issues"])
        self.assertEqual(len(result["paid_audit"]["decisions"]), 13)
        self.assertEqual(rows["existing-manual"]["disposition"], "manual_paused")
        self.assertEqual(rows["existing-manual"]["proposal_status"], "manual_pause_verified")
        self.assertEqual(rows["proven-main"]["disposition"], "main_retained")
        payload["paid_sweep"]["decision_handoff"]["decisions"][0]["binding"]["epoch_id"] = "nonmatching"
        self.assertEqual(by_id(build_plan(payload))["proven-main"]["disposition"], "unresolved")

    def test_paid_metric_forgery_and_wait_anchor_future_fail(self):
        payload = sample_payload(resolve_disagreement=True)
        row = next(row for row in payload["adjudications"] if row["ad_id"] == "unproductive-incumbent")
        row["performance_review"]["observed"]["checkout"] = 4
        payload["first_proposals"][0] = {**payload["first_proposals"][0], "snapshot_as_of":"2026-11-16T14:00:00Z"}
        result = build_plan(payload)
        self.assertIn("performance_review.observed.checkout must match the chosen sweep window", by_id(result)["unproductive-incumbent"]["issues"])
        wait = by_id(result)["old-credit-awaiting"]["first_proposal_exposure"]
        self.assertEqual(wait["state"], "wait_only")
        self.assertIsNone(wait["observed_platform_spend_delta"])
        self.assertFalse(result["packet_eligible"])

    def test_projected_paid_audit_validates_strict_with_same_history(self):
        payload = sample_payload(resolve_disagreement=True)
        payload["creative_history"] = history_attachment(payload, "old-credit-awaiting")
        result = build_plan(payload)
        self.assertTrue(result["packet_eligible"], result["issues"])
        errors, warnings = validate(final_packet(result), paid_sweep=payload["paid_sweep"], creative_test=True,
                                    creative_history=payload["creative_history"])
        self.assertEqual(errors + warnings, [])

    def test_frozen_met_trigger_cannot_renew_with_same_unproven_unproductive_watch(self):
        payload = sample_payload(resolve_disagreement=True)
        row = next(row for row in payload["adjudications"] if row["ad_id"] == "unproductive-incumbent")
        new_watch = deepcopy(next(item for item in payload["adjudications"] if item["ad_id"] == "first-checkout")["continuation"])
        old_watch = deepcopy(new_watch["watch_contract"])
        old_watch["due_at"] = "2026-11-15T21:00:00Z"
        old_watch["condition"]["window"] = {"start_date":"2026-11-14", "end_date":"2026-11-14"}
        payload["creative_history"] = history_attachment(payload, "unproductive-incumbent", {"next_read_at":old_watch["due_at"], "watch_contract":old_watch})
        new_watch["rationale"] += " Same check continues."
        new_watch["trigger"]["state"] = "pending"
        row.update(disposition="watch", continuation=new_watch)
        result = build_plan(payload)
        reviewed = by_id(result)["unproductive-incumbent"]
        self.assertEqual(reviewed["watch_evaluation"]["prior_trigger_state"], "met")
        self.assertIn("watch_trigger_must_match_derived_observation", reviewed["issues"])
        self.assertEqual(reviewed["disposition"], "unresolved")
        self.assertFalse(result["packet_eligible"])


if __name__ == "__main__":
    unittest.main()
