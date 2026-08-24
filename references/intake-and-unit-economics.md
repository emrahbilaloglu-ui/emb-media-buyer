# Intake and unit economics

Paid media is a capital-allocation problem constrained by measurement. Establish the commercial contract before optimizing platform metrics.

## Minimum decision intake

Recover or record:

- decision and deadline;
- business model, market, currency, account time zone, and tax basis;
- acquisition unit: order, new customer, qualified lead, opportunity, subscriber, install, activated user, or retained cohort;
- revenue recognition and refund/return/cancellation window;
- variable costs and capacity constraints;
- new versus returning treatment and lifetime-value horizon;
- cash/payback requirement and desired contribution or growth trade-off;
- primary source of business truth and owner;
- platform optimization event and its relationship to the business outcome;
- reporting, attribution, and conversion-lag windows.

If an input is unknown, do not substitute a public benchmark without asking or labeling it. Use a scenario range and show which input changes the decision.

## Use a consistent revenue basis

Define revenue before calculating any return metric. Possible bases include booked gross sales, net sales, collected cash, recognized revenue, or platform-attributed conversion value. Do not compare ratios built on different bases.

For commerce, avoid double counting. A practical expected contribution per order is:

expected net revenue
− product cost
− variable fulfillment and packaging
− merchant-funded shipping
− payment and marketplace fees
− expected returns, refunds, chargebacks, and cancellations not already netted from revenue
− other order-variable costs

Taxes collected and remitted for the buyer normally are not revenue; taxes borne by the advertiser are a cost. State the chosen treatment.

## Core calculations

Use scripts/media_math.py when the inputs are available.

### Commerce

- Contribution margin ratio = expected pre-ad contribution / expected net revenue.
- Break-even CPA = expected pre-ad contribution per acquired unit.
- Break-even ROAS = expected net revenue per unit / expected pre-ad contribution per unit, equivalent to 1 / contribution margin ratio when definitions align.
- Target CPA = pre-ad contribution per unit − desired post-ad contribution − risk reserve.
- Target ROAS = expected net revenue per unit / target CPA.
- MER = advertiser-owned revenue / total marketing spend. MER is blended efficiency, not incrementality.

For new-customer acquisition, use new-customer revenue and contribution if the decision is about new customers. Do not subsidize prospecting with returning-customer revenue unless the user explicitly chooses a blended objective.

### Lead generation

Expected pre-ad contribution per lead can be estimated as:

P(qualified | lead) × P(sale | qualified) × expected contribution per won sale
− variable qualification and sales cost per lead

Use observed stage transitions from the same source and cohort. Account for sales lag, duplicate/spam leads, no-shows, cancellations, and capacity. Platform cost per lead is not a business CPA.

### SaaS and B2B

Choose the acquisition unit explicitly. Useful measures include customer acquisition cost, sales-qualified opportunity cost, pipeline contribution, closed-won contribution, gross-margin LTV, payback period, and cohort retention.

- Gross-margin LTV must state horizon, retention/churn method, discounting if material, servicing costs, and source.
- Payback months = CAC / expected monthly gross contribution, only when the contribution stream is defined and sufficiently stable.
- Pipeline ROAS is a leading indicator, not realized revenue. Apply stage probabilities or report raw pipeline separately.

### Apps

Use cohort value on a defined horizon, net of platform fees, refunds, incentives, and variable servicing costs. Keep installs, activations, retained users, subscribers, and payers separate. MMP- or SKAdNetwork-attributed value is not automatically finance truth.

## Average versus marginal economics

Average CPA or ROAS describes the observed mix. A scale decision asks what the next unit of spend is expected to produce. Inspect response by time, market, audience, query, product, creative, and spend level where identifiable. Look for saturation and selection effects.

When a credible marginal response curve is unavailable:

- do not assume the average persists;
- stage the change;
- define a cooldown and complete conversion-lag window;
- preregister a rollback threshold based on contribution or another business constraint;
- preserve a control or comparable baseline where feasible.

## Scenario and sensitivity discipline

For uncertain inputs, report at least downside, base, and upside scenarios. Use ranges that come from business history or named assumptions. Identify the switch point: the value at which act becomes hold or revert.

Common sensitivity inputs include return/refund/cancellation rate, contribution margin, shipping subsidy, new-customer mix, repeat behavior, lead qualification/show/close/collection rates, retention/churn, gross-margin LTV, conversion lag, missing offline outcomes, stock, fulfillment, and sales-team capacity.

## Portfolio constraints

Before recommending allocation, document:

- minimum viable spend or coverage commitments;
- maximum capacity, inventory, geography, and policy constraints;
- brand, prospecting, retention, and experimentation roles;
- cash-flow and billing limits;
- dependency on one product, market, audience, or platform;
- downside if the attribution system is wrong.

Budget allocation is not a ranking of historical ROAS. It is a constrained decision over expected marginal contribution, uncertainty, learning value, and strategic coverage.

