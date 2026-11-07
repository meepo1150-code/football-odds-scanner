# Report 3 — Odds movement impact

| market | category | fixtures | wr | roi | roi_ci95_low | roi_ci95_high | roi_lift_descriptive | mean_goal_difference | mean_total_goals |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AH | CONTINUOUS | 393 | 0.5141 | -0.0076 | -0.0970 | 0.0796 | 0.0330 | 0.1756 | 3.1069 |
| AH | LINE_DOWN_0.25 | 189 | 0.4742 | -0.0477 | -0.1734 | 0.0788 | -0.0072 | 0.4815 | 3.2328 |
| AH | LINE_DOWN_0.50_PLUS | 11 | 0.4000 | -0.1966 | -0.6818 | 0.3555 | -0.1561 | 0.9091 | 3.4545 |
| AH | LINE_UP_0.25 | 126 | 0.4952 | -0.0668 | -0.2131 | 0.0787 | -0.0263 | 0.2857 | 3.0794 |
| AH | LINE_UP_0.50_PLUS | 6 | 0.5556 | 0.0212 | -0.5948 | 0.6188 | 0.0618 | 0.0000 | 4.3333 |
| AH | REVERSAL | 226 | 0.5392 | 0.0423 | -0.0714 | 0.1594 | 0.0829 | 0.4027 | 3.3053 |
| AH | SAME_LINE_PRICE_DOWN | 389 | 0.5130 | -0.0154 | -0.1044 | 0.0726 | 0.0252 | 0.3393 | 3.0231 |
| AH | SAME_LINE_PRICE_UP | 407 | 0.5048 | -0.0113 | -0.0978 | 0.0740 | 0.0293 | 0.1622 | 3.0270 |
| AH | STABLE | 257 | 0.4621 | -0.1017 | -0.2061 | 0.0094 | -0.0611 | 0.2763 | 2.8911 |
| OU | CONTINUOUS | 384 | 0.4703 | -0.0821 | -0.1754 | 0.0043 | -0.0573 | 0.2891 | 2.9453 |
| OU | LINE_DOWN_0.25 | 130 | 0.5354 | 0.0021 | -0.1451 | 0.1467 | 0.0268 | 0.2000 | 3.1538 |
| OU | LINE_DOWN_0.50_PLUS | 3 | 0.6667 | 0.2313 | -1.0000 | 0.8470 | 0.2561 | 0.0000 | 2.6667 |
| OU | LINE_UP_0.25 | 168 | 0.5710 | 0.1183 | -0.0150 | 0.2566 | 0.1431 | 0.4940 | 3.4702 |
| OU | LINE_UP_0.50_PLUS | 4 | 0.5000 | 0.0025 | -1.0000 | 1.0050 | 0.0273 | 1.5000 | 3.0000 |
| OU | REVERSAL | 178 | 0.5492 | 0.0526 | -0.0785 | 0.1789 | 0.0773 | 0.3539 | 3.2865 |
| OU | SAME_LINE_PRICE_DOWN | 342 | 0.4983 | -0.0468 | -0.1396 | 0.0497 | -0.0220 | 0.5000 | 3.0380 |
| OU | SAME_LINE_PRICE_UP | 354 | 0.4976 | -0.0282 | -0.1252 | 0.0658 | -0.0035 | 0.1582 | 2.8927 |
| OU | STABLE | 384 | 0.4776 | -0.0759 | -0.1655 | 0.0128 | -0.0511 | 0.1667 | 2.9635 |

Category ROI lift is a descriptive difference against all movement fixtures, not a controlled causal effect. Fixed first favorite side for AH; Over for OU. Signed handicap is from that selected side. Reversal requires both directions of >0.01 price changes on the same line; continuous movement requires >=3 observations on one line. These diagnostics overlap categories and are not independent tests.

| market | model | train | validation | test | MSE | bets | wr | roi | roi_ci95_low | roi_ci95_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AH | A | 625 | 92 | 177 | 0.8261 | 7 | 0.3636 | -0.2183 | -0.7857 | 0.4206 |
| AH | A_BROADER | 625 | 92 | 178 | 0.8263 | 7 | 0.3636 | -0.2183 | -0.7857 | 0.4206 |
| AH | B | 625 | 92 | 177 | 0.8267 | 17 | 0.4828 | -0.0338 | -0.4664 | 0.3849 |
| AH | C | 625 | 92 | 177 | 0.8355 | 11 | 0.2105 | -0.4864 | -0.9091 | -0.0073 |
| OU | A | 635 | 88 | 185 | 0.8135 | 67 | 0.4872 | -0.0507 | -0.2650 | 0.1530 |
| OU | A_BROADER | 635 | 88 | 186 | 0.8154 | 68 | 0.4790 | -0.0647 | -0.2744 | 0.1426 |
| OU | B | 635 | 88 | 185 | 0.8136 | 66 | 0.5043 | -0.0217 | -0.2380 | 0.1935 |
| OU | C | 635 | 88 | 185 | 0.8148 | 64 | 0.4865 | -0.0509 | -0.2554 | 0.1712 |

A=18 alone; B=18 plus 15→18 movement; C=18 plus all available earlier same-day observations. Same complete-case test population for all three.

initial_controlled_models.json provides chronological ridge comparisons conditioning on INITIAL price/line/share, league, kickoff distance, then movement. setup_decision_models.json conditions on current 18:00 market. Both are retrospective tests, not untouched holdouts. MSE improvements are predictive return loss, not FT winner accuracy; FT goal difference/total associations are in the table. Model ROI and EV thresholds are exploratory, not validated betting decisions.


EXPLORATORY — NO PROVEN EDGE. ROI is units per unit staked (0.01 = 1%). CLV N/A; latest observed price is not a certified close. See [protocol](PROTOCOL.md), [input inventory](data_inventory.csv), [statistical tests with Holm adjustment](statistical_tests.csv). No frozen promotion gate changed.
