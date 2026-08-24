# EMB Media Buyer

An evidence-led, cross-platform paid-media skill for Codex. It supports strategy, account audits, diagnosis, measurement, budgeting, creative testing, forecasting, reporting, and approval-gated execution across major advertising platforms.

The skill keeps platform-attributed results, advertiser-owned business outcomes, and causal evidence separate. It reconciles query coverage and conversion aliases before declaring zeros, records threshold provenance, avoids universal kill/scale rules, verifies volatile platform facts at runtime, and requires explicit approval, preflight, independent read-back, and rollback planning before live changes.

## Install

```bash
git clone https://github.com/emrahbilaloglu-ui/emb-media-buyer.git ~/.codex/skills/emb-media-buyer
```

## Invoke

```text
Use $emb-media-buyer to audit my paid media, reconcile business economics, and produce an evidence-led decision plan.
```

## Included

- Cross-platform operating guides and current-source registry
- Unit economics, pacing, marginal-return, noise, and power calculations
- Decision-packet schema and validator
- Approval-gated API execution and recovery contracts
- Adversarial decision and trigger-boundary evaluations
- Security, privacy, consent, claims, and responsible-automation guardrails

Decision-packet schema `1.1` requires `plan.threshold_records` (an empty array when no exact threshold is used). Money-moving packets need at least one sourced record; an unapproved `proposed_governance` threshold cannot authorize a live change.

## Validate

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
```

Passing validation confirms package structure and deterministic tests; it does not prove real-account performance or authorize live advertising changes.
