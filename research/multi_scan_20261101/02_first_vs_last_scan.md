# Report 2 — First vs last scan

| market | comparison | settled_pairs | line_changes_excluded | first_roi | last_roi | effect | ci95_low | ci95_high | p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AH | FIRST→LAST | 1053 | 366 | -0.0351 | -0.0349 | 0.0002 | -0.0023 | 0.0028 | 0.8691 |
| AH | 15:00→18:00 | 804 | 157 | -0.0215 | -0.0222 | -0.0007 | -0.0029 | 0.0016 | 0.5567 |
| AH | 18:00→21:00 | 533 | 126 | -0.0271 | -0.0277 | -0.0007 | -0.0036 | 0.0022 | 0.6452 |
| OU | FIRST→LAST | 1080 | 326 | -0.0503 | -0.0510 | -0.0007 | -0.0028 | 0.0013 | 0.4758 |
| OU | 15:00→18:00 | 823 | 129 | -0.0279 | -0.0288 | -0.0009 | -0.0026 | 0.0008 | 0.2944 |
| OU | 18:00→21:00 | 552 | 105 | -0.0472 | -0.0471 | 0.0001 | -0.0022 | 0.0025 | 0.9305 |

Price-only: first side held fixed, exact same line/book/provider, strictly later observation required. Includes actual valid prices outside core range to isolate pricing, unlike core-range independent benchmarks. Effect = later minus earlier unit return. First/last are within fixture Thai football day. A single observation is not evidence of multi-scan benefit.

[stage_metrics.csv](stage_metrics.csv) reports independent AH-favorite, fixed H/A, O/U selections, all settlement counts, WR, ROI, confidence intervals, odds and normalized price share. These simple controls have no validated predictive selection rule. Last pre-match selection is a retrospective endpoint; it is not necessarily actionable because one cannot know ex ante which later scan will fail.

WR counts resolved stake: (FW+0.5HW)/(FW+0.5HW+FL+0.5HL). Push stakes excluded from WR, included in ROI stake denominator; half wins are not full wins. Bootstrap resamples fixtures, not snapshots.


EXPLORATORY — NO PROVEN EDGE. ROI is units per unit staked (0.01 = 1%). CLV N/A; latest observed price is not a certified close. See [protocol](PROTOCOL.md), [input inventory](data_inventory.csv), [statistical tests with Holm adjustment](statistical_tests.csv). No frozen promotion gate changed.
