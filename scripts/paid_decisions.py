#!/usr/bin/env python3
"""Carry forward historical paid decisions from caller-supplied, scoped evidence.

Use ``handoff(payload)`` or pass a JSON file (or ``-``) on the command line.
``scope``, ``inventory`` and ``current_rows`` use the paid sweep's normalized
contract. Decision, proposal, application, transition and retention records use
the five fields in BINDING. Timestamps are ISO 8601 with an explicit offset.
The output describes evidence and parent scenarios, and conveys no authority.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


BINDING = ("account_id", "campaign_id", "parent_id", "ad_id", "epoch_id")
PARENT = BINDING[:3]
OPEN = {"open", "pending", "deferred", "trigger_met", "rebind"}
DECISION_STATES = OPEN | {"rejected", "applied_verified", "closed_new_evidence"}
APPLICATION_STATES = {
    "pending", "accepted", "in_process", "deferred", "rejected", "failed",
    "unknown", "readback_mismatch", "applied_verified",
}
REMAINING_REASONS = {
    "awaiting_approval", "deferred", "rejected", "trigger_met", "rebind",
    "out_of_approved_scope", "new_evidence", "open", "not_attempted",
    "pending", "accepted", "in_process", "failed", "unknown", "readback_mismatch",
}
ACTION_STATUS = {"pause": "PAUSED", "activate": "ACTIVE"}
ACTIVE = {"ACTIVE", "ENABLED", "DELIVERING"}
INELIGIBLE = {
    "PAUSED", "DISABLED", "ARCHIVED", "DELETED", "REMOVED", "ENDED", "COMPLETED",
    "INACTIVE", "ADSET_PAUSED", "CAMPAIGN_PAUSED", "DISAPPROVED",
}


class InputError(ValueError):
    """The payload is malformed or contains duplicate identifiers."""


def obj(value, name):
    if not isinstance(value, dict):
        raise InputError(f"{name} must be an object")
    return value


def string(value, name):
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{name} must be a nonempty string")
    return value


def timestamp(value, name):
    try:
        dt = datetime.fromisoformat(string(value, name).replace("Z", "+00:00"))
    except ValueError as error:
        raise InputError(f"{name} must be an ISO 8601 timestamp with offset") from error
    if dt.utcoffset() is None:
        raise InputError(f"{name} must include a UTC offset")
    return dt


def records(container, name):
    rows = container.get(name, [])
    if not isinstance(rows, list):
        raise InputError(f"{name} must be a list")
    return [obj(row, name) for row in rows]


def key(row, fields=BINDING):
    return tuple(string(row.get(field), field) for field in fields)


def index(rows, identify, name):
    out = {}
    for row in rows:
        row_key = identify(row)
        if row_key in out:
            raise InputError(f"duplicate {name} key: {row_key}")
        out[row_key] = row
    return out


def snapshot_index(rows, name, issue):
    identified = {}
    for row in rows:
        bound = tuple(row.get(field) if isinstance(row.get(field), str) and row[field].strip() else None
                      for field in BINDING)
        if None in bound[:4]:
            issue(bound, f"{name}_identity_unresolved")
            continue
        if bound[4] is None and not passive_historical(row):
            issue(bound, f"{name}_epoch_unresolved")
        if bound in identified:
            raise InputError(f"duplicate {name} key: {bound}")
        identified[bound] = row
    return identified


def passive_historical(row):
    return status(row.get("configured_status")) in INELIGIBLE and status(row.get("effective_status")) in INELIGIBLE


def choose(value, allowed, name):
    value = string(value, name)
    if value not in allowed:
        raise InputError(f"unsupported {name}: {value}")
    return value


def next_review(value):
    review = obj(value, "next_review")
    timestamp(review.get("at"), "next_review.at")
    string(review.get("condition"), "next_review.condition")
    string(review.get("source"), "next_review.source")
    return review


def evidence_time(value, name, as_of):
    evidence = obj(value, name)
    string(evidence.get("source"), f"{name}.source")
    string(evidence.get("detail"), f"{name}.detail")
    observed = timestamp(evidence.get("observed_at"), f"{name}.observed_at")
    if observed > as_of:
        raise InputError(f"{name} cannot use evidence from after the snapshot")
    return observed


def decision_key(row):
    # Parent and campaign identity are validated independently. They must not
    # let two records for the same account/ad/epoch/instant evade deduplication.
    bound = key(row)
    return bound[0], bound[3], bound[4], timestamp(row.get("as_of"), "decision.as_of")


def validate_decision(row, as_of):
    state = choose(row.get("status"), DECISION_STATES, "decision.status")
    string(row.get("reason"), "decision.reason")
    observed = timestamp(row["as_of"], "decision.as_of")
    if state in OPEN:
        review = next_review(row.get("next_review"))
        if timestamp(review["at"], "next_review.at") <= observed:
            raise InputError("open decision next_review.at must follow its as_of")
    if state == "trigger_met":
        trigger = obj(row.get("trigger"), "trigger")
        string(trigger.get("condition"), "trigger.condition")
        evidence_time(trigger, "trigger", min(as_of, observed))
    if state == "closed_new_evidence":
        evidence_time(row.get("closure_evidence"), "closure_evidence", min(as_of, observed))


def checked_number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            if math.isfinite(value) and value >= 0:
                return value
        except OverflowError:
            pass
    return None


def difference(after, before):
    if checked_number(after) is None or checked_number(before) is None:
        return None
    return float(Decimal(str(after)) - Decimal(str(before)))


def ledger_delta(before, after, fields, basis, as_of, previous):
    if not isinstance(before, dict) or not isinstance(after, dict):
        return {"state": "unknown", "reason": "missing_snapshot"}
    if not all(before.get(field) is not None and before[field] == after.get(field) for field in basis):
        return {"state": "not_comparable", "reason": "scope_or_definition_changed"}
    try:
        before_time = timestamp(before.get("as_of"), "prior observation.as_of")
        after_time = timestamp(after.get("as_of"), "current observation.as_of")
        string(before.get("source"), "prior observation.source")
        string(after.get("source"), "current observation.source")
    except InputError:
        return {"state": "unknown", "reason": "snapshot_source_or_time_missing"}
    if not before_time <= previous < after_time <= as_of:
        return {"state": "not_comparable", "reason": "snapshot_chronology_mismatch"}
    deltas = {field: difference(after.get(field), before.get(field)) for field in fields}
    return {
        "state": "comparable" if all(value is not None for value in deltas.values()) else "partial",
        "deltas": deltas,
        "prior_source": before["source"],
        "current_source": after["source"],
    }


def dated_observations(rows, through, start):
    result = {}
    for row in rows:
        row = obj(row, "ad day observation")
        raw_day = string(row.get("date"), "ad day observation.date")
        try:
            day = date.fromisoformat(raw_day)
        except ValueError as error:
            raise InputError("ad day observation.date must use YYYY-MM-DD") from error
        if day.isoformat() != raw_day or not start <= day <= through:
            raise InputError("ad day observation.date is outside its snapshot window")
        if day in result:
            raise InputError(f"duplicate ad day observation: {raw_day}")
        result[day] = {field: checked_number(row.get(field)) for field in ("spend", "purchases", "purchase_value")}
    return result


def dated_report_changes(before, after, comparable):
    if not comparable or not all(isinstance(snapshot.get("ad_day_observations"), list) for snapshot in (before, after)):
        return {"state": "unknown", "reason": "comparable_dated_snapshots_unavailable"}
    timezone = ZoneInfo(after["timezone"])
    prior_date = timestamp(before["as_of"], "prior observation.as_of").astimezone(timezone).date()
    current_date = timestamp(after["as_of"], "current observation.as_of").astimezone(timezone).date()
    try:
        start = date.fromisoformat(after["start_date"])
    except (TypeError, ValueError) as error:
        raise InputError("comparable dated snapshots require an ISO lifecycle start date") from error
    old = dated_observations(before["ad_day_observations"], prior_date, start)
    new = dated_observations(after["ad_day_observations"], current_date, start)
    if not old and not new:
        return {"state": "unknown", "reason": "no_observed_report_dates"}
    revisions, later, missing = [], [], []
    partial = None
    for day in sorted(set(old) | set(new)):
        label = day.isoformat()
        if day > prior_date:
            later.append({"date": label, "observation": new[day], "partial_as_of": day == current_date})
        elif day not in old or day not in new:
            missing.append({"date": label, "missing_from": "prior" if day not in old else "current"})
        else:
            deltas = {field: difference(new[day][field], old[day][field]) for field in new[day]}
            change = {"date": label, "deltas": deltas, "state": "partial" if None in deltas.values() else "observed"}
            if day == prior_date:
                partial = {**change, "still_partial_as_of": day == current_date}
            elif any(value != 0 for value in deltas.values()):
                revisions.append(change)
    return {
        "state": "partial" if missing or partial is None or any(
            value is None for snapshot in (old, new) for row in snapshot.values() for value in row.values()
        ) else "compared",
        "prior_closed_date_revisions": revisions,
        "prior_partial_date_roll_forward": partial,
        "later_report_dates": later,
        "missing_counterpart_dates": missing,
    }


def observations(prior, current, native_row, scope, as_of, meta_source):
    lifecycle = (native_row or {}).get("metrics", {}).get("lifecycle", {})
    before = (prior or {}).get("observation", {})
    after = (current or {}).get("observation", {})
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise InputError("observation must be an object")
    meta = {
        "source": lifecycle.get("source") or meta_source,
        "as_of": scope["as_of"],
        "start_date": lifecycle.get("start_date"),
        **{field: scope.get(field) for field in ("currency", "timezone", "attribution", "report_time")},
        **{field: lifecycle.get(field) for field in ("spend", "purchases", "purchase_value")},
        "revision": (native_row or {}).get("revision"),
        "ad_day_observations": (native_row or {}).get("ad_day_observations"),
    }
    merchant = after.get("merchant")
    if merchant is not None:
        merchant = obj(merchant, "current merchant observation")
        string(merchant.get("source"), "current merchant observation.source")
        if timestamp(merchant.get("as_of"), "current merchant observation.as_of") > as_of:
            raise InputError("current merchant observation is dated after scope.as_of")
    result = {"prior": before or None, "current": {"meta": meta, "merchant": merchant}}
    if prior is None:
        return result
    previous = timestamp(prior["as_of"], "prior decision.as_of")
    result["meta_change"] = ledger_delta(
        before.get("meta"), meta, ("spend", "purchases", "purchase_value"),
        ("start_date", "currency", "timezone", "attribution", "report_time"), as_of, previous,
    )
    result["meta_change"]["interpretation"] = "snapshot differences may include attribution revisions"
    result["meta_change"]["dated_report_changes"] = dated_report_changes(
        before.get("meta"), meta, result["meta_change"]["state"] in {"comparable", "partial"},
    )
    result["merchant_change"] = ledger_delta(
        before.get("merchant"), merchant, ("orders", "value"),
        ("start_date", "currency", "timezone", "definition", "binding_basis"), as_of, previous,
    )
    return result


def eligible(row):
    configured, effective = status(row.get("configured_status")), status(row.get("effective_status"))
    if configured in ACTIVE and effective in ACTIVE:
        return True
    if effective in INELIGIBLE and (configured in INELIGIBLE or configured in ACTIVE):
        return False
    return None


def status(value):
    return value.strip().upper() if isinstance(value, str) else "UNKNOWN"


def applied_application(row, proposal, ad, as_of):
    """Only an exact, independent post-read can settle a recorded application."""
    if proposal is None:
        return False, "no_matching_proposal"
    action = choose(row.get("action"), ACTION_STATUS, "application.action")
    if action != proposal["action"]:
        return False, "application_action_mismatch"
    if ad is None or ad.get("binding_verified") is not True:
        return False, "native_binding_unverified"
    if row["status"] != "applied_verified":
        return False, row["status"]
    try:
        applied = timestamp(row.get("applied_at"), "application.applied_at")
        mutation_source = string(row.get("source"), "application.source")
        readback = obj(row.get("readback"), "application.readback")
        read_at = timestamp(readback.get("read_at"), "readback.read_at")
        read_source = string(readback.get("source"), "readback.source")
        if key(readback) != key(row):
            return False, "readback_binding_mismatch"
        if ad.get("epoch_started_at") is not None and applied < timestamp(ad["epoch_started_at"], "epoch_started_at"):
            return False, "application_predates_binding"
    except InputError:
        return False, "readback_evidence_missing"
    if not timestamp(proposal["proposed_at"], "proposal.proposed_at") <= applied < read_at <= as_of:
        return False, "readback_not_fresh_as_of"
    expected = ACTION_STATUS[action]
    if readback.get("independent") is not True or read_source == mutation_source:
        return False, "readback_not_independent"
    if readback.get("configured_status") != expected or readback.get("effective_status") != expected:
        return False, "readback_status_mismatch"
    return True, None


def authorization_evidence(row, bound, as_of):
    evidence = row.get("authorization")
    if evidence is None:
        return {"recorded_status": "unknown", "record": None}
    evidence = obj(evidence, "authorization")
    state = choose(evidence.get("status"), {"approved", "rejected", "awaiting_approval", "revoked"}, "authorization.status")
    source = string(evidence.get("source"), "authorization.source")
    at = timestamp(evidence.get("at"), "authorization.at")
    if key(evidence) != bound or evidence.get("action") != row.get("action") or at > as_of:
        raise InputError("recorded authorization must match the application binding and as-of")
    return {"recorded_status": state, "source": source, "record": evidence}


def before_application(row):
    before = row.get("before")
    if not isinstance(before, dict):
        return None
    try:
        if key(before) != key(row) or not before.get("source"):
            return None
        read_at = timestamp(before.get("read_at"), "application.before.read_at")
        applied = timestamp(row.get("applied_at"), "application.applied_at")
    except InputError:
        return None
    return eligible(before) if read_at <= applied else None


def roster(statuses, parent_status):
    known = sorted(ad_id for ad_id, state in statuses.items() if state is True)
    uncertain = sorted(ad_id for ad_id, state in statuses.items() if state is None)
    if not known and not uncertain:
        topology = "empty"
    elif uncertain:
        topology = "uncertain"
    elif len(known) == 1:
        topology = "sole_remaining"
    else:
        topology = "multiple_remaining"
    return {
        "topology": topology, "eligible_child_ids": known, "unknown_child_ids": uncertain,
        "sole_remaining_ad_id": known[0] if topology == "sole_remaining" else None,
        "parent_eligibility": parent_status,
        "concentration": "possible_on_sole_child" if topology == "sole_remaining" and parent_status is True else "undetermined",
    }


def parent_effects(parents, ads, proposals, verified, exact, inventory_complete):
    by_parent = {}
    for bound in proposals:
        by_parent.setdefault(bound[:3], []).append(bound)
    children = {}
    for bound, row in ads.items():
        children.setdefault(bound[:3], {})[bound[3]] = eligible(row)
    output = []
    for parent_key, proposal_keys in sorted(by_parent.items()):
        parent = parents.get(parent_key, {})
        parent_status = eligible(parent)
        native = children.get(parent_key, {})
        baseline = dict(native)
        after_verified = dict(native)
        for bound in proposal_keys:
            if bound in verified:
                baseline[bound[3]] = before_application(verified[bound])
                after_verified[bound[3]] = verified[bound]["action"] == "activate"
        projected = dict(baseline)
        for bound in proposal_keys:
            projected[bound[3]] = (proposals[bound]["action"] == "activate") if exact(bound) else None
        scenarios = {
            "before_projection": roster(baseline, parent_status),
            "native_as_of": roster(native, parent_status),
            "if_entire_proposed_batch_applied": roster(projected, parent_status),
            "with_verified_applications": roster(after_verified, parent_status),
        }
        if not inventory_complete:
            for scenario in scenarios.values():
                scenario.update(topology="uncertain_inventory", sole_remaining_ad_id=None, concentration="undetermined")
        output.append({
            **dict(zip(PARENT, parent_key)),
            "configured_status": parent.get("configured_status"),
            "effective_status": parent.get("effective_status"),
            "nominal_daily_budget": checked_number(parent.get("daily_budget")),
            "currency": parent.get("currency"),
            **scenarios,
            "proposed_ad_ids": sorted(bound[3] for bound in proposal_keys),
            "verified_applied_ad_ids": sorted(bound[3] for bound in proposal_keys if bound in verified),
            "interpretation": "Child roster scenarios use the supplied parent and sibling snapshot. "
                              "Allocation, realized spend, savings and delivery remain unknown.",
        })
    return output


def epoch_context(ad, row, event, timezone, as_of):
    metrics = (row or {}).get("metrics", {})
    output = {
        "whole_ad_lifecycle": metrics.get("lifecycle"),
        "current_binding_window": metrics.get("current_epoch") if ad.get("epoch_started_at") and ad.get("binding_verified") is True else None,
        "binding_started_at": ad.get("epoch_started_at"),
        "first_delivery_at": None,
        "transition": "unknown",
    }
    if event is None:
        return output
    kind = choose(event.get("kind"), {"unchanged", "measurement", "treatment"}, "epoch.kind")
    string(event.get("source"), "epoch.source")
    old_epoch = string(event.get("from_epoch_id"), "epoch.from_epoch_id")
    at = timestamp(event.get("effective_at"), "epoch.effective_at")
    native_start = timestamp(ad.get("epoch_started_at"), "epoch_started_at")
    if at != native_start or at > as_of or (old_epoch == ad["epoch_id"]) != (kind == "unchanged"):
        raise InputError("epoch event contradicts native binding chronology or transition kind")
    if event.get("first_delivery_at") is not None:
        delivered = timestamp(event["first_delivery_at"], "epoch.first_delivery_at")
        string(event.get("delivery_source"), "epoch.delivery_source")
        if not at <= delivered <= as_of:
            raise InputError("first delivery is outside its binding's observed timeline")
        output["first_delivery_at"] = event["first_delivery_at"]
    local = at.astimezone(timezone)
    output.update({
        "transition": kind, "source": event["source"], "previous_epoch_id": old_epoch,
        "mixed_treatment_date": local.date().isoformat() if kind == "treatment" and local.time() != time() else None,
        "treatment_history_preserved": kind != "treatment",
    })
    return output


def media_counterevidence(rows, ads, as_of):
    result = {}
    for row in rows:
        bound = key(row)
        prior = obj(row.get("prior_media_binding"), "prior_media_binding")
        historical = key(prior)
        evidence_time(row, "media_history", as_of)
        media_hash = string(row.get("media_hash"), "media_hash")
        ad = ads.get(bound, {})
        if (ad.get("binding_verified") is not True or prior.get("binding_verified") is not True
                or historical[0] != bound[0] or historical[3] == bound[3]
                or ad.get("media_hash") != media_hash or prior.get("media_hash") != media_hash):
            raise InputError("media history requires verified equal hashes on distinct, same-account ad IDs")
        # Retain evidence identity and observation. Prior decision and approval
        # records do not become records on the target ad ID.
        result.setdefault(bound, []).append({
            "prior_binding": dict(zip(BINDING, historical)), "media_hash": media_hash,
            "source": row["source"], "observed_at": row["observed_at"], "detail": row["detail"],
        })
    return result


def handoff(payload):
    scope = obj(obj(payload, "payload").get("scope"), "scope")
    account = string(scope.get("account_id"), "scope.account_id")
    campaign = string(scope.get("campaign_id"), "scope.campaign_id")
    as_of = timestamp(scope.get("as_of"), "scope.as_of")
    try:
        timezone = ZoneInfo(string(scope.get("timezone"), "scope.timezone"))
    except ZoneInfoNotFoundError as error:
        raise InputError("scope.timezone is not an IANA timezone") from error
    inventory = obj(payload.get("inventory"), "inventory")
    manifest = obj(inventory.get("manifest"), "inventory.manifest")
    string(manifest.get("source_id"), "inventory.manifest.source_id")
    retrieved_at = timestamp(manifest.get("retrieved_at"), "inventory.manifest.retrieved_at")
    if (manifest.get("independent") is not True or manifest.get("account_id") != account
            or manifest.get("campaign_id") != campaign
            or timestamp(manifest.get("as_of"), "inventory.manifest.as_of") != as_of):
        raise InputError("independent native inventory must match scope account, campaign and as-of")
    meta_source = payload.get("current_meta_source")
    if meta_source is not None:
        string(meta_source, "current_meta_source")
    issues = []

    def issue(bound, reason):
        issues.append({"binding": dict(zip(BINDING, bound)), "reason": reason})

    inventory_complete = manifest.get("complete") is True and manifest.get("pagination_complete") is True and retrieved_at <= as_of
    if not inventory_complete:
        issue((account, campaign, None, None, None), "native_inventory_not_complete_at_as_of")

    ads = snapshot_index(records(inventory, "ads"), "native_ad", issue)
    index(ads.values(), lambda row: (row["account_id"], row["ad_id"]), "native ad")
    parents = index(records(inventory, "parents"), lambda row: key(row, PARENT), "parent")
    rows = snapshot_index(records(payload, "current_rows"), "sweep_row", issue)
    proposals = index(records(payload, "proposals"), key, "proposal")
    applications = index(records(payload, "applications"), key, "application")
    epochs = index(records(payload, "epoch_events"), key, "epoch event")
    retention = index(records(payload, "main_retention"), key, "retention mapping")
    media_history = media_counterevidence(records(payload, "media_history"), ads, as_of)
    rebinds = index(records(payload, "rebinds"), key, "rebind from old binding")
    prior_rows = records(payload, "prior_decisions")
    current_rows = records(payload, "current_decisions")
    index(prior_rows + current_rows, decision_key, "account/ad/epoch/as-of decision")
    prior = {}
    opened_at = {}
    first_seen = {}
    for row in sorted(prior_rows, key=lambda item: timestamp(item["as_of"], "prior decision.as_of")):
        observed = timestamp(row["as_of"], "prior decision.as_of")
        if observed >= as_of:
            raise InputError("prior decision must precede scope.as_of")
        validate_decision(row, as_of)
        bound = key(row)
        prior[bound] = row
        first_seen.setdefault(bound, observed)
        if row["status"] in OPEN:
            claimed_open = timestamp(row.get("opened_at", row["as_of"]), "decision.opened_at")
            if claimed_open > observed:
                raise InputError("decision.opened_at cannot follow its snapshot")
            opened_at.setdefault(bound, claimed_open)
        else:
            opened_at.pop(bound, None)
    current = index(current_rows, key, "current decision binding")
    for row in current.values():
        if timestamp(row["as_of"], "current decision.as_of") != as_of:
            raise InputError("current decision.as_of must match scope.as_of")
        validate_decision(row, as_of)
    for group in (ads, parents, proposals, applications, epochs, retention, rebinds, prior, current):
        if any(bound[:2] != (account, campaign) for bound in group):
            raise InputError("all bindings must be inside scope.account_id/campaign_id")

    def exact(bound):
        if bound not in ads or bound[4] is None or ads[bound].get("binding_verified") is not True or bound[:3] not in parents:
            return False
        if ads[bound].get("epoch_started_at") is None:
            return True
        try:
            return timestamp(ads[bound].get("epoch_started_at"), "epoch_started_at") <= as_of
        except InputError:
            return False

    for bound in set(ads) | set(rows):
        if bound not in ads or bound not in rows:
            issue(bound, "sweep_native_binding_missing")
        elif bound[:3] not in parents:
            issue(bound, "native_parent_missing")
        elif not exact(bound) and not passive_historical(ads[bound]):
            issue(bound, "native_binding_unverified")
        elif any(status(rows[bound].get(field)) != status(ads[bound].get(field)) for field in ("configured_status", "effective_status")):
            issue(bound, "sweep_native_status_mismatch")

    for bound, proposal in proposals.items():
        choose(proposal.get("action"), ACTION_STATUS, "proposal.action")
        string(proposal.get("reason"), "proposal.reason")
        string(proposal.get("counterevidence"), "proposal.counterevidence")
        if timestamp(proposal.get("proposed_at"), "proposal.proposed_at") > as_of:
            raise InputError("proposal is dated after scope.as_of")
        if not exact(bound):
            issue(bound, "proposal_binding_unverified")
        if proposal.get("next_review") is not None:
            next_review(proposal["next_review"])

    verified = {}
    application_results = []
    for bound, application in sorted(applications.items()):
        choose(application.get("status"), APPLICATION_STATES, "application.status")
        matched, reason = applied_application(application, proposals.get(bound), ads.get(bound) if exact(bound) else None, as_of)
        if matched:
            verified[bound] = application
        elif application["status"] == "applied_verified" or bound not in proposals:
            issue(bound, reason)
        application_results.append({
            "record": application, "verified": matched, "reason": reason,
            "authorization_evidence": authorization_evidence(application, bound, as_of),
            "native_status_matches_applied": (
                all(status(ads[bound].get(field)) == ACTION_STATUS[application["action"]]
                    for field in ("configured_status", "effective_status")) if matched else None
            ),
        })

    retained = set()
    for bound, mapping in retention.items():
        kind = choose(mapping.get("kind"), {"promoted_source", "candidate"}, "retention.kind")
        if kind == "candidate":
            continue
        main_ad = string(mapping.get("main_ad_id"), "retention.main_ad_id")
        main_campaign = string(mapping.get("main_campaign_id"), "retention.main_campaign_id")
        string(mapping.get("source"), "retention.source")
        string(mapping.get("policy_source"), "retention.policy_source")
        if exact(bound) and main_ad != bound[3] and main_campaign != bound[1] and mapping.get("binding_verified") is True:
            retained.add(bound)
        else:
            issue(bound, "promoted_source_binding_unverified")

    transitions = {}
    carried_from = {}
    carried_targets = set()
    for bound, transition in rebinds.items():
        to_epoch = string(transition.get("to_epoch_id"), "rebind.to_epoch_id")
        target = bound[:4] + (to_epoch,)
        disposition = choose(transition.get("disposition"), {"carry", "close"}, "rebind.disposition")
        string(transition.get("reason"), "rebind.reason")
        string(transition.get("source"), "rebind.source")
        at = timestamp(transition.get("at"), "rebind.at")
        old = prior.get(bound)
        valid = (old is not None and old["status"] in OPEN and target != bound and exact(target)
                 and ads[target].get("epoch_started_at") is not None)
        event = epochs.get(target, {})
        valid = valid and event.get("from_epoch_id") == bound[4] and event.get("kind") in {"measurement", "treatment"}
        if valid:
            start = timestamp(ads[target].get("epoch_started_at"), "epoch_started_at")
            valid = timestamp(old["as_of"], "prior decision.as_of") < start <= at <= as_of
        if not valid or (disposition == "carry" and target not in current and target not in prior):
            issue(bound, "unresolved_rebind")
            continue
        if disposition == "carry":
            if target in carried_targets:
                raise InputError("rebind carry has more than one preceding decision")
            if target in prior:
                if first_seen[target] < at:
                    issue(bound, "rebind_recorded_after_target_decision")
                    continue
                if opened_at.get(target) == first_seen[target]:
                    opened_at[target] = min(opened_at[target], opened_at[bound])
            else:
                carried_from[target] = bound
            carried_targets.add(target)
        transitions[bound] = transition

    decisions = []
    for bound in sorted(set(current) | set(prior) | set(proposals)):
        prior_bound = carried_from.get(bound, bound)
        old, new = prior.get(prior_bound), current.get(bound)
        transition = transitions.get(bound)
        proposed = proposals.get(bound)
        proposed_at = timestamp(proposed["proposed_at"], "proposal.proposed_at") if proposed is not None else None
        if new is not None and not exact(bound):
            issue(bound, "current_decision_binding_unverified")
            new = None
        if transition is not None:
            state = "rebind"
        elif new is None:
            state = "unresolved" if old is not None and old["status"] in OPEN else (old or {}).get("status")
            if state == "unresolved":
                issue(bound, "prior_open_decision_missing_current")
            elif proposed is not None and (old is None or proposed_at > timestamp(old["as_of"], "prior decision.as_of")):
                state = "applied_verified" if bound in verified else "open"
                if exact(bound):
                    new = {
                        **dict(zip(BINDING, bound)), "status": state, "as_of": scope["as_of"],
                        "reason": proposed["reason"], "next_review": proposed.get("next_review"),
                    }
        else:
            state = new["status"]
            if state == "applied_verified" and bound not in verified:
                state = "unresolved"
                issue(bound, "decision_application_unverified")
            if state == "rebind" and bound not in carried_targets:
                state = "unresolved"
                issue(bound, "decision_rebind_unverified")
            if state == "closed_new_evidence" and old is not None:
                observed = evidence_time(new["closure_evidence"], "closure_evidence", as_of)
                if observed <= timestamp(old["as_of"], "prior decision.as_of"):
                    state = "unresolved"
                    issue(bound, "closure_evidence_not_new")
        opened = opened_at.get(prior_bound)
        if new is not None and state in OPEN and opened is None:
            opened = proposed_at or as_of
        observation = observations(old, new, rows.get(bound), scope, as_of, meta_source)
        if new is not None and state != "unresolved":
            new = {**new, "observation": observation["current"]}
            if state in OPEN:
                new["opened_at"] = (opened or as_of).isoformat()
        decisions.append({
            "binding": dict(zip(BINDING, bound)), "status": state, "prior": old, "current": new,
            "open_age_seconds": (as_of - opened).total_seconds() if opened is not None else None,
            "rebind": transition or transitions.get(prior_bound),
            "observation": observation,
            "main_retained": bound in retained,
        })

    remaining = []
    for bound, proposal in sorted(proposals.items()):
        decision = current.get(bound, {})
        review = proposal.get("next_review", decision.get("next_review"))
        try:
            review = next_review(review)
        except InputError:
            issue(bound, "proposal_next_review_missing_or_untyped")
            review = None
        if bound in verified:
            continue
        if review is not None and timestamp(review["at"], "next_review.at") <= as_of:
            issue(bound, "remaining_proposal_next_review_is_stale")
        reason = proposal.get("remaining_reason", decision.get("remaining_reason"))
        if not isinstance(reason, str) or reason not in REMAINING_REASONS:
            issue(bound, "remaining_proposal_reason_missing_or_untyped")
            reason = None
        remaining.append({
            "proposal": proposal, "remaining_reason": reason, "next_review": review,
            "application_status": applications.get(bound, {}).get("status"),
            "main_retention_conflict": bound in retained and proposal["action"] == "pause",
        })

    contexts = []
    for bound, ad in sorted(ads.items()):
        event = epochs.get(bound)
        if event is not None and (not exact(bound) or ad.get("epoch_started_at") is None):
            issue(bound, "epoch_event_native_start_unverified")
            event = None
        context = epoch_context(ad, rows.get(bound), event, timezone, as_of)
        if not exact(bound):
            context["current_binding_window"] = None
        contexts.append({
            "binding": dict(zip(BINDING, bound)), **context,
            "same_media_counterevidence": media_history.get(bound, []),
        })
    for bound in sorted(set(epochs) - set(ads)):
        issue(bound, "epoch_event_binding_not_current")
    return {
        "scope": scope,
        "complete_for_decision": not issues,
        "decisions": decisions,
        "epoch_context": contexts,
        "remaining_proposals": remaining,
        "applications": application_results,
        "parent_effects": parent_effects(parents, ads, proposals, verified, exact, inventory_complete),
        "issues": sorted(issues, key=lambda item: (tuple(value or "" for value in item["binding"].values()), item["reason"])),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON input path or - for stdin")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        print(json.dumps(handoff(json.loads(raw)), indent=2, allow_nan=False))
    except (InputError, OSError, ValueError) as error:
        parser.exit(2, f"paid_decisions: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
