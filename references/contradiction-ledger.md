# Contradiction ledger

Paid-media advice often conflicts because sources answer different questions, use different populations, or turn local heuristics into rules. Preserve the disagreement and route it to the correct decision test.

## Platform learning thresholds

**Conflict:** official platform guidance and practitioner content cite different event counts, budgets, and time windows for delivery learning.

**Resolution:** these are platform/product/account/time-specific delivery signals, not business sufficiency or cross-platform policy. Verify current account state and official eligibility. Use account-relevant variance, practical effect, lag, and a named method for decision sufficiency.

## Automation versus manual control

**Conflict:** platform engineering/product material emphasizes automated audience, bidding, budget, placement, feed, and creative systems; operators report cases where controls/segmentation matter.

**Resolution:** automation expands candidate selection; it does not erase distinct economics, policy, market, capacity, offer, or measurement constraints. Read the exact controls and delivered mix. Consolidate only cells that share decision targets and governance; segment when differences are material and the evidence cost of fragmentation is acceptable.

## Attribution versus incrementality

**Conflict:** platform dashboards allocate conversions/revenue to ads, while field experiments and measurement research show observational attribution can over- or under-credit effects.

**Resolution:** keep platform-attributed, advertiser-owned, and incremental ledgers separate. Attribution can support in-platform operation; business reconciliation supports economics; a credible counterfactual supports causation.

## Randomized test versus divergent delivery

**Conflict:** an A/B test randomizes assignment, but auction/optimization systems can deliver different spend, impressions, placements, audience composition, products, or asset combinations across arms.

**Resolution:** randomization strengthens the scoped comparison but does not make delivery artifacts disappear. Preregister treatment, inspect per-arm delivery/compliance, report divergence, and limit transport. If the platform varies the thing the test claims to hold constant, the intended estimand may be unavailable.

## Creative volume versus creative diversity

**Conflict:** creator workflows prescribe many ads/hooks/variants; official and practitioner evidence also emphasizes distinct concepts/customer motivations.

**Resolution:** track concept, audience/job, angle, proof, offer, narrative, hook, format, creator, and execution separately. Cosmetic variants can support export or a surface test but do not count as independent concepts. Derive volume from production capacity, outcome density, test design, and portfolio coverage.

## Attention metrics versus business performance

**Conflict:** high CTR, hook/hold rate, engagement, or low CPC can coexist with weak landing continuity, lead quality, purchase conversion, refunds, or contribution.

**Resolution:** use attention metrics to locate the funnel break. Judge commercial value on advertiser-owned qualified outcomes and economics. Verify that the creative promise matches the destination.

## Highest spend versus winner

**Conflict:** the platform spends more on an entity it predicts will perform, then reporting treats the high-spend entity as evidence of superiority.

**Resolution:** allocation is endogenous. Report concentration and comparable outcome counts; use a randomized design for a directional choice and lift/geo designs for incremental claims.

## Frequency or age versus fatigue

**Conflict:** public rules attach fatigue to a frequency, impression count, or age; real declines can come from audience, mix, auction, offer, destination, stock, tracking, calendar, or regression.

**Resolution:** treat fatigue as competing hypotheses. Derive account-specific patterns only from verified asset lineage, comparable delivery, downstream outcomes, and enough history.

## Linear pacing versus business-optimal pacing

**Conflict:** open automation examples compare actual spend with a linear daily curve and auto-reallocate; flights may be intentionally front/back-loaded and underdelivery may reflect economically protective bid/target constraints.

**Resolution:** pace against the approved cumulative curve. Diagnose constraints and outcome quality before changing delivery. Never infer efficiency or auto-authorize a transfer from pace alone.

## Average ROAS versus scale

**Conflict:** common playbooks scale a cell after average ROAS clears a threshold; response curves normally saturate and observed mix changes with spend.

**Resolution:** base scale on expected marginal contribution, uncertainty, cash, capacity, lag, and a staged downside. Average ROAS is historical description. Do not extrapolate it linearly.

## Paid search/PMax efficiency versus demand creation

**Conflict:** Search, Shopping, and PMax can report strong attributed results while capturing branded, organic, returning, or already-intended demand.

**Resolution:** inspect query/brand/product/channel/customer mix and total business outcomes. Use experiments or credible causal models for incremental claims. A before/after lift without a counterfactual remains observational.

## MMM output versus “ground truth”

**Conflict:** open MMM packages can return precise response curves and allocation suggestions from the same data while using different priors, controls, transformations, and optimization.

**Resolution:** compare estimands and assumptions, inspect identifiability, collinearity, fit, holdouts/backtests, posterior/interval uncertainty, sensitivity, calibration experiments, and observed spend range. Do not average incompatible model outputs.

## Server-side tracking versus privacy

**Conflict:** technical content presents server events and advanced matching as measurement recovery; legal/privacy obligations still apply.

**Resolution:** server-side transport does not bypass consent, notice, purpose, minimization, retention, or platform policy. Verify current market requirements and actual consent/event behavior.

## “Privacy Sandbox retired” versus feature-level reality

**Conflict:** summaries may say Google retired Privacy Sandbox, while Google’s current feature-status page shows a mixed state.

**Resolution:** many advertising technologies—including Attribution Reporting, Protected Audience, Topics, and related components—are being deprecated or removed, while CHIPS, FedCM, Private State Tokens, storage/network partitioning, and other features remain supported. Name and verify the exact technology, platform, and removal status; do not turn a portfolio of features into one binary claim.

## API success versus applied change

**Conflict:** mutation responses and automation frameworks treat a successful request as completion; platforms may normalize, reject partially, queue, or apply to a shared/dependent resource.

**Resolution:** separate validated, accepted, applied, delivering, outcome-measured, and commercially validated states. Use a fresh independent read-back and report partial failures.

## Partial failure versus atomic safety

**Conflict:** API examples enable partial failure or batching to improve throughput, while an operator may need a dependent change set to land as one unit.

**Resolution:** model the dependency graph first. Use atomic/all-or-nothing semantics where current platform contracts support them and the operations must stand together. Use partial failure only for genuinely independent edits, map every result to its operation, freeze on mixed state, and obtain approval before compensating. Batch transport is not evidence of atomicity.

## Agent autonomy versus financial safety

**Conflict:** reference agents may auto-approve “minor” changes or auto-rebalance pacing; the user may not have authorized any live mutation.

**Resolution:** internal severity is not authority. Every live spend/delivery mutation requires exact user approval, bounded target/field/exposure, preflight, read-back, and rollback. Analysis and preparation remain read-only.

## How to use this ledger

When a recommendation resembles one side of a conflict:

1. identify which question each source answered;
2. align population, market, account, outcome, attribution, period, and release date;
3. rank source quality and preserve vendor/practitioner incentives;
4. choose the evidence standard required by the business decision;
5. label unresolved claims and design the cheapest discriminator;
6. verify volatile platform facts at runtime before action.
