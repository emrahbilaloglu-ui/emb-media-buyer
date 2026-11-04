# Budget, pacing, and scaling

Treat budget as a constrained portfolio and marginal-economics decision. Delivery pace alone never establishes performance.

## Build the pacing basis

Record:

- account/entity, currency, time zone, flight start/end, current time, and budget type;
- approved total, daily, lifetime, shared, or portfolio budget and billing constraints;
- planned cumulative spend curve by day/hour, including weekday, seasonality, promotion, and launch shape;
- actual spend and any pending or delayed reporting;
- conversion and revenue lag;
- bid/target, schedule, audience, placement, policy, asset, feed, and inventory constraints;
- business outcome, unit economics, capacity, and risk limits.

Do not default to a linear curve when the plan is intentionally front-loaded, back-loaded, day-parted, seasonal, or learning-oriented. If no planned curve exists, a linear curve may be shown as an explicit assumption, not a truth.

## Pacing arithmetic

Use scripts/media_math.py for reproducible calculations.

- Elapsed fraction = elapsed flight time / total flight time.
- Expected cumulative spend = planned cumulative curve evaluated at current time.
- Pace ratio = actual cumulative spend / expected cumulative spend.
- Remaining budget = approved flight budget − actual cumulative spend.
- Required remaining average pace = remaining budget / remaining time.

Report units and sign conventions. A pace ratio above one means spend is ahead of the selected curve; it does not mean efficient. Below one means behind the curve; it does not mean bad.

## Diagnose underdelivery or overdelivery

Check in order:

1. reporting freshness, time zone, billing, and budget definition;
2. intentional schedule or planned curve;
3. eligibility, approvals, policy, asset/feed, destination, and account limits;
4. bid, target, cost cap, value target, budget, and optimization-event constraints;
5. audience/query/product/placement/geo availability and overlap;
6. auction and seasonality evidence;
7. measurement lag and business outcome quality;
8. capacity, stock, promotion, and landing/sales constraints.

Do not fix underdelivery by automatically loosening controls or adding budget. The constraint may be protecting marginal economics. Do not fix overdelivery by automatically reallocating; confirm the flight plan and outcome quality.

## Scaling eligibility

A scale proposal requires:

- an explicit acquisition unit and business target;
- reconciled or bounded business outcomes;
- contribution, cash/payback, capacity, and stock/operations constraints;
- evidence about marginal, not only average, performance;
- complete enough conversion/refund/sales lag;
- a scoped mechanism for why more spend can reach additional profitable demand;
- change size, staged alternative, monitoring cadence, cooldown, and rollback threshold;
- impact on active experiments and learning.

If marginal response is unknown, a staged test may be eligible; a confident full allocation shift is not.

## Choosing change size

There is no universal safe percentage. Derive size from financial downside, response-curve uncertainty, historical sensitivity to comparable changes, current platform/account constraints, expected outcome volume and lag, control preservation, campaign role, auction depth, audience size, and operational capacity.

Show current value, proposed value, absolute delta, percentage delta, daily and flight exposure, and the staged alternative. Do not hide a material money move inside an average portfolio percentage.

## Portfolio allocation

Allocate against expected marginal contribution and strategic constraints. Consider brand capture versus incremental prospecting, short-term contribution versus learning value, diversification, correlated risk, inventory, capacity, funnel coverage, sales-cycle lag, measurement quality, minimum coverage, maximum scalable demand, and downside under attribution error.

A high historical ROAS cell may be saturated, brand-heavy, retargeting-heavy, or unable to absorb more demand. A lower average ROAS cell may have better marginal headroom. State the mechanism and uncertainty.

As a formal benchmark, if total spend is fixed and each credible response function is smooth and concave, maximize total contribution subject to the budget and business constraints. At an interior optimum, funded unconstrained cells have equal expected marginal contribution per next currency unit; a cell at zero has no higher eligible marginal contribution. This is an analytical condition, not permission to trust a fitted curve. Priors, confounding, sparse spend ranges, S-shaped/non-concave response, minimums, capacity, risk, and strategic coverage can make the mathematical optimum unstable or commercially wrong. Show uncertainty and stage movement outside the observed range.

