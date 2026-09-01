# Research source ledger

Reviewed for this skill on 2026-08-23 and extended with the TikTok Agentic Hub/MCP review on 2026-09-01. This is a broad, curated research snapshot—not an exhaustive copy of the open web. Runtime facts must be refreshed through references/runtime-source-registry.md. No third-party source text or code is vendored into this skill; sources informed principles, checks, anti-patterns, and implementation design.

## Current official platform sources

### Meta

- [Meta Andromeda: supercharging Advantage+ automation with a next-gen ads retrieval engine](https://engineering.fb.com/2024/12/02/production-engineering/meta-andromeda-advantage-automation-next-gen-personalized-ads-retrieval-engine/) — first-party engineering context for large-scale candidate retrieval and creative diversity. Reported uplifts are Meta case results, not universal account forecasts.
- [Meta Adaptive Ranking Model](https://engineering.fb.com/2026/03/31/ml-applications/meta-adaptive-ranking-model-bending-the-inference-scaling-curve-to-serve-llm-scale-models-for-ads/) — first-party ranking-system context; does not establish a universal campaign structure.
- [Generative AI transparency in Meta ads products](https://about.fb.com/news/2025/02/gen-ai-transparency-metas-ads-products/) — current first-party disclosure/label context; verify market and product behavior at export/runtime.
- [Agents Rule of Two: a practical approach to AI agent security](https://ai.meta.com/blog/practical-ai-agent-security/) — first-party defense-in-depth framework separating untrusted inputs, sensitive access, and state change/external communication; not a substitute for least privilege or human/tool-layer controls.
- [Meta Blueprint: Conversion Lift](https://www.facebookblueprint.com/student/page/674272) — official training context for incrementality and current product routing; confirm account eligibility.
- [Meta Business Help Center](https://www.facebook.com/business/help) and [Marketing API documentation](https://developers.facebook.com/docs/marketing-apis/) — runtime sources for configuration, reporting, policy, and API semantics.

### Google

- [About lift studies](https://support.google.com/google-ads/answer/16104408?hl=en) — official measurement overview and current product availability.
- [User-based Conversion Lift](https://support.google.com/google-ads/answer/12005564?hl=en) — feasibility, power, eligibility, confidence, and conversion-lag considerations; verify the account.
- [Performance Max experiments](https://support.google.com/google-ads/answer/12997711?hl=en) — current PMax experiment routes; results are scoped to the test.
- [Geo lift studies and incremental ROAS](https://support.google.com/google-ads/answer/14102986?hl=en) — official geo-test interpretation including uncertainty; align outcome and spend definitions.
- [Google Ads experiments](https://support.google.com/google-ads/answer/7281575?hl=en) — hypothesis and variable-isolation guidance; current UI/eligibility can change.
- [Google Ads API Change Events](https://developers.google.com/google-ads/api/docs/change-event?hl=en) — first-party audit support for reconstructing before/after state.
- [Google Ads API partial failures](https://developers.google.com/google-ads/api/docs/best-practices/partial-failures), [mutating resources](https://developers.google.com/google-ads/api/docs/mutating/overview), and [batch processing](https://developers.google.com/google-ads/api/docs/batch-processing/overview) — method-level execution contracts. Partial failure and batch throughput are not atomic safety; validate and read back exact state.
- [Changes to target-based bid strategies](https://support.google.com/google-ads/answer/17061251) and [official FAQ](https://support.google.com/google-ads/answer/17125145?hl=en) — global rollout began 2026-08-17 for target-based campaigns that are Limited by budget. Use as a dated transition confound; verify account rollout and business economics rather than treating Google’s scale guidance as proof.
- [Consent mode concepts](https://developers.google.com/tag-platform/security/concepts/consent-mode?hl=en) — basic/advanced consent behavior and consent states; implementation is not legal advice.
- [About modeled conversions](https://support.google.com/google-ads/answer/10081327?hl=en) — modeled and observed outcomes can be reported together and modeled conversions can take up to five days to stabilize; apply only when relevant and include account-specific conversion/import lag.
- [Privacy Sandbox feature status](https://privacysandbox.google.com/overview/status) and [technology plan update](https://privacysandbox.google.com/blog/update-on-plans-for-privacy-sandbox-technologies) — as of the 2026-08-14 status page, many advertising APIs are being deprecated/removed while several privacy/security technologies remain supported. Reject the overbroad claim that the whole initiative is uniformly retired.
- [Google Ads Help](https://support.google.com/google-ads/) and [Google Ads API](https://developers.google.com/google-ads/api/) — runtime sources for fields, campaign types, attribution, bidding, and reporting.

### TikTok

- [TikTok Ads learning phase](https://ads.tiktok.com/resources/help/article/learning-phase) — official, volatile delivery guidance; never freeze its current thresholds into skill policy.
- [Updates to Smart+](https://ads.tiktok.com/resources/help/article/about-updates-to-smart-plus) — current unified Smart+ workflow and controls; terminology may change again.
- [TikTok event deduplication](https://ads.tiktok.com/help/article/event-deduplication?redirected=2) — official event-id and client/server deduplication guidance.
- [TikTok measurement products](https://ads.tiktok.com/business/en/products/measurement) — attribution, split-test, and lift product context; verify market/account eligibility.
- [TikTok Business API documentation](https://business-api.tiktok.com/portal/docs) — runtime source for fields, reporting, and mutations.
- [TikTok for Business MCP Server](https://ads.tiktok.com/resources/help/article/about-tiktok-for-business-mcp-server) — official August 2026 overview of full versus progressive disclosure, campaign/reporting/audience/creative capability families, and automatic capability growth. It does not grant live-change authority or prove an agent's recommendations.
- [TikTok for Business Agentic Hub](https://ads.tiktok.com/resources/help/article/about-tiktok-for-business-agentic-hub) and [catalogue](https://ads.tiktok.com/apps_and_agents/agentic-hub) — official discovery layer. The 55-card snapshot reviewed on 2026-09-01 is classified in `assets/research/tiktok-agentic-hub-55.json`; card claims are product descriptions, not verified performance evidence.
- [About attribution for GMV Max](https://ads.tiktok.com/resources/help/article/about-attribution-for-gmv-max?lang=en) — current official scope says Product and LIVE GMV Max can attribute paid and organic orders while active. Use dedicated reporting and never equate the attributed total with paid-media incrementality.
- [GMV Max guidelines](https://ads.tiktok.com/help/article/gmv-max-guidelines?lang=en) — current primary-ad-account/shop and campaign interaction constraints; verify the actual shop and account before action.
- Connected TikTok MCP discovery snapshot, retrieved 2026-09-01 — progressive disclosure exposed 40 native aliases and `tool_list` returned 379 dispatcher tools across 48 groups. Selected schemas confirmed separate regular, Smart+, GMV Max, benchmark, diagnostic, changelog, lead, app, catalog, split-test, automated-rule, and R&F surfaces. Counts and schemas are volatile and must be rediscovered.

### Other channels and standards

- [Apple Ads campaign dashboard metrics](https://ads.apple.com/app-store/help/reporting/0024-view-campaigns-dashboard-metrics) — official metric definitions; connect installs to retained cohort value.
- [Amazon Ads display guide](https://advertising.amazon.com/library/guides/display-ads-guide) and [Amazon marketing mix models](https://advertising.amazon.com/measurement-analytics/marketing-mix-models) — first-party product/measurement context; vendor claims need independent validation.
- [Pinterest Ads Manager guide](https://business.pinterest.com/en-us/getting-started-in-ads-manager/) — official setup/reporting orientation; verify current controls.
- [Snapchat MMM guidance](https://forbusiness.snapchat.com/blog/how-to-use-mmms) — first-party vendor guidance; use alongside transparent modeling diagnostics.
- [Reddit Conversions API](https://business.reddithelp.com/articles/Knowledge/Conversions-API) and [Reddit web attribution](https://business.reddithelp.com/articles/Knowledge/Web-Attribution-Overview) — official instrumentation and attribution definitions.
- [IAB Measurement Center](https://www.iab.com/organizations/measurement-center/) — industry measurement standards and guidance.
- [IAB incremental measurement guidelines for commerce media](https://www.iab.com/guidelines/guidelines-for-incremental-measurement-in-commerce-media/) — industry framework for incrementality; inspect disclosed assumptions and participating interests.
- [IAB Tech Lab standards](https://iabtechlab.com/standards/) — current programmatic specifications, privacy, supply-chain, and agentic-advertising standards.

## Academic and primary methods

- [Measuring ad effectiveness using geo experiments](https://research.google/pubs/measuring-ad-effectiveness-using-geo-experiments/) — randomized market-level causal design foundations.
- [Robust causal inference for incremental return on ad spend with randomized paired geo experiments](https://research.google/pubs/robust-causal-inference-for-incremental-return-on-ad-spend-with-randomized-paired-geo-experiments/) — paired-geo iROAS methods and robustness.
- [A time-based regression matched-markets approach for designing geo experiments](https://research.google/pubs/a-time-based-regression-matched-markets-approach-for-designing-geo-experiments/) — market selection/design methodology; validate pre-fit and interference.
- [Inferring causal impact using Bayesian structural time-series models](https://research.google/pubs/inferring-causal-impact-using-bayesian-structural-time-series-models/) — counterfactual time-series method with model assumptions.
- [Bias correction for paid search in media mix modeling](https://research.google/pubs/bias-correction-for-paid-search-in-media-mix-modeling/) — addresses demand confounding in paid-search MMM.
- [Measuring the effects of advertising: the digital frontier](https://www.nber.org/system/files/working_papers/w19520/w19520.pdf) — Lewis, Rao, and Reiley on low power and observational bias in advertising measurement.
- [Where A/B Testing Goes Wrong: How Divergent Delivery Affects What Online Experiments Cannot (and Can) Tell You](https://journals.sagepub.com/doi/10.1177/00222429241275886) — peer-reviewed Journal of Marketing evidence that randomized eligibility can still yield different optimized exposure mixes, confounding pure creative-effect interpretation.
- [Characterizing and Minimizing Divergent Delivery in Meta Advertising Experiments](https://arxiv.org/abs/2508.21251) — large-scale working paper contrasting Lift and A/B delivery patterns; inspect author/platform affiliations and design before transport.
- [Algorithm or Creative? A Three-Arm Experimental Design](https://arxiv.org/abs/2605.23706) — 2026 preprint proposing separation of creative and algorithmic channels; promising method evidence, not settled platform policy.
- [Budget pacing for targeted online advertisements at LinkedIn](https://doi.org/10.1145/2623330.2623366) — production pacing/control research; not an account-specific action threshold.
- [Optimal real-time bidding and pacing for ads](https://arxiv.org/abs/2503.06942) — recent pacing/control research; treat as a method input subject to review.
- [A comparison of budget pacing heuristics](https://www.sciencedirect.com/science/article/pii/S0167811625000850) — open research on pacing policies; operational applicability depends on objective and constraints.

## Open-source measurement and platform tooling

Repository metadata and licenses were checked on 2026-08-23. Recheck before reuse.

- [google/meridian](https://github.com/google/meridian) — Apache-2.0 Bayesian MMM; inspect data sufficiency, priors, calibration, diagnostics, and extrapolation.
- [facebookexperimental/Robyn](https://github.com/facebookexperimental/Robyn) — MIT MMM; optimization output does not remove identification or calibration risk.
- [pymc-labs/pymc-marketing](https://github.com/pymc-labs/pymc-marketing) — Apache-2.0 Bayesian marketing analytics/MMM components.
- [facebookincubator/GeoLift](https://github.com/facebookincubator/GeoLift) — MIT geo experimentation; validate market design, spillover, power, and outcome quality.
- [google/matched_markets](https://github.com/google/matched_markets) — Apache-2.0 geo-test design tooling.
- [google/CausalImpact](https://github.com/google/CausalImpact) — Apache-2.0 causal time-series implementation; assumptions and controls govern validity.
- [google/trimmed_match](https://github.com/google/trimmed_match) — Apache-2.0 paired-geo estimator; older maintenance state requires caution.
- [google/lightweight_mmm](https://github.com/google/lightweight_mmm) — archived; prefer the project’s Meridian migration guidance for new work.
- [googleads/google-ads-mcp](https://github.com/googleads/google-ads-mcp) — Apache-2.0 account-access/tooling patterns; tool capability is not write authority.
- [googleads/google-ads-python](https://github.com/googleads/google-ads-python) — official Apache-2.0 client library; current API docs remain authoritative.
- [tiktok/tiktok-business-api-sdk](https://github.com/tiktok/tiktok-business-api-sdk) — MIT official SDK; verify API version and account permissions.
- [IABTechLab/AAMP](https://github.com/IABTechLab/AAMP) — Apache-2.0 agentic advertising standards work.
- [IABTechLab/buyer-agent](https://github.com/IABTechLab/buyer-agent) — Apache-2.0 reference buyer-agent and change-request state patterns. Its automation defaults are examples, not safe universal policy; this skill requires explicit live-change approval.

## Open agent/skill repositories reviewed as patterns and anti-patterns

- [nowork-studio/notfair-plugin](https://github.com/nowork-studio/notfair-plugin) — MIT operating-contract patterns: metric qualifiers, source/window/currency/attribution adjacency, validate-before-write, exact current/proposed state, approval, fresh read-back, and rollback.
- [Synter-Media-AI/free-skills](https://github.com/Synter-Media-AI/free-skills) — useful taxonomy examples but includes universal kill/scale/fatigue thresholds. Those numbers were explicitly rejected as policy.
- [gomarble-ai/gomarble-ai-paid-media-claude-skills](https://github.com/gomarble-ai/gomarble-ai-paid-media-claude-skills) — workflow research only; restrictive/non-standard licensing observed, so no text or code was copied.
- [rghrmkr1993/ad-campaign-skills](https://github.com/rghrmkr1993/ad-campaign-skills), [Hainrixz/claude-ads](https://github.com/Hainrixz/claude-ads), and [Pauesome/Paid-Media-MCP](https://github.com/Pauesome/Paid-Media-MCP) — community workflow/coverage references, not factual authorities.
- [facebook/facebook-python-business-sdk](https://github.com/facebook/facebook-python-business-sdk) — official SDK repository with non-SPDX/custom licensing context; not treated as permissively open-source code for this skill.

## YouTube and practitioner evidence

Subtitles/transcripts or video metadata were inspected where available. These sources informed hypotheses and operator vocabulary; none supplies a universal threshold. Paraphrase rather than copying scripts.

- [Meta for Business: Unlock better performance by diversifying creative](https://www.youtube.com/watch?v=NGIKjtQTcLM) — official practitioner training: diversify concepts/customer motivations, then adapt formats and placements.
- [Google Ads: Performance Max uplift experiments](https://www.youtube.com/watch?v=Jkkp2l00TEs) — official product demonstration; verify current experiment setup and do not generalize case uplift.
- [Google Ads: Marketing mix modeling](https://www.youtube.com/watch?v=Xnq_q_b5l8U) — official MMM orientation; use transparent diagnostics and experiments for calibration.
- [TikTok for Business: Smart+](https://www.youtube.com/watch?v=0sW69rn9wlk) — official product positioning; current help/account state outranks the video.
- [MeasureSchool: consent mode implementation](https://www.youtube.com/watch?v=In4TNHLTz_Y) — technical workflow hypothesis: audit consent state and actual cookies/events; not legal advice.
- [Recast: incrementality testing](https://www.youtube.com/watch?v=XhMbeN7cH34) — practitioner/vendor explanation of counterfactuals, geo tests, and attribution overclaim; confirm methodology with primary research.
- [Dara Denney: testing Facebook ad creatives at different budgets](https://www.youtube.com/watch?v=7knQyPYLmfo) — practitioner testing architecture; fixed ad counts, spend, or durations remain heuristics.
- [Professor Charley T: Meta creative testing](https://www.youtube.com/watch?v=8lQO5RO-tuY) — practitioner concept/testing ideas; validate against actual account evidence.
- [Foxwell Digital interview on creative strategy](https://www.youtube.com/watch?v=qUw6NIZfMYc) — practitioner evidence for the creative strategist/media buyer/merchandising feedback loop.
- [Savannah Sanchez and Motion: hooks and creative strategy](https://www.youtube.com/watch?v=76KH-GZZ5w4) — practitioner taxonomy and production research; trends/hooks are time-bound hypotheses.

## Rejected universal rules

The research repeatedly surfaced fixed rules such as a required conversion count per week, a universal number of creatives, a fixed test duration, CTR/hook-rate cutoffs, “three times CPA” kill rules, fixed daily scale percentages, impression-based fatigue limits, and linear pacing alarms.

These are not encoded as policy. A number is actionable only when it comes from business economics, comparable account history, a named power/design method, or current verified platform/account requirements. Otherwise it remains a labeled practitioner heuristic.
