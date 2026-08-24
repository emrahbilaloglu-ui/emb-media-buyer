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

## Cut, hold, and revert

Do not turn poor attributed performance into an automatic kill. Before a cut, inspect tracking, lag, comparability, creative/destination binding, business reconciliation, marginal economics, strategic role, and cost of losing learning.

- Use **hold** when a material gate is unresolved.
- Use **monitor** when the configuration remains within business guardrails but needs a complete window.
- Use **test** when a controlled change can resolve the question.
- Use **revert** only when an approved/preregistered guardrail failed and rollback is authorized.
- Use **act** when the economic and evidential contract supports the change.

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
