# Report 6 — Final recommendation

**NO PROVEN EDGE. Keep production schedule unchanged; evaluate 15:00→18:00 in shadow mode.**

1. Multi-scan selection quality: not established. Multiple scans create price/movement evidence, but retrospective pricing gains are not incremental forecasting skill.
2. Movement predictive value: inspect setup_decision_models.json and initial_controlled_models.json, with corrected tests in statistical_tests.csv. Small split sizes or unconfirmed test improvements cannot pass frozen gates. No causation claimed.
3. First vs last: exact matched effects and CI in Report 2; line changes excluded from price-only comparison. WR alone cannot show better prices.
4. Best pre-kickoff hour: not established; matched result in Report 4. Unmatched high-ROI bins cannot justify schedule changes.
5. Reducing to 15/18: loses later coverage, late price information and all pre-18 final decisions. Actual primary pair coverage: 1066 fixture pairs versus 1837 union fixtures. See kickoff bands and missed core-range opportunities, not just snapshot counts.
6. Setup→decision sufficient for real betting: not proven. Existing frozen registry has zero approved patterns. Neither retrospective positive ROI nor model predicted return authorizes betting selection.
7. Two, three or many: retain current scans while running offline shadow. Benefit: retains evidence and a paired counterfactual. Cost: current API usage continues. Risk: provider/scope drift and missing FT can invalidate forward comparisons. Three rounds may preserve more coverage than two, but there is no established betting-performance superiority.
8. If forced to two: 15/18 is an operational candidate, not statistically best. Coverage-only alternatives are in two_slot_coverage_candidates.csv; later scans may fit night matches but lose early opportunities. Do not select a winner from these data and call its evidence confirmatory.

## Forward validation plan

Freeze the current protocol, feature sets and trained rule version before new outcomes. Retain all production rounds; evaluate B at ACTUAL decision time, no fallback from 21/00. Log eligible fixture universe, unavailable markets, active status, observed time, immutable provider IDs, actual requests and complete 90-minute FT. Paired ROI CI and coverage loss are co-primary. Require B−A lower one-sided 95% CI >−2pp, coverage loss <=5pp, missed validated opportunities <=5%, savings >=25%, in addition to all existing gates. A non-significant difference does not prove noninferiority.

Fresh prospective sample required (all historical rows have been inspected):

| market | paired_sd | additional_future_pairs_for_80pct_power |
| --- | --- | --- |
| AH | 0.2286 | 809 |
| OU | 0.0761 | 90 |

These are paired return-difference variance-based planning estimates, not independent snapshot counts. Use max(AH,OU,150+80+40) future settled matched fixtures, >=60 football days, >=8 weeks and >=3 leagues. Increase for within-day clustering, serial dependence, multiple co-primary claims and attrition; reassess sample size without inspecting effect direction. ROI-difference planning is not power for nonlinear movement models; they need a separate simulation/power assessment before promotion. Freeze a future holdout before collection and reserve it until the analysis decision date. If current production approved patterns remain empty, validated real-bet performance comparison is unavailable, regardless of benchmark sample.

## Reproduction and evidence boundaries

Run `python research/multi_scan_20261101/run.py` from the pinned repository with research requirements. It writes only this research directory and performs zero network calls. Input inventory pins every versioned data/cache file. Master observations and settlements are derived, never replacements for production data. Six reports, detailed CSVs, model predictions and tests allow every reported calculation to be traced back to a source file and row. Future executions on newer data are a new exploratory analysis unless holdout restrictions are enforced separately.

Historical tick files are audited but not pooled into live-schedule inference. Existing normalized scan history is used; an audit of every unretained Actions artifact or independent verification of every cached result is outside available evidence. Genuine CLV and execution freshness remain unavailable; report N/A, never substitute the last scan and call it closing.

## Numerical decision evidence

| market | comparison | settled_pairs | effect | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| AH | FIRST→LAST | 1053 | 0.0002 | -0.0023 | 0.0028 |
| AH | 15:00→18:00 | 804 | -0.0007 | -0.0029 | 0.0016 |
| AH | 18:00→21:00 | 533 | -0.0007 | -0.0036 | 0.0022 |
| OU | FIRST→LAST | 1080 | -0.0007 | -0.0028 | 0.0013 |
| OU | 15:00→18:00 | 823 | -0.0009 | -0.0026 | 0.0008 |
| OU | 18:00→21:00 | 552 | 0.0001 | -0.0022 | 0.0025 |

| strategy | market | snapshot_fixtures | bets | wr | roi | roi_ci95_low | roi_ci95_high |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | AH | 1559 | 1352 | 0.5063 | -0.0195 | -0.0665 | 0.0293 |
| A | OU | 1559 | 1379 | 0.5022 | -0.0311 | -0.0788 | 0.0136 |
| B | AH | 1185 | 1004 | 0.4969 | -0.0340 | -0.0881 | 0.0191 |
| B | OU | 1185 | 1023 | 0.5072 | -0.0215 | -0.0758 | 0.0333 |
| C | AH | 1540 | 1337 | 0.5043 | -0.0223 | -0.0676 | 0.0264 |
| C | OU | 1540 | 1361 | 0.5025 | -0.0303 | -0.0771 | 0.0159 |
| D_T3 | AH | 1629 | 1433 | 0.4917 | -0.0425 | -0.0923 | 0.0020 |
| D_T3 | OU | 1629 | 1456 | 0.5017 | -0.0303 | -0.0768 | 0.0167 |

The current-era sensitivity is crucial: since 2026-10-21, compare A/B/C on the same observed fixture union in current_era_sensitivity.csv. Missing historical schedules must not be mistaken for present-system reliability. Model test dates are only three football days (29–31 October), including incomplete FT at extraction; selected-bet samples are very small. Positive or negative selected ROI is not reliable proof. This dataset cannot establish global or multi-season stability.


EXPLORATORY — NO PROVEN EDGE. ROI is units per unit staked (0.01 = 1%). CLV N/A; latest observed price is not a certified close. See [protocol](PROTOCOL.md), [input inventory](data_inventory.csv), [statistical tests with Holm adjustment](statistical_tests.csv). No frozen promotion gate changed.
