# Report 5 — Scan schedules

| mode | strategy | market | snapshot_fixtures | opportunities | bets | wr | roi | profit_units | max_drawdown_units | longest_losing_streak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DEPLOYABLE_FIRST_ELIGIBLE | A | AH | 1559 | 1478 | 1352 | 0.5063 | -0.0195 | -26.3310 | 62.3375 | 13 |
| DEPLOYABLE_FIRST_ELIGIBLE | A | OU | 1559 | 1504 | 1379 | 0.5022 | -0.0311 | -42.8220 | 73.8945 | 8 |
| DEPLOYABLE_FIRST_ELIGIBLE | B | AH | 1185 | 1127 | 1004 | 0.4969 | -0.0340 | -34.1730 | 57.5295 | 15 |
| DEPLOYABLE_FIRST_ELIGIBLE | B | OU | 1185 | 1146 | 1023 | 0.5072 | -0.0215 | -21.9990 | 46.8470 | 8 |
| DEPLOYABLE_FIRST_ELIGIBLE | C | AH | 1540 | 1463 | 1337 | 0.5043 | -0.0223 | -29.8345 | 64.8350 | 13 |
| DEPLOYABLE_FIRST_ELIGIBLE | C | OU | 1540 | 1486 | 1361 | 0.5025 | -0.0303 | -41.2630 | 72.3355 | 8 |
| DEPLOYABLE_FIRST_ELIGIBLE | D_T3 | AH | 1629 | 1555 | 1433 | 0.4917 | -0.0425 | -60.8380 | 88.0795 | 15 |
| DEPLOYABLE_FIRST_ELIGIBLE | D_T3 | OU | 1629 | 1580 | 1456 | 0.5017 | -0.0303 | -44.1290 | 66.6630 | 8 |
| DEPLOYABLE_FIRST_ELIGIBLE | B_EXACT18_AVAILABLE | AH | 1555 | 1490 | 1368 | 0.4981 | -0.0321 | -43.9175 | 76.1045 | 12 |
| DEPLOYABLE_FIRST_ELIGIBLE | B_EXACT18_AVAILABLE | OU | 1555 | 1504 | 1383 | 0.4998 | -0.0331 | -45.8015 | 71.4895 | 8 |
| LAST_AVAILABLE_ORACLE | A | AH | 1559 | 1490 | 1363 | 0.5044 | -0.0211 | -28.8235 | 61.2950 | 11 |
| LAST_AVAILABLE_ORACLE | A | OU | 1559 | 1509 | 1383 | 0.5047 | -0.0250 | -34.5275 | 70.9215 | 8 |
| LAST_AVAILABLE_ORACLE | B | AH | 1185 | 1127 | 1004 | 0.4969 | -0.0340 | -34.1730 | 57.5295 | 15 |
| LAST_AVAILABLE_ORACLE | B | OU | 1185 | 1146 | 1023 | 0.5072 | -0.0215 | -21.9990 | 46.8470 | 8 |
| LAST_AVAILABLE_ORACLE | C | AH | 1540 | 1470 | 1343 | 0.5023 | -0.0253 | -33.9340 | 64.1095 | 11 |
| LAST_AVAILABLE_ORACLE | C | OU | 1540 | 1491 | 1365 | 0.5039 | -0.0273 | -37.2320 | 69.2345 | 8 |

A=00/15/18/21 plus weekend 12; B=15 setup, 18 decision only; C=15/18/21; D_T3=latest available at kickoff−3h (no future backfill). DEPLOYABLE_FIRST_ELIGIBLE uses first observed eligible round; LAST_AVAILABLE_ORACLE is clearly an ex-post availability upper bound, not a deployable betting policy. Both use the same descriptive side rule. Strict B_EXACT18_AVAILABLE can use earlier observations but never calls them an 18:00 quote. Operational B waits for the actual 18:00 poll, at most 18:15 and strictly pre-kickoff.

| kickoff_band | fixtures | A_covered | B_18slot_covered | B_missing | setup_and_decision | B_exact18_prior_available |
| --- | --- | --- | --- | --- | --- | --- |
| BEFORE18 | 72 | 67 | 0 | 72 | 0 | 0 |
| 18–21 | 426 | 387 | 274 | 152 | 244 | 357 |
| 21–00 | 741 | 614 | 501 | 240 | 461 | 647 |
| 00–03 | 578 | 471 | 390 | 188 | 342 | 532 |
| 03–06 | 20 | 20 | 20 | 0 | 19 | 19 |

03–06 includes 05–06 on its own football day; 03–05 belongs to previous football day. Matches before 18:00 cannot be betting decisions at 18:00. Missing 18 slot stays missing. Setup coverage and decision coverage are separate.

| market | clusters | effect | ci95_low | ci95_high | missing_B_vs_A | union_effect | additional_future_pairs_for_80pct_power |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AH | 983 | -0.0158 | -0.0308 | -0.0022 | 373 | -0.0057 | 809 |
| OU | 1006 | -0.0024 | -0.0068 | 0.0022 | 378 | 0.0149 | 90 |

Matched policy effect compares B vs A on common settled fixtures; differs from pure price comparison because policy may choose another side/line. Union effect assigns zero profit to no bet (no synthetic price), quantifying opportunity loss. No noninferiority claim: proposed margin −0.02 unit/bet requires prospective validation and <=5pp coverage loss.

Ledger: {"ledger_rows": 167, "known_request_rows": 163, "unknown_request_rows": 4, "known_requests_total": 586.0, "known_B_retained": 274.0, "known_C_retained": 404.0, "caution": "Ledger receipts may omit other callers and account refreshes; not a verified counterfactual monthly bill. D batching cost unknown."}

Theoretical rounds/week: A=30, B=14, C=21. Equal cost per round would save B 53.3%, C 30%; NOT a measured bill reduction. Monthly calls depend on batch size, repeats and changing fixture universe; extrapolating incomplete ledger is unreliable. D requires a batching design before request cost can be estimated. See current_era_sensitivity.csv for post-18-Oct and post-21-Oct cohorts; historical missing slots are not assumed to be current schedule failures. request_periods.csv shows known requests by Bangkok day/month, with unknowns retained. Closed registry has zero validated bets, so benchmark opportunities are not proven profitable missed bets.


EXPLORATORY — NO PROVEN EDGE. ROI is units per unit staked (0.01 = 1%). CLV N/A; latest observed price is not a certified close. See [protocol](PROTOCOL.md), [input inventory](data_inventory.csv), [statistical tests with Holm adjustment](statistical_tests.csv). No frozen promotion gate changed.
