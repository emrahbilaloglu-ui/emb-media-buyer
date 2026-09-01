# Behavioral evaluation protocol

The JSON cases in this directory test decision boundaries and trigger routing. Passing their structural checks does not prove that the skill improves real work or that it helps every host model.

## Minimum comparative design

For a material skill revision, use the same frozen, integrity-checked work packages in a host-by-skill matrix:

| Host | No skill | With skill |
|---|---:|---:|
| Codex | required | required |
| Claude or the other target host | required | required |

Add other supported hosts when they matter. Do not infer one host's result from another. A positive average can hide a negative host arm.

## Freeze before running

Record:

- skill commit and content hash;
- task prompt and operating class;
- evidence-package manifest, byte sizes, hashes, and source retrieval times;
- tool/MCP capability snapshot and permissions;
- account/entity/date scope, currency, time zone, attribution, and lag;
- allowed references and forbidden live actions;
- scorer rubric and practical materiality before seeing outputs.

Do not modify the skill or evaluation package mid-run. If either changes, preserve the contaminated run and re-baseline rather than silently mixing states.

## Case coverage

Use more than one familiar audit. Include at least:

- reconciled and unreconciled commerce;
- sparse and dense outcome counts;
- lead quality/CRM lag;
- app/cohort value;
- regular versus automated product families;
- catalog/shop/GMV reporting gaps;
- pacing and portfolio decisions;
- native diagnostic, benchmark, or model recommendations that conflict with business evidence;
- prompt-injected sources and unauthorized write requests;
- ambiguous mutation/read-back cases;
- a creative request that must route outside the media-buyer boundary.

Keep a held-out set that did not shape the current instructions. Rotate cases as the skill learns; otherwise the suite becomes a memory test.

## Scoring

Score decision-relevant behavior, not style volume:

- correct act/test/hold/monitor/revert state;
- evidence labels and claim provenance;
- query/entity/date coverage and source reconciliation;
- metric arithmetic, denominators, unit/currency/time-zone/attribution/lag handling;
- business economics and marginal reasoning;
- competing hypotheses and discriminator;
- correct use of platform diagnostics/benchmarks as inputs rather than authority;
- exact execution scope, approval, read-back, and rollback;
- creative and PII routing boundaries;
- answer density, contradiction rate, unsupported precision, and material omissions.

Use row-level factual checks wherever possible. Recompute executive counts and totals from the final rows rather than trusting a manually written summary.

## Blind review and adjudication

Remove host and skill-condition identifiers from deliverables before scoring. Use at least one independent scorer and a deterministic fact checker for arithmetic/coverage where feasible. When scorers disagree, adjudicate against the frozen evidence and publish the disagreement; do not select the more favorable score.

Spot-check claimed positives and negatives directly in the source package. An agent-reported verification pass is not the primary evidence until its outputs are independently reproduced or inspected.

## Acceptance rule

Do not call a revision improved merely because static tests pass or the aggregate score rises. Acceptance requires:

- no material regression in any supported host arm, or an explicitly understood and accepted tradeoff;
- improvement on the targeted failure modes;
- no new authority, privacy, causal, arithmetic, or coverage failure;
- no material increase in irrelevant context or output burden;
- deterministic scripts and schemas still valid;
- a clean package with no client data, credentials, or evaluation leakage.

If a host regresses, first test whether the problem is instruction conflict, excess context, duplicated policy, tool mismatch, or output overproduction. Keep the router small and load references only for the current platform and decision.
