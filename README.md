# EMB Omni Media Buyer

EMB Omni Media Buyer is an evidence-led, cross-platform paid-media operating system for Codex. It supports strategy, account audits, account-specific diagnosis, comparable benchmarking, funnel analysis, measurement, budgeting, pacing, forecasting, objective-aware weekly business reviews, and approval-gated execution across major advertising platforms.

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
- TikTok for Business MCP discovery and safe operations across regular campaigns, Smart+, Shop/GMV Max, lead generation, apps, R&F, reporting, diagnostics, and catalog workflows
- Unit economics, pacing, marginal-return, noise, and power calculations
- Deterministic within-account benchmark, funnel, and WBR arithmetic
- Decision-packet schema and validator
- Approval-gated API execution and recovery contracts
- Adversarial decision and trigger-boundary evaluations
- Blind host-by-skill behavioral evaluation protocol with no-skill baselines and negative-arm detection
- Security, privacy, consent, claims, and responsible-automation guardrails
- Machine-readable reconciliation of all 55 TikTok Agentic Hub skills, with creative work routed outside the media-buyer boundary

Decision-packet schema `1.3` separates claim strength, exposure increase/reduction/rotation/continuation, sourced decision basis, and scoped unresolved gates. Qualitative risk stops need no invented numeric threshold or safety incident; paid KEEP/WATCH needs a current continuation rationale. Unknown margin still gates unsupported growth/profit. Version `1.2` packets remain supported under their conservative legacy checks. Execute packets retain exact approval, resolved write/read tools, recomputed deltas, exposure arithmetic with nominal-reference versus verified-bound semantics, independent read-back, and rollback. An applied state passes only when the fresh observed projection matches exactly; non-execute packets cannot carry staged writes.

## Validate

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
```

Passing validation confirms package structure and deterministic tests; it does not prove real-account performance or authorize live advertising changes.
