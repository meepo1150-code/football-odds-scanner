# Report 4 — Pre-kickoff timing

| time_bin | market | raw_observations | unique_fixtures | bets | wr | roi | roi_ci95_low | roi_ci95_high | stake_share_calibration_error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T-2 | AH | 724 | 723 | 651 | 0.5157 | -0.0016 | -0.0728 | 0.0681 | 0.0184 |
| T-2 | OU | 724 | 723 | 671 | 0.4796 | -0.0685 | -0.1330 | 0.0005 | 0.0199 |
| T-1 | AH | 452 | 452 | 415 | 0.5075 | -0.0195 | -0.1053 | 0.0674 | 0.0284 |
| T-1 | OU | 452 | 452 | 421 | 0.5174 | -0.0029 | -0.0854 | 0.0795 | 0.0179 |
| T-3 | AH | 608 | 608 | 542 | 0.4905 | -0.0434 | -0.1191 | 0.0335 | 0.0084 |
| T-3 | OU | 608 | 608 | 542 | 0.5274 | 0.0143 | -0.0622 | 0.0935 | 0.0282 |
| T-9 | AH | 1145 | 1071 | 939 | 0.5093 | -0.0126 | -0.0698 | 0.0477 | 0.0233 |
| T-9 | OU | 1145 | 1071 | 948 | 0.5094 | -0.0152 | -0.0719 | 0.0399 | 0.0098 |
| T-12 | AH | 491 | 487 | 437 | 0.5369 | 0.0373 | -0.0485 | 0.1243 | 0.0379 |
| T-12 | OU | 491 | 487 | 440 | 0.5421 | 0.0400 | -0.0472 | 0.1246 | 0.0416 |
| T-18 | AH | 29 | 29 | 28 | 0.3962 | -0.2174 | -0.5602 | 0.1175 | 0.1036 |
| T-18 | OU | 29 | 29 | 27 | 0.4783 | -0.0567 | -0.4013 | 0.2735 | 0.1220 |
| T-6 | AH | 1190 | 1145 | 1013 | 0.4719 | -0.0768 | -0.1309 | -0.0194 | 0.0271 |
| T-6 | OU | 1190 | 1145 | 1025 | 0.5011 | -0.0309 | -0.0857 | 0.0232 | 0.0070 |
| T-4 | AH | 498 | 493 | 435 | 0.5477 | 0.0502 | -0.0313 | 0.1345 | 0.0476 |
| T-4 | OU | 498 | 493 | 446 | 0.5194 | -0.0017 | -0.0817 | 0.0832 | 0.0190 |

Bins are [lower,upper), e.g. exactly 1h belongs to T-2. Latest observed row per fixture/bin, no fabricated boundary price. Bet counts may be lower than unique fixtures due to missing markets, core range and FT. Each fixture may occur in several bins; inference below is paired, not independent observations.

| market | clusters | effect | ci95_low | ci95_high | p |
| --- | --- | --- | --- | --- | --- |
| AH | 528 | 0.0012 | -0.0024 | 0.0045 | 0.5112 |
| OU | 523 | -0.0033 | -0.0062 | -0.0005 | 0.0255 |

Matched 1–3h vs 6–12h controls exact fixture, league, selected side, bookmaker, provider, exact line and both prices within 1.80–2.20. Unmatched bin differences remain confounded by league/time/day; they must not be used to name an optimal window. Calibration is won-stake share vs two-sided de-vig price share, not full-win probability. No window declared optimal without forward confirmation. D uses preregistered T-3, not the best historical bin.


EXPLORATORY — NO PROVEN EDGE. ROI is units per unit staked (0.01 = 1%). CLV N/A; latest observed price is not a certified close. See [protocol](PROTOCOL.md), [input inventory](data_inventory.csv), [statistical tests with Holm adjustment](statistical_tests.csv). No frozen promotion gate changed.