## Cut, continue, rotate, hold, and revert

Before either a cut or paid continuation, inspect tracking, lag, comparability, delivered binding, business evidence, relevant economics, strategic role, and the costs of stopping versus waiting. Poor attributed results are not an automatic kill; sparse outcomes are not an automatic KEEP. A reversible operational stop or rotation does not assert creative inferiority and need not await a formal power test or proof that siblings are better. Missing margin still limits profit/scale claims; it does not alone block an authorized, verified risk stop. Relevant identity, binding, technical, and authority gates remain mandatory.

- Use **hold** for the specific action/claim a material gate blocks; state actual delivery status separately.
- Use **monitor** when the configuration remains within business guardrails but needs a complete window.
- Use **test** when a controlled change can resolve the question.
- Use **revert** only when an approved/preregistered guardrail failed and rollback is authorized.
- Use **act** when evidence supports the type of change: economics for expansion/profit, or a sourced operational rationale for a reversible stop/rotation without those claims.

### Paid continuation at the existing review cadence

For a material KEEP/WATCH or hold that leaves paid delivery active, give a compact record:

- incremental spend and new outcomes since the previous review;
- last attributed and business outcome dates and spend since each, with separate source/window/lag qualifiers or explicit unknowns;
- current authorized operating context, actual pacing and plausible exposure until the next existing review, and opportunity cost;
- expected new information and why it justifies continuation now, including counterevidence and cost of stopping;
- next read, decision-changing condition, and recommendation if met. If renewed WATCH is chosen after a met trigger, explain the new basis.

If continuation lacks a defensible basis, recommend a scoped pause or rotation and expose any execution authority gap. Do not renew WATCH merely because the entity once purchased, has fresh carts, lacks a proven replacement, or has unknown margin. Fresh sales are real counterevidence, not automatic protection. Low-spend rows remain undecided unless other evidence supports a decision. Small connection/status queries do not need this paid-decision record.

### Allocation and financial consequence

State whether a change increases exposure, reduces it, rotates delivery within existing budgets, or continues it. Pausing one shared-budget ad can redirect delivery to siblings without reducing total spend; neither redirection, equal allocation, superior results, nor savings is guaranteed. Past spend is not recoverable cash. Check the incumbent and alternatives separately.

If the last eligible child is paused, inspect the resulting parent/slot status separately. A child pause does not itself authorize parent shutdown, budget reuse, replacement, or refill. Check whether existing explicit/standing authority already covers those exact actions; proceed within it without redundant approval, otherwise prepare the remaining decision. Verify native state rather than assuming the parent became PAUSED.

Apply an owner retention rule only to the actual promoted source/TEST bindings it covers. Promotion candidates and merely purchasing ads do not inherit MAIN-winner retention. Existing valid source mappings need no newly invented individual naming approval; later explicit stop instructions must be resolved against the current rule.

Budget multiplied by periods is a nominal arithmetic reference, not actual spend, expected delivery, or a hard cash ceiling. Account for partial days, pacing, platform spending flexibility, and shared budgets; show a forecast range only with supported assumptions. Unknown evergreen total exposure stays unknown. This review creates no per-ad lifetime budget, universal cash/day/CPA cap, scheduler, or automatic cut/scale/refill.

## Forecasts and scenarios

Forecasts must include baseline window and comparability, spend plan and response assumption, downside/base/upside outcome and contribution, lag, seasonality, capacity, cannibalization, uncertainty, switch points, triggers, and values extrapolated beyond observed history.

Do not multiply current average ROAS by a larger budget and call it a forecast. If no response curve is credible, use bounded scenarios and stage the decision.

## Monitoring contract

For each change, preregister:

- first technical read-back time;
- first delivery read;
- earliest complete outcome read based on lag;
- primary business metric and source;
- guardrails and anomaly checks;
- cooldown and forbidden edits;
- continue, hold, revert, or escalate rule;
- owner and communication channel.

Distinguish accepted by API, visible in account, delivering, outcome-measured, and commercially validated.
