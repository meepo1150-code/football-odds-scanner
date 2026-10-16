# September 15–17 historical odds experiment

https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38867737713

Research only. Football-day membership uses the original explicit football_day where present. Bet365 kickoff before 06:00 Bangkok belongs to the previous football day, matching the established noon-to-06:00 window. Actual collection dates are preserved in source_observations.jsonl. Same fixture/bookmaker is fetched once and reused across dates. Targets at or after kickoff are NOT_PREMATCH_SLOT; candidates with no pre-kickoff target are not requested.

This football-day run: 15 new historical requests + 33 account checks, 43 cache hits. Across the entire task (including the initial collection-date experiment): **63 historical requests + 138 account checks = 201 HTTP calls**. All 63 live historical fixture/bookmaker requests were unique and HTTP 200. Research quota remained 0/250; production quota remained 192/250.

Initial collection-date execution: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38866711140

The initial count of 97 fixtures referred to collection dates and included fixtures of other football days. This canonical report contains the 52 unique fixtures / 58 fixture-bookmaker pairs belonging to football days September 15–17. The initial experiment and every request remain in sep15_17 for auditability.

**Coverage:** historical AH exists for 58/58 fixture-bookmaker pairs; 204/216 pre-kickoff target slots have a complete active recorded pair at or before target without an age limit; 198/216 have a pair within the balanced price range; 169/216 meet the one-hour freshness gate. The 47 unresolved fresh slots comprise 29 with older balanced pairs only, 6 with active pairs outside the balanced range, and 12 without a complete active pair before target. Sixteen other targets are at/after kickoff and excluded. Twenty-four unique fixtures pass all four fresh rounds.

**Validation:** 87 existing historical safety/price tests passed in every job. Published data checks reject future/in-play selected timestamps and duplicate live request identities. Same-bookmaker/same-line original-snapshot comparison: 72 complete quote pairs under the freshness gate; 57 exactly match both original prices. Other differences are retained and not automatically errors because capture times differ. No production collector, scheduler, quota ledger, data or dashboard writes occurred.

BALANCED_LINE requires active pairs, both decimal prices 1.80–2.20, each history-entry age <=3600 seconds. It does not mean official mainline. LAST_REPORTED.json and ALL_REPORTED_LINES.csv preserve older entries separately without a freshness claim. createdAt is the provider history-entry timestamp, not guaranteed bookmaker change time.

| Day | Unique fixtures | Fixture × bookmaker | Any recorded pair before target | Fresh balanced slots | Unresolved | At/after kickoff |
|---|---:|---:|---:|---:|---:|---:|
| 2026-09-15 | 24 | 26 | 87 | 70 | 24 | 10 |
| 2026-09-16 | 15 | 17 | 64 | 51 | 15 | 2 |
| 2026-09-17 | 13 | 15 | 53 | 48 | 8 | 4 |

## Prices and original timestamps (Bangkok)

| Day | Fixture / bookmaker | Target | Home AH | Home / away odds | Home / away history-entry time | Status |
|---|---|---|---|---|---|---|
| 2026-09-15 | Deportivo Alaves – Valencia CF / bet365 | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Deportivo Alaves – Valencia CF / bet365 | 2026-09-15T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Deportivo Alaves – Valencia CF / bet365 | 2026-09-15T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Deportivo Alaves – Valencia CF / bet365 | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Deportivo Alaves – Valencia CF / pinnacle | 2026-09-15T15:00:00+07:00 | -0.75 | 2.009 / 1.917 | 2026-09-15T14:56:00.387000+07:00 / 2026-09-15T14:56:00.387000+07:00 | BALANCED_LINE |
| 2026-09-15 | Deportivo Alaves – Valencia CF / pinnacle | 2026-09-15T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Deportivo Alaves – Valencia CF / pinnacle | 2026-09-15T21:00:00+07:00 | -0.75 | 1.934 / 1.98 | 2026-09-15T20:58:06.168000+07:00 / 2026-09-15T20:13:30.659000+07:00 | BALANCED_LINE |
| 2026-09-15 | Deportivo Alaves – Valencia CF / pinnacle | 2026-09-16T00:00:00+07:00 | -0.75 | 1.925 / 2.0 | 2026-09-15T23:54:52.611000+07:00 / 2026-09-15T23:54:52.611000+07:00 | BALANCED_LINE |
| 2026-09-16 | Atletico Madrid – CA Osasuna / bet365 | 2026-09-16T15:00:00+07:00 | -1.25 | 1.815 / 1.915 | 2026-09-16T14:29:18.411000+07:00 / 2026-09-16T14:29:18.411000+07:00 | BALANCED_LINE |
| 2026-09-16 | Atletico Madrid – CA Osasuna / bet365 | 2026-09-16T18:00:00+07:00 | -1.25 | 1.815 / 1.915 | 2026-09-16T17:46:59.035000+07:00 / 2026-09-16T17:46:59.035000+07:00 | BALANCED_LINE |
| 2026-09-16 | Atletico Madrid – CA Osasuna / bet365 | 2026-09-16T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Atletico Madrid – CA Osasuna / bet365 | 2026-09-17T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-17 | Real Betis Seville – Getafe CF / bet365 | 2026-09-17T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-17 | Real Betis Seville – Getafe CF / bet365 | 2026-09-17T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-17 | Real Betis Seville – Getafe CF / bet365 | 2026-09-17T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-17 | Real Betis Seville – Getafe CF / bet365 | 2026-09-18T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-17 | Real Betis Seville – Getafe CF / pinnacle | 2026-09-17T15:00:00+07:00 | -0.75 | 1.854 / 2.06 | 2026-09-17T14:54:36.594000+07:00 / 2026-09-17T14:54:36.594000+07:00 | BALANCED_LINE |
| 2026-09-17 | Real Betis Seville – Getafe CF / pinnacle | 2026-09-17T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-17 | Real Betis Seville – Getafe CF / pinnacle | 2026-09-17T21:00:00+07:00 | -1.0 | 2.02 / 1.9 | 2026-09-17T20:41:15.563000+07:00 / 2026-09-17T20:41:14.415000+07:00 | BALANCED_LINE |
| 2026-09-17 | Real Betis Seville – Getafe CF / pinnacle | 2026-09-18T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-16 | RC Deportivo de A Coruna – Sevilla FC / bet365 | 2026-09-16T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | RC Deportivo de A Coruna – Sevilla FC / bet365 | 2026-09-16T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | RC Deportivo de A Coruna – Sevilla FC / bet365 | 2026-09-16T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | RC Deportivo de A Coruna – Sevilla FC / bet365 | 2026-09-17T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | Elche CF – Real Madrid / pinnacle | 2026-09-15T15:00:00+07:00 | 2.0 | 2.02 / 1.884 | 2026-09-15T14:56:35.559000+07:00 / 2026-09-15T14:48:29.733000+07:00 | BALANCED_LINE |
| 2026-09-15 | Elche CF – Real Madrid / pinnacle | 2026-09-15T18:00:00+07:00 | 2.0 | 2.06 / 1.854 | 2026-09-15T17:58:15.499000+07:00 / 2026-09-15T17:58:15.499000+07:00 | BALANCED_LINE |
| 2026-09-15 | Elche CF – Real Madrid / pinnacle | 2026-09-15T21:00:00+07:00 | 2.0 | 2.029 / 1.884 | 2026-09-15T20:54:11.056000+07:00 / 2026-09-15T20:54:11.056000+07:00 | BALANCED_LINE |
| 2026-09-15 | Elche CF – Real Madrid / pinnacle | 2026-09-16T00:00:00+07:00 | 2.0 | 1.952 / 1.952 | 2026-09-15T23:44:53.388000+07:00 / 2026-09-15T23:44:53.388000+07:00 | BALANCED_LINE |
| 2026-09-16 | FC Barcelona – Racing Santander / bet365 | 2026-09-16T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | FC Barcelona – Racing Santander / bet365 | 2026-09-16T18:00:00+07:00 | -3.25 | 1.815 / 1.915 | 2026-09-16T17:46:25.521000+07:00 / 2026-09-16T17:46:25.521000+07:00 | BALANCED_LINE |
| 2026-09-16 | FC Barcelona – Racing Santander / bet365 | 2026-09-16T21:00:00+07:00 | -3.25 | 1.815 / 1.915 | 2026-09-16T20:48:34.948000+07:00 / 2026-09-16T20:48:34.948000+07:00 | BALANCED_LINE |
| 2026-09-16 | FC Barcelona – Racing Santander / bet365 | 2026-09-17T00:00:00+07:00 | -3.25 | 1.915 / 1.815 | 2026-09-16T23:10:14.076000+07:00 / 2026-09-16T23:10:14.076000+07:00 | BALANCED_LINE |
| 2026-09-16 | FC Barcelona – Racing Santander / pinnacle | 2026-09-16T15:00:00+07:00 | -3.25 | 1.9 / 1.99 | 2026-09-16T14:45:21.278000+07:00 / 2026-09-16T14:45:21.278000+07:00 | BALANCED_LINE |
| 2026-09-16 | FC Barcelona – Racing Santander / pinnacle | 2026-09-16T18:00:00+07:00 | -3.25 | 1.862 / 2.04 | 2026-09-16T17:47:15.124000+07:00 / 2026-09-16T17:47:15.124000+07:00 | BALANCED_LINE |
| 2026-09-16 | FC Barcelona – Racing Santander / pinnacle | 2026-09-16T21:00:00+07:00 | -3.25 | 2.0 / 1.892 | 2026-09-16T20:40:54.981000+07:00 / 2026-09-16T20:49:32.251000+07:00 | BALANCED_LINE |
| 2026-09-16 | FC Barcelona – Racing Santander / pinnacle | 2026-09-17T00:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Levante UD – Athletic Bilbao / bet365 | 2026-09-16T15:00:00+07:00 | 0.25 | 1.915 / 1.815 | 2026-09-16T14:28:49.610000+07:00 / 2026-09-16T14:28:49.610000+07:00 | BALANCED_LINE |
| 2026-09-16 | Levante UD – Athletic Bilbao / bet365 | 2026-09-16T18:00:00+07:00 | 0.25 | 1.915 / 1.815 | 2026-09-16T17:46:28.382000+07:00 / 2026-09-16T17:46:28.382000+07:00 | BALANCED_LINE |
| 2026-09-16 | Levante UD – Athletic Bilbao / bet365 | 2026-09-16T21:00:00+07:00 | 0.25 | 1.915 / 1.815 | 2026-09-16T20:30:25.097000+07:00 / 2026-09-16T20:30:25.097000+07:00 | BALANCED_LINE |
| 2026-09-16 | Levante UD – Athletic Bilbao / bet365 | 2026-09-17T00:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Levante UD – Athletic Bilbao / pinnacle | 2026-09-16T15:00:00+07:00 | 0.25 | 2.02 / 1.909 | 2026-09-16T14:52:28.315000+07:00 / 2026-09-16T14:52:28.315000+07:00 | BALANCED_LINE |
| 2026-09-16 | Levante UD – Athletic Bilbao / pinnacle | 2026-09-16T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Levante UD – Athletic Bilbao / pinnacle | 2026-09-16T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Levante UD – Athletic Bilbao / pinnacle | 2026-09-17T00:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-17 | Malaga CF – Villarreal CF / bet365 | 2026-09-17T15:00:00+07:00 | 0.5 | 1.815 / 1.915 | 2026-09-17T14:51:30.641000+07:00 / 2026-09-17T14:51:30.641000+07:00 | BALANCED_LINE |
| 2026-09-17 | Malaga CF – Villarreal CF / bet365 | 2026-09-17T18:00:00+07:00 | 0.5 | 1.865 / 1.865 | 2026-09-17T17:55:18.765000+07:00 / 2026-09-17T17:55:18.765000+07:00 | BALANCED_LINE |
| 2026-09-17 | Malaga CF – Villarreal CF / bet365 | 2026-09-17T21:00:00+07:00 | 0.5 | 1.865 / 1.865 | 2026-09-17T20:08:58.549000+07:00 / 2026-09-17T20:08:58.549000+07:00 | BALANCED_LINE |
| 2026-09-17 | Malaga CF – Villarreal CF / bet365 | 2026-09-18T00:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-17 | Malaga CF – Villarreal CF / pinnacle | 2026-09-17T15:00:00+07:00 | 0.5 | 1.952 / 1.952 | 2026-09-17T14:33:08.689000+07:00 / 2026-09-17T14:33:08.689000+07:00 | BALANCED_LINE |
| 2026-09-17 | Malaga CF – Villarreal CF / pinnacle | 2026-09-17T18:00:00+07:00 | 0.5 | 1.97 / 1.952 | 2026-09-17T17:59:33.301000+07:00 / 2026-09-17T17:59:33.301000+07:00 | BALANCED_LINE |
| 2026-09-17 | Malaga CF – Villarreal CF / pinnacle | 2026-09-17T21:00:00+07:00 | 0.5 | 1.943 / 1.98 | 2026-09-17T20:59:32.605000+07:00 / 2026-09-17T20:59:32.605000+07:00 | BALANCED_LINE |
| 2026-09-17 | Malaga CF – Villarreal CF / pinnacle | 2026-09-18T00:00:00+07:00 | 0.5 | 1.943 / 1.98 | 2026-09-17T23:55:50.227000+07:00 / 2026-09-17T23:55:50.227000+07:00 | BALANCED_LINE |
| 2026-09-15 | Rayo Vallecano – Espanyol Barcelona / bet365 | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Rayo Vallecano – Espanyol Barcelona / bet365 | 2026-09-15T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Rayo Vallecano – Espanyol Barcelona / bet365 | 2026-09-15T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Rayo Vallecano – Espanyol Barcelona / bet365 | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | Rayo Vallecano – Espanyol Barcelona / pinnacle | 2026-09-15T15:00:00+07:00 | -0.25 | 2.05 / 1.884 | 2026-09-15T14:46:35.375000+07:00 / 2026-09-15T14:46:35.375000+07:00 | BALANCED_LINE |
| 2026-09-15 | Rayo Vallecano – Espanyol Barcelona / pinnacle | 2026-09-15T18:00:00+07:00 | -0.25 | 2.06 / 1.869 | 2026-09-15T17:49:51.686000+07:00 / 2026-09-15T17:20:39.774000+07:00 | BALANCED_LINE |
| 2026-09-15 | Rayo Vallecano – Espanyol Barcelona / pinnacle | 2026-09-15T21:00:00+07:00 | -0.25 | 2.1 / 1.84 | 2026-09-15T20:41:23.557000+07:00 / 2026-09-15T20:41:23.557000+07:00 | BALANCED_LINE |
| 2026-09-15 | Rayo Vallecano – Espanyol Barcelona / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | Bristol City – Lincoln City / pinnacle | 2026-09-15T15:00:00+07:00 | -0.5 | 1.877 / 2.029 | 2026-09-15T14:55:22.145000+07:00 / 2026-09-15T14:55:22.145000+07:00 | BALANCED_LINE |
| 2026-09-15 | Bristol City – Lincoln City / pinnacle | 2026-09-15T18:00:00+07:00 | -0.5 | 1.892 / 2.02 | 2026-09-15T17:49:09.793000+07:00 / 2026-09-15T17:49:09.793000+07:00 | BALANCED_LINE |
| 2026-09-15 | Bristol City – Lincoln City / pinnacle | 2026-09-15T21:00:00+07:00 | -0.5 | 1.934 / 1.97 | 2026-09-15T20:08:17.106000+07:00 / 2026-09-15T20:08:17.106000+07:00 | BALANCED_LINE |
| 2026-09-15 | Bristol City – Lincoln City / pinnacle | 2026-09-16T00:00:00+07:00 | -0.5 | 1.961 / 1.943 | 2026-09-15T23:53:29.971000+07:00 / 2026-09-15T23:53:29.971000+07:00 | BALANCED_LINE |
| 2026-09-15 | Middlesbrough FC – Millwall FC / pinnacle | 2026-09-15T15:00:00+07:00 | -1.0 | 1.833 / 2.09 | 2026-09-15T14:27:09.390000+07:00 / 2026-09-15T14:27:09.390000+07:00 | BALANCED_LINE |
| 2026-09-15 | Middlesbrough FC – Millwall FC / pinnacle | 2026-09-15T18:00:00+07:00 | -1.25 | 2.06 / 1.854 | 2026-09-15T17:46:41.721000+07:00 / 2026-09-15T17:46:41.721000+07:00 | BALANCED_LINE |
| 2026-09-15 | Middlesbrough FC – Millwall FC / pinnacle | 2026-09-15T21:00:00+07:00 | -1.25 | 2.029 / 1.877 | 2026-09-15T20:59:36.119000+07:00 / 2026-09-15T20:59:36.119000+07:00 | BALANCED_LINE |
| 2026-09-15 | Middlesbrough FC – Millwall FC / pinnacle | 2026-09-16T00:00:00+07:00 | -1.25 | 1.925 / 1.98 | 2026-09-15T23:50:57.788000+07:00 / 2026-09-15T23:50:57.788000+07:00 | BALANCED_LINE |
| 2026-09-15 | Peterborough United – Barnsley FC / pinnacle | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Peterborough United – Barnsley FC / pinnacle | 2026-09-15T18:00:00+07:00 | -0.25 | 2.0 / 1.892 | 2026-09-15T17:33:40.440000+07:00 / 2026-09-15T17:33:40.440000+07:00 | BALANCED_LINE |
| 2026-09-15 | Peterborough United – Barnsley FC / pinnacle | 2026-09-15T21:00:00+07:00 | -0.25 | 1.98 / 1.909 | 2026-09-15T20:58:10.728000+07:00 / 2026-09-15T20:56:43.486000+07:00 | BALANCED_LINE |
| 2026-09-15 | Peterborough United – Barnsley FC / pinnacle | 2026-09-16T00:00:00+07:00 | -0.25 | 2.0 / 1.862 | 2026-09-15T23:48:13.814000+07:00 / 2026-09-15T23:48:13.814000+07:00 | BALANCED_LINE |
| 2026-09-15 | West Ham United – Fulham FC / pinnacle | 2026-09-15T15:00:00+07:00 | 0.25 | 1.847 / 2.05 | 2026-09-15T14:24:46.017000+07:00 / 2026-09-15T14:24:46.017000+07:00 | BALANCED_LINE |
| 2026-09-15 | West Ham United – Fulham FC / pinnacle | 2026-09-15T18:00:00+07:00 | 0.0 | 2.06 / 1.833 | 2026-09-15T17:50:52.806000+07:00 / 2026-09-15T17:50:52.806000+07:00 | BALANCED_LINE |
| 2026-09-15 | West Ham United – Fulham FC / pinnacle | 2026-09-15T21:00:00+07:00 | 0.0 | 2.009 / 1.884 | 2026-09-15T20:30:25.407000+07:00 / 2026-09-15T20:30:25.407000+07:00 | BALANCED_LINE |
| 2026-09-15 | West Ham United – Fulham FC / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Ipswich Town – Arsenal FC / pinnacle | 2026-09-15T15:00:00+07:00 | 1.5 | 1.961 / 1.943 | 2026-09-15T14:56:45.771000+07:00 / 2026-09-15T14:56:45.771000+07:00 | BALANCED_LINE |
| 2026-09-15 | Ipswich Town – Arsenal FC / pinnacle | 2026-09-15T18:00:00+07:00 | 1.75 | 1.854 / 2.06 | 2026-09-15T17:16:04.895000+07:00 / 2026-09-15T17:16:04.895000+07:00 | BALANCED_LINE |
| 2026-09-15 | Ipswich Town – Arsenal FC / pinnacle | 2026-09-15T21:00:00+07:00 | 1.5 | 2.05 / 1.862 | 2026-09-15T20:57:24.569000+07:00 / 2026-09-15T20:57:24.569000+07:00 | BALANCED_LINE |
| 2026-09-15 | Ipswich Town – Arsenal FC / pinnacle | 2026-09-16T00:00:00+07:00 | 1.75 | 1.884 / 1.952 | 2026-09-15T23:57:29.506000+07:00 / 2026-09-15T23:57:29.506000+07:00 | BALANCED_LINE |
| 2026-09-15 | Reading FC – Brentford FC / pinnacle | 2026-09-15T15:00:00+07:00 | 1.75 | 1.961 / 1.909 | 2026-09-15T14:07:54.239000+07:00 / 2026-09-15T14:07:54.239000+07:00 | BALANCED_LINE |
| 2026-09-15 | Reading FC – Brentford FC / pinnacle | 2026-09-15T18:00:00+07:00 | 1.75 | 1.97 / 1.9 | 2026-09-15T17:16:04.895000+07:00 / 2026-09-15T17:16:04.895000+07:00 | BALANCED_LINE |
| 2026-09-15 | Reading FC – Brentford FC / pinnacle | 2026-09-15T21:00:00+07:00 | 2.0 | 1.854 / 2.02 | 2026-09-15T20:53:18.928000+07:00 / 2026-09-15T20:53:18.928000+07:00 | BALANCED_LINE |
| 2026-09-15 | Reading FC – Brentford FC / pinnacle | 2026-09-16T00:00:00+07:00 | 2.0 | 1.98 / 1.862 | 2026-09-15T23:48:41.008000+07:00 / 2026-09-15T23:48:41.008000+07:00 | BALANCED_LINE |
| 2026-09-16 | Fleetwood Town – Sheffield United / pinnacle | 2026-09-16T15:00:00+07:00 | 0.75 | 2.009 / 1.884 | 2026-09-16T14:35:03.911000+07:00 / 2026-09-16T14:35:03.911000+07:00 | BALANCED_LINE |
| 2026-09-16 | Fleetwood Town – Sheffield United / pinnacle | 2026-09-16T18:00:00+07:00 | 0.75 | 2.029 / 1.862 | 2026-09-16T17:46:23.547000+07:00 / 2026-09-16T17:46:23.547000+07:00 | BALANCED_LINE |
| 2026-09-16 | Fleetwood Town – Sheffield United / pinnacle | 2026-09-16T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Fleetwood Town – Sheffield United / pinnacle | 2026-09-17T00:00:00+07:00 | 0.75 | 2.05 / 1.813 | 2026-09-16T23:50:08.526000+07:00 / 2026-09-16T23:50:08.526000+07:00 | BALANCED_LINE |
| 2026-09-16 | Coventry City – Aston Villa / pinnacle | 2026-09-16T15:00:00+07:00 | 0.25 | 1.99 / 1.9 | 2026-09-16T14:52:15.977000+07:00 / 2026-09-16T14:09:01.259000+07:00 | BALANCED_LINE |
| 2026-09-16 | Coventry City – Aston Villa / pinnacle | 2026-09-16T18:00:00+07:00 | 0.25 | 1.97 / 1.917 | 2026-09-16T17:07:43.464000+07:00 / 2026-09-16T17:07:43.464000+07:00 | BALANCED_LINE |
| 2026-09-16 | Coventry City – Aston Villa / pinnacle | 2026-09-16T21:00:00+07:00 | 0.25 | 2.02 / 1.869 | 2026-09-16T20:29:10.863000+07:00 / 2026-09-16T20:36:03.028000+07:00 | BALANCED_LINE |
| 2026-09-16 | Coventry City – Aston Villa / pinnacle | 2026-09-17T00:00:00+07:00 | 0.5 | 1.877 / 1.98 | 2026-09-16T23:57:22.689000+07:00 / 2026-09-16T23:51:11.455000+07:00 | BALANCED_LINE |
| 2026-09-15 | Liverpool FC – Tottenham Hotspur / pinnacle | 2026-09-15T15:00:00+07:00 | -0.75 | 1.877 / 2.029 | 2026-09-15T14:56:34.620000+07:00 / 2026-09-15T14:56:34.620000+07:00 | BALANCED_LINE |
| 2026-09-15 | Liverpool FC – Tottenham Hotspur / pinnacle | 2026-09-15T18:00:00+07:00 | -0.75 | 1.909 / 2.0 | 2026-09-15T17:40:26.074000+07:00 / 2026-09-15T17:40:26.074000+07:00 | BALANCED_LINE |
| 2026-09-15 | Liverpool FC – Tottenham Hotspur / pinnacle | 2026-09-15T21:00:00+07:00 | -0.75 | 1.99 / 1.909 | 2026-09-15T20:56:47.186000+07:00 / 2026-09-15T20:51:43.214000+07:00 | BALANCED_LINE |
| 2026-09-15 | Liverpool FC – Tottenham Hotspur / pinnacle | 2026-09-16T00:00:00+07:00 | -0.75 | 1.854 / 2.0 | 2026-09-15T23:56:25.102000+07:00 / 2026-09-15T23:48:26.342000+07:00 | BALANCED_LINE |
| 2026-09-16 | Manchester United – Brighton & Hove Albion / pinnacle | 2026-09-16T15:00:00+07:00 | -0.75 | 2.029 / 1.862 | 2026-09-16T14:20:51.659000+07:00 / 2026-09-16T14:20:51.659000+07:00 | BALANCED_LINE |
| 2026-09-16 | Manchester United – Brighton & Hove Albion / pinnacle | 2026-09-16T18:00:00+07:00 | -0.75 | 1.925 / 1.961 | 2026-09-16T17:30:40.242000+07:00 / 2026-09-16T17:30:40.242000+07:00 | BALANCED_LINE |
| 2026-09-16 | Manchester United – Brighton & Hove Albion / pinnacle | 2026-09-16T21:00:00+07:00 | -1.0 | 2.009 / 1.877 | 2026-09-16T20:45:32.864000+07:00 / 2026-09-16T20:45:32.864000+07:00 | BALANCED_LINE |
| 2026-09-16 | Manchester United – Brighton & Hove Albion / pinnacle | 2026-09-17T00:00:00+07:00 | -1.0 | 1.925 / 1.925 | 2026-09-16T23:50:39.355000+07:00 / 2026-09-16T23:50:39.355000+07:00 | BALANCED_LINE |
| 2026-09-17 | Manchester City – Norwich City / pinnacle | 2026-09-17T15:00:00+07:00 | -2.75 | 2.029 / 1.833 | 2026-09-17T14:48:45.266000+07:00 / 2026-09-17T14:48:45.266000+07:00 | BALANCED_LINE |
| 2026-09-17 | Manchester City – Norwich City / pinnacle | 2026-09-17T18:00:00+07:00 | -2.75 | 1.99 / 1.862 | 2026-09-17T17:49:09.995000+07:00 / 2026-09-17T17:49:09.995000+07:00 | BALANCED_LINE |
| 2026-09-17 | Manchester City – Norwich City / pinnacle | 2026-09-17T21:00:00+07:00 | -2.75 | 2.02 / 1.84 | 2026-09-17T20:38:41.321000+07:00 / 2026-09-17T20:38:41.321000+07:00 | BALANCED_LINE |
| 2026-09-17 | Manchester City – Norwich City / pinnacle | 2026-09-18T00:00:00+07:00 | -2.25 | 1.892 / 1.952 | 2026-09-17T23:50:42.101000+07:00 / 2026-09-17T23:46:56.724000+07:00 | BALANCED_LINE |
| 2026-09-16 | Everton FC – Wolverhampton Wanderers / pinnacle | 2026-09-16T15:00:00+07:00 | -1.0 | 1.819 / 2.08 | 2026-09-16T14:58:08.565000+07:00 / 2026-09-16T14:02:53.170000+07:00 | BALANCED_LINE |
| 2026-09-16 | Everton FC – Wolverhampton Wanderers / pinnacle | 2026-09-16T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Everton FC – Wolverhampton Wanderers / pinnacle | 2026-09-16T21:00:00+07:00 | -1.25 | 2.05 / 1.847 | 2026-09-16T20:54:57.021000+07:00 / 2026-09-16T20:54:57.021000+07:00 | BALANCED_LINE |
| 2026-09-16 | Everton FC – Wolverhampton Wanderers / pinnacle | 2026-09-17T00:00:00+07:00 | -1.25 | 2.009 / 1.847 | 2026-09-16T23:50:16.159000+07:00 / 2026-09-16T23:50:16.159000+07:00 | BALANCED_LINE |
| 2026-09-17 | AFC Wimbledon – Milton Keynes Dons / pinnacle | 2026-09-17T15:00:00+07:00 | 0.25 | 1.826 / 2.08 | 2026-09-17T14:01:54.718000+07:00 / 2026-09-17T14:01:54.718000+07:00 | BALANCED_LINE |
| 2026-09-17 | AFC Wimbledon – Milton Keynes Dons / pinnacle | 2026-09-17T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-17 | AFC Wimbledon – Milton Keynes Dons / pinnacle | 2026-09-17T21:00:00+07:00 | 0.25 | 1.9 / 1.98 | 2026-09-17T20:44:33.629000+07:00 / 2026-09-17T20:45:19.817000+07:00 | BALANCED_LINE |
| 2026-09-17 | AFC Wimbledon – Milton Keynes Dons / pinnacle | 2026-09-18T00:00:00+07:00 | 0.0 | 2.009 / 1.877 | 2026-09-17T23:59:04.886000+07:00 / 2026-09-17T23:32:55.347000+07:00 | BALANCED_LINE |
| 2026-09-15 | Hibernian FC – Kilmarnock FC / pinnacle | 2026-09-15T15:00:00+07:00 | -1.25 | 1.909 / 2.0 | 2026-09-15T14:30:13.629000+07:00 / 2026-09-15T14:30:13.629000+07:00 | BALANCED_LINE |
| 2026-09-15 | Hibernian FC – Kilmarnock FC / pinnacle | 2026-09-15T18:00:00+07:00 | -1.25 | 1.917 / 1.99 | 2026-09-15T17:49:15.897000+07:00 / 2026-09-15T17:49:15.897000+07:00 | BALANCED_LINE |
| 2026-09-15 | Hibernian FC – Kilmarnock FC / pinnacle | 2026-09-15T21:00:00+07:00 | -1.25 | 1.869 / 2.04 | 2026-09-15T20:46:37.639000+07:00 / 2026-09-15T20:46:37.639000+07:00 | BALANCED_LINE |
| 2026-09-15 | Hibernian FC – Kilmarnock FC / pinnacle | 2026-09-16T00:00:00+07:00 | -1.25 | 1.854 / 2.06 | 2026-09-15T23:45:14.953000+07:00 / 2026-09-15T23:45:14.953000+07:00 | BALANCED_LINE |
| 2026-09-15 | Falkirk FC – Heart of Midlothian FC / pinnacle | 2026-09-15T15:00:00+07:00 | 0.5 | 1.943 / 1.961 | 2026-09-15T14:28:36.190000+07:00 / 2026-09-15T14:28:36.190000+07:00 | BALANCED_LINE |
| 2026-09-15 | Falkirk FC – Heart of Midlothian FC / pinnacle | 2026-09-15T18:00:00+07:00 | 0.5 | 1.98 / 1.925 | 2026-09-15T17:48:49.320000+07:00 / 2026-09-15T17:48:49.320000+07:00 | BALANCED_LINE |
| 2026-09-15 | Falkirk FC – Heart of Midlothian FC / pinnacle | 2026-09-15T21:00:00+07:00 | 0.5 | 2.0 / 1.909 | 2026-09-15T20:47:02+07:00 / 2026-09-15T20:40:03.161000+07:00 | BALANCED_LINE |
| 2026-09-15 | Falkirk FC – Heart of Midlothian FC / pinnacle | 2026-09-16T00:00:00+07:00 | 0.5 | 1.854 / 2.06 | 2026-09-15T23:45:59.174000+07:00 / 2026-09-15T23:45:59.174000+07:00 | BALANCED_LINE |
| 2026-09-15 | Motherwell FC – Aberdeen FC / pinnacle | 2026-09-15T15:00:00+07:00 | -0.5 | 1.869 / 2.04 | 2026-09-15T14:46:25.194000+07:00 / 2026-09-15T14:46:25.194000+07:00 | BALANCED_LINE |
| 2026-09-15 | Motherwell FC – Aberdeen FC / pinnacle | 2026-09-15T18:00:00+07:00 | -0.5 | 1.854 / 2.07 | 2026-09-15T17:51:04.016000+07:00 / 2026-09-15T17:51:04.016000+07:00 | BALANCED_LINE |
| 2026-09-15 | Motherwell FC – Aberdeen FC / pinnacle | 2026-09-15T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Motherwell FC – Aberdeen FC / pinnacle | 2026-09-16T00:00:00+07:00 | -0.5 | 1.847 / 2.07 | 2026-09-15T23:48:35.656000+07:00 / 2026-09-15T23:48:35.656000+07:00 | BALANCED_LINE |
| 2026-09-15 | Ajax Amsterdam – Willem II Tilburg / pinnacle | 2026-09-15T15:00:00+07:00 | -2.5 | 1.917 / 1.97 | 2026-09-15T14:44:42.809000+07:00 / 2026-09-15T14:44:42.809000+07:00 | BALANCED_LINE |
| 2026-09-15 | Ajax Amsterdam – Willem II Tilburg / pinnacle | 2026-09-15T18:00:00+07:00 | -2.5 | 1.862 / 2.029 | 2026-09-15T17:30:11.575000+07:00 / 2026-09-15T17:30:11.575000+07:00 | BALANCED_LINE |
| 2026-09-15 | Ajax Amsterdam – Willem II Tilburg / pinnacle | 2026-09-15T21:00:00+07:00 | -2.5 | 1.909 / 1.98 | 2026-09-15T20:58:04.940000+07:00 / 2026-09-15T20:58:04.940000+07:00 | BALANCED_LINE |
| 2026-09-15 | Ajax Amsterdam – Willem II Tilburg / pinnacle | 2026-09-16T00:00:00+07:00 | -2.75 | 1.99 / 1.9 | 2026-09-15T23:59:01.360000+07:00 / 2026-09-15T23:59:01.360000+07:00 | BALANCED_LINE |
| 2026-09-15 | Korona Kielce – Gornik Zabrze / pinnacle | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Korona Kielce – Gornik Zabrze / pinnacle | 2026-09-15T18:00:00+07:00 | 0.0 | 1.98 / 1.909 | 2026-09-15T17:33:33.356000+07:00 / 2026-09-15T17:33:33.356000+07:00 | BALANCED_LINE |
| 2026-09-15 | Korona Kielce – Gornik Zabrze / pinnacle | 2026-09-15T21:00:00+07:00 | 0.0 | 1.961 / 1.925 | 2026-09-15T20:21:17.972000+07:00 / 2026-09-15T20:21:17.972000+07:00 | BALANCED_LINE |
| 2026-09-15 | Korona Kielce – Gornik Zabrze / pinnacle | 2026-09-16T00:00:00+07:00 | 0.0 | 1.961 / 1.925 | 2026-09-15T23:37:55.750000+07:00 / 2026-09-15T23:37:55.750000+07:00 | BALANCED_LINE |
| 2026-09-15 | RKS Rakow Czestochowa – Zaglebie Lubin / pinnacle | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | RKS Rakow Czestochowa – Zaglebie Lubin / pinnacle | 2026-09-15T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | RKS Rakow Czestochowa – Zaglebie Lubin / pinnacle | 2026-09-15T21:00:00+07:00 | -0.5 | 2.07 / 1.826 | 2026-09-15T20:30:18.420000+07:00 / 2026-09-15T20:51:27.727000+07:00 | BALANCED_LINE |
| 2026-09-15 | RKS Rakow Czestochowa – Zaglebie Lubin / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | Grasshopper Club Zurich – FC Sion / pinnacle | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Grasshopper Club Zurich – FC Sion / pinnacle | 2026-09-15T18:00:00+07:00 | 0.5 | 2.04 / 1.869 | 2026-09-15T17:15:12.595000+07:00 / 2026-09-15T17:15:12.595000+07:00 | BALANCED_LINE |
| 2026-09-15 | Grasshopper Club Zurich – FC Sion / pinnacle | 2026-09-15T21:00:00+07:00 | 0.5 | 2.0 / 1.909 | 2026-09-15T20:48:40.013000+07:00 / 2026-09-15T20:48:40.013000+07:00 | BALANCED_LINE |
| 2026-09-15 | Grasshopper Club Zurich – FC Sion / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | Genoa CFC – FC Sudtirol Bolzano / pinnacle | 2026-09-15T15:00:00+07:00 | -1.0 | 2.029 / 1.862 | 2026-09-15T14:24:20.255000+07:00 / 2026-09-15T14:24:20.255000+07:00 | BALANCED_LINE |
| 2026-09-15 | Genoa CFC – FC Sudtirol Bolzano / pinnacle | 2026-09-15T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Genoa CFC – FC Sudtirol Bolzano / pinnacle | 2026-09-15T21:00:00+07:00 | -1.0 | 1.909 / 1.98 | 2026-09-15T20:48:09.437000+07:00 / 2026-09-15T20:48:09.437000+07:00 | BALANCED_LINE |
| 2026-09-15 | Genoa CFC – FC Sudtirol Bolzano / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | ACF Fiorentina – Pisa SC / pinnacle | 2026-09-15T15:00:00+07:00 | -1.25 | 1.884 / 2.009 | 2026-09-15T14:24:22.719000+07:00 / 2026-09-15T14:24:22.719000+07:00 | BALANCED_LINE |
| 2026-09-15 | ACF Fiorentina – Pisa SC / pinnacle | 2026-09-15T18:00:00+07:00 | -1.25 | 1.862 / 2.029 | 2026-09-15T17:18:48.599000+07:00 / 2026-09-15T17:18:48.599000+07:00 | BALANCED_LINE |
| 2026-09-15 | ACF Fiorentina – Pisa SC / pinnacle | 2026-09-15T21:00:00+07:00 | -1.25 | 1.862 / 2.029 | 2026-09-15T20:43:14.791000+07:00 / 2026-09-15T20:43:14.791000+07:00 | BALANCED_LINE |
| 2026-09-15 | ACF Fiorentina – Pisa SC / pinnacle | 2026-09-16T00:00:00+07:00 | -1.5 | 2.05 / 1.847 | 2026-09-15T23:50:20.020000+07:00 / 2026-09-15T23:50:20.020000+07:00 | BALANCED_LINE |
| 2026-09-15 | MSV Duisburg – TSV Havelse / pinnacle | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | MSV Duisburg – TSV Havelse / pinnacle | 2026-09-15T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | MSV Duisburg – TSV Havelse / pinnacle | 2026-09-15T21:00:00+07:00 | -1.75 | 1.99 / 1.862 | 2026-09-15T20:03:39.948000+07:00 / 2026-09-15T20:03:39.948000+07:00 | BALANCED_LINE |
| 2026-09-15 | MSV Duisburg – TSV Havelse / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | Jahn Regensburg – Fortuna Dusseldorf / pinnacle | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | Jahn Regensburg – Fortuna Dusseldorf / pinnacle | 2026-09-15T18:00:00+07:00 | 0.25 | 1.869 / 1.98 | 2026-09-15T17:42:55.639000+07:00 / 2026-09-15T17:42:55.639000+07:00 | BALANCED_LINE |
| 2026-09-15 | Jahn Regensburg – Fortuna Dusseldorf / pinnacle | 2026-09-15T21:00:00+07:00 | 0.25 | 1.854 / 2.0 | 2026-09-15T20:02:03.703000+07:00 / 2026-09-15T20:02:03.703000+07:00 | BALANCED_LINE |
| 2026-09-15 | Jahn Regensburg – Fortuna Dusseldorf / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | SV Meppen 1912 – FC Viktoria Cologne / pinnacle | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | SV Meppen 1912 – FC Viktoria Cologne / pinnacle | 2026-09-15T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | SV Meppen 1912 – FC Viktoria Cologne / pinnacle | 2026-09-15T21:00:00+07:00 | 0.25 | 1.909 / 1.943 | 2026-09-15T20:05:30.838000+07:00 / 2026-09-15T20:05:30.838000+07:00 | BALANCED_LINE |
| 2026-09-15 | SV Meppen 1912 – FC Viktoria Cologne / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | SG Sonnenhof Grossaspach – SC Verl / pinnacle | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | SG Sonnenhof Grossaspach – SC Verl / pinnacle | 2026-09-15T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | SG Sonnenhof Grossaspach – SC Verl / pinnacle | 2026-09-15T21:00:00+07:00 | -0.25 | 1.9 / 1.943 | 2026-09-15T20:39:41.054000+07:00 / 2026-09-15T20:48:58.711000+07:00 | BALANCED_LINE |
| 2026-09-15 | SG Sonnenhof Grossaspach – SC Verl / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-15 | FC Wurzburger Kickers – Alemannia Aachen / pinnacle | 2026-09-15T15:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-15 | FC Wurzburger Kickers – Alemannia Aachen / pinnacle | 2026-09-15T18:00:00+07:00 | 0.5 | 1.877 / 1.98 | 2026-09-15T17:43:48.131000+07:00 / 2026-09-15T17:43:48.131000+07:00 | BALANCED_LINE |
| 2026-09-15 | FC Wurzburger Kickers – Alemannia Aachen / pinnacle | 2026-09-15T21:00:00+07:00 | 0.5 | 1.84 / 2.02 | 2026-09-15T20:16:51.552000+07:00 / 2026-09-15T20:16:51.552000+07:00 | BALANCED_LINE |
| 2026-09-15 | FC Wurzburger Kickers – Alemannia Aachen / pinnacle | 2026-09-16T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-16 | AC Milan – SL Benfica / pinnacle | 2026-09-16T15:00:00+07:00 | -0.25 | 2.0 / 1.909 | 2026-09-16T14:48:29.907000+07:00 / 2026-09-16T14:48:29.907000+07:00 | BALANCED_LINE |
| 2026-09-16 | AC Milan – SL Benfica / pinnacle | 2026-09-16T18:00:00+07:00 | -0.25 | 1.99 / 1.917 | 2026-09-16T17:52:13.458000+07:00 / 2026-09-16T17:52:13.458000+07:00 | BALANCED_LINE |
| 2026-09-16 | AC Milan – SL Benfica / pinnacle | 2026-09-16T21:00:00+07:00 | -0.25 | 2.07 / 1.847 | 2026-09-16T20:56:32.938000+07:00 / 2026-09-16T20:56:32.938000+07:00 | BALANCED_LINE |
| 2026-09-16 | AC Milan – SL Benfica / pinnacle | 2026-09-17T00:00:00+07:00 | -0.25 | 2.029 / 1.877 | 2026-09-16T23:54:22.512000+07:00 / 2026-09-16T23:38:11.781000+07:00 | BALANCED_LINE |
| 2026-09-16 | Bayer Leverkusen – NK Celje / pinnacle | 2026-09-16T15:00:00+07:00 | -2.75 | 1.909 / 1.97 | 2026-09-16T14:11:42.107000+07:00 / 2026-09-16T14:23:02.643000+07:00 | BALANCED_LINE |
| 2026-09-16 | Bayer Leverkusen – NK Celje / pinnacle | 2026-09-16T18:00:00+07:00 | -3.0 | 2.04 / 1.854 | 2026-09-16T17:22:28.656000+07:00 / 2026-09-16T17:22:28.656000+07:00 | BALANCED_LINE |
| 2026-09-16 | Bayer Leverkusen – NK Celje / pinnacle | 2026-09-16T21:00:00+07:00 | -3.25 | 2.009 / 1.877 | 2026-09-16T20:59:44.893000+07:00 / 2026-09-16T20:59:48.638000+07:00 | BALANCED_LINE |
| 2026-09-16 | Bayer Leverkusen – NK Celje / pinnacle | 2026-09-17T00:00:00+07:00 | -3.5 | 2.04 / 1.854 | 2026-09-16T23:53:59.702000+07:00 / 2026-09-16T23:53:59.702000+07:00 | BALANCED_LINE |
| 2026-09-16 | Hapoel Be`er Sheva FC – GNK Dinamo Zagreb / pinnacle | 2026-09-16T15:00:00+07:00 | 0.5 | 2.05 / 1.869 | 2026-09-16T14:51:17.994000+07:00 / 2026-09-16T14:51:17.994000+07:00 | BALANCED_LINE |
| 2026-09-16 | Hapoel Be`er Sheva FC – GNK Dinamo Zagreb / pinnacle | 2026-09-16T18:00:00+07:00 | 0.5 | 2.06 / 1.854 | 2026-09-16T17:36:33.180000+07:00 / 2026-09-16T17:36:33.180000+07:00 | BALANCED_LINE |
| 2026-09-16 | Hapoel Be`er Sheva FC – GNK Dinamo Zagreb / pinnacle | 2026-09-16T21:00:00+07:00 | 0.5 | 2.06 / 1.854 | 2026-09-16T20:48:33.585000+07:00 / 2026-09-16T20:49:14.892000+07:00 | BALANCED_LINE |
| 2026-09-16 | Hapoel Be`er Sheva FC – GNK Dinamo Zagreb / pinnacle | 2026-09-17T00:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Olympiacos Piraeus – Jagiellonia Bialystok / pinnacle | 2026-09-16T15:00:00+07:00 | -1.5 | 1.943 / 1.961 | 2026-09-16T14:59:41.820000+07:00 / 2026-09-16T14:59:41.820000+07:00 | BALANCED_LINE |
| 2026-09-16 | Olympiacos Piraeus – Jagiellonia Bialystok / pinnacle | 2026-09-16T18:00:00+07:00 | -1.5 | 1.909 / 2.0 | 2026-09-16T17:45:52.787000+07:00 / 2026-09-16T17:33:18.986000+07:00 | BALANCED_LINE |
| 2026-09-16 | Olympiacos Piraeus – Jagiellonia Bialystok / pinnacle | 2026-09-16T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Olympiacos Piraeus – Jagiellonia Bialystok / pinnacle | 2026-09-17T00:00:00+07:00 | -1.75 | 2.06 / 1.854 | 2026-09-16T23:57:57.451000+07:00 / 2026-09-16T23:57:57.451000+07:00 | BALANCED_LINE |
| 2026-09-16 | RSC Anderlecht – Olympique Lyon / pinnacle | 2026-09-16T15:00:00+07:00 | 0.0 | 2.12 / 1.806 | 2026-09-16T14:57:24.837000+07:00 / 2026-09-16T14:57:24.837000+07:00 | BALANCED_LINE |
| 2026-09-16 | RSC Anderlecht – Olympique Lyon / pinnacle | 2026-09-16T18:00:00+07:00 | 0.25 | 1.847 / 2.07 | 2026-09-16T17:05:58.734000+07:00 / 2026-09-16T17:05:58.734000+07:00 | BALANCED_LINE |
| 2026-09-16 | RSC Anderlecht – Olympique Lyon / pinnacle | 2026-09-16T21:00:00+07:00 | 0.25 | 1.862 / 2.05 | 2026-09-16T20:49:03.571000+07:00 / 2026-09-16T20:49:03.571000+07:00 | BALANCED_LINE |
| 2026-09-16 | RSC Anderlecht – Olympique Lyon / pinnacle | 2026-09-17T00:00:00+07:00 | 0.25 | 1.847 / 2.07 | 2026-09-16T23:42:11.598000+07:00 / 2026-09-16T23:42:11.598000+07:00 | BALANCED_LINE |
| 2026-09-16 | SK Sturm Graz – Stade Rennais FC / pinnacle | 2026-09-16T15:00:00+07:00 | 0.5 | 2.02 / 1.892 | 2026-09-16T14:48:29.258000+07:00 / 2026-09-16T14:48:29.258000+07:00 | BALANCED_LINE |
| 2026-09-16 | SK Sturm Graz – Stade Rennais FC / pinnacle | 2026-09-16T18:00:00+07:00 | 0.75 | 1.854 / 2.06 | 2026-09-16T17:03:31.383000+07:00 / 2026-09-16T17:03:31.383000+07:00 | BALANCED_LINE |
| 2026-09-16 | SK Sturm Graz – Stade Rennais FC / pinnacle | 2026-09-16T21:00:00+07:00 | 0.75 | 1.847 / 2.07 | 2026-09-16T20:59:25.040000+07:00 / 2026-09-16T20:59:25.040000+07:00 | BALANCED_LINE |
| 2026-09-16 | SK Sturm Graz – Stade Rennais FC / pinnacle | 2026-09-17T00:00:00+07:00 | 0.75 | 1.892 / 2.009 | 2026-09-16T23:54:45.455000+07:00 / 2026-09-16T23:39:11.076000+07:00 | BALANCED_LINE |
| 2026-09-16 | Sunderland AFC – AZ Alkmaar / pinnacle | 2026-09-16T15:00:00+07:00 | -1.0 | 1.84 / 2.08 | 2026-09-16T14:31:49.548000+07:00 / 2026-09-16T14:31:49.548000+07:00 | BALANCED_LINE |
| 2026-09-16 | Sunderland AFC – AZ Alkmaar / pinnacle | 2026-09-16T18:00:00+07:00 | -1.0 | 1.826 / 2.1 | 2026-09-16T17:51:54.419000+07:00 / 2026-09-16T17:51:54.419000+07:00 | BALANCED_LINE |
| 2026-09-16 | Sunderland AFC – AZ Alkmaar / pinnacle | 2026-09-16T21:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-16 | Sunderland AFC – AZ Alkmaar / pinnacle | 2026-09-17T00:00:00+07:00 | -1.25 | 2.04 / 1.877 | 2026-09-16T23:59:17.418000+07:00 / 2026-09-16T23:58:55.921000+07:00 | BALANCED_LINE |
| 2026-09-17 | OFI Crete – TSG Hoffenheim / pinnacle | 2026-09-17T15:00:00+07:00 | 1.5 | 1.952 / 1.952 | 2026-09-17T14:56:40.982000+07:00 / 2026-09-17T14:56:40.982000+07:00 | BALANCED_LINE |
| 2026-09-17 | OFI Crete – TSG Hoffenheim / pinnacle | 2026-09-17T18:00:00+07:00 | 1.5 | 2.02 / 1.884 | 2026-09-17T17:52:18.838000+07:00 / 2026-09-17T17:35:51.129000+07:00 | BALANCED_LINE |
| 2026-09-17 | OFI Crete – TSG Hoffenheim / pinnacle | 2026-09-17T21:00:00+07:00 | 1.5 | 2.04 / 1.869 | 2026-09-17T20:49:22.405000+07:00 / 2026-09-17T20:49:22.405000+07:00 | BALANCED_LINE |
| 2026-09-17 | OFI Crete – TSG Hoffenheim / pinnacle | 2026-09-18T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-17 | PFC Levski Sofia – FC Salzburg / pinnacle | 2026-09-17T15:00:00+07:00 | 0.25 | 1.99 / 1.917 | 2026-09-17T14:23:09.560000+07:00 / 2026-09-17T14:42:23.355000+07:00 | BALANCED_LINE |
| 2026-09-17 | PFC Levski Sofia – FC Salzburg / pinnacle | 2026-09-17T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-17 | PFC Levski Sofia – FC Salzburg / pinnacle | 2026-09-17T21:00:00+07:00 | 0.25 | 2.08 / 1.84 | 2026-09-17T20:34:47.046000+07:00 / 2026-09-17T20:34:47.046000+07:00 | BALANCED_LINE |
| 2026-09-17 | PFC Levski Sofia – FC Salzburg / pinnacle | 2026-09-18T00:00:00+07:00 | None | None / None | — / — | NOT_PREMATCH_SLOT |
| 2026-09-17 | Besiktas Istanbul – Olympique Marseille / pinnacle | 2026-09-17T15:00:00+07:00 | -0.75 | 2.06 / 1.862 | 2026-09-17T14:55:27.289000+07:00 / 2026-09-17T14:55:27.289000+07:00 | BALANCED_LINE |
| 2026-09-17 | Besiktas Istanbul – Olympique Marseille / pinnacle | 2026-09-17T18:00:00+07:00 | None | None / None | — / — | MAINLINE_UNRESOLVED |
| 2026-09-17 | Besiktas Istanbul – Olympique Marseille / pinnacle | 2026-09-17T21:00:00+07:00 | -0.75 | 2.0 / 1.909 | 2026-09-17T20:47:47.545000+07:00 / 2026-09-17T20:47:47.545000+07:00 | BALANCED_LINE |
| 2026-09-17 | Besiktas Istanbul – Olympique Marseille / pinnacle | 2026-09-18T00:00:00+07:00 | -0.75 | 1.943 / 1.961 | 2026-09-17T23:27:04.621000+07:00 / 2026-09-17T23:27:04.621000+07:00 | BALANCED_LINE |
| 2026-09-17 | Celtic Glasgow – Ferencvarosi Budapest / pinnacle | 2026-09-17T15:00:00+07:00 | -0.75 | 1.98 / 1.925 | 2026-09-17T14:22:02.030000+07:00 / 2026-09-17T14:22:02.030000+07:00 | BALANCED_LINE |
| 2026-09-17 | Celtic Glasgow – Ferencvarosi Budapest / pinnacle | 2026-09-17T18:00:00+07:00 | -0.75 | 1.884 / 2.02 | 2026-09-17T17:10:59.873000+07:00 / 2026-09-17T17:38:49.995000+07:00 | BALANCED_LINE |
| 2026-09-17 | Celtic Glasgow – Ferencvarosi Budapest / pinnacle | 2026-09-17T21:00:00+07:00 | -0.75 | 1.934 / 1.97 | 2026-09-17T20:41:08.998000+07:00 / 2026-09-17T20:41:08.998000+07:00 | BALANCED_LINE |
| 2026-09-17 | Celtic Glasgow – Ferencvarosi Budapest / pinnacle | 2026-09-18T00:00:00+07:00 | -0.75 | 1.877 / 2.04 | 2026-09-17T23:50:13.743000+07:00 / 2026-09-17T23:50:13.743000+07:00 | BALANCED_LINE |
| 2026-09-17 | Crystal Palace – KKS Lech Poznan / pinnacle | 2026-09-17T15:00:00+07:00 | -1.5 | 2.08 / 1.84 | 2026-09-17T14:33:08.359000+07:00 / 2026-09-17T14:33:08.359000+07:00 | BALANCED_LINE |
| 2026-09-17 | Crystal Palace – KKS Lech Poznan / pinnacle | 2026-09-17T18:00:00+07:00 | -1.5 | 2.02 / 1.892 | 2026-09-17T17:52:43.609000+07:00 / 2026-09-17T17:52:43.609000+07:00 | BALANCED_LINE |
| 2026-09-17 | Crystal Palace – KKS Lech Poznan / pinnacle | 2026-09-17T21:00:00+07:00 | -1.5 | 1.98 / 1.925 | 2026-09-17T20:51:29.970000+07:00 / 2026-09-17T20:51:29.970000+07:00 | BALANCED_LINE |
| 2026-09-17 | Crystal Palace – KKS Lech Poznan / pinnacle | 2026-09-18T00:00:00+07:00 | -1.5 | 1.917 / 1.98 | 2026-09-17T23:43:40.960000+07:00 / 2026-09-17T23:08:42.133000+07:00 | BALANCED_LINE |
| 2026-09-17 | FC Viktoria Plzen – Union Saint-Gilloise / pinnacle | 2026-09-17T15:00:00+07:00 | 0.0 | 1.84 / 2.08 | 2026-09-17T14:55:00.485000+07:00 / 2026-09-17T14:55:00.485000+07:00 | BALANCED_LINE |
| 2026-09-17 | FC Viktoria Plzen – Union Saint-Gilloise / pinnacle | 2026-09-17T18:00:00+07:00 | 0.0 | 1.833 / 2.09 | 2026-09-17T17:00:38.073000+07:00 / 2026-09-17T17:00:38.073000+07:00 | BALANCED_LINE |
| 2026-09-17 | FC Viktoria Plzen – Union Saint-Gilloise / pinnacle | 2026-09-17T21:00:00+07:00 | 0.0 | 1.847 / 2.07 | 2026-09-17T20:48:59.815000+07:00 / 2026-09-17T20:48:59.815000+07:00 | BALANCED_LINE |
| 2026-09-17 | FC Viktoria Plzen – Union Saint-Gilloise / pinnacle | 2026-09-18T00:00:00+07:00 | 0.0 | 1.833 / 2.08 | 2026-09-17T23:37:17.679000+07:00 / 2026-09-17T23:54:24.075000+07:00 | BALANCED_LINE |
| 2026-09-17 | Juventus Turin – NEC Nijmegen / pinnacle | 2026-09-17T15:00:00+07:00 | -2.0 | 1.909 / 2.0 | 2026-09-17T14:56:18.222000+07:00 / 2026-09-17T14:58:15.070000+07:00 | BALANCED_LINE |
| 2026-09-17 | Juventus Turin – NEC Nijmegen / pinnacle | 2026-09-17T18:00:00+07:00 | -2.25 | 2.07 / 1.826 | 2026-09-17T17:58:44.578000+07:00 / 2026-09-17T17:58:44.578000+07:00 | BALANCED_LINE |
| 2026-09-17 | Juventus Turin – NEC Nijmegen / pinnacle | 2026-09-17T21:00:00+07:00 | -2.25 | 2.04 / 1.854 | 2026-09-17T20:45:47.067000+07:00 / 2026-09-17T20:45:47.067000+07:00 | BALANCED_LINE |
| 2026-09-17 | Juventus Turin – NEC Nijmegen / pinnacle | 2026-09-18T00:00:00+07:00 | -2.25 | 2.009 / 1.877 | 2026-09-17T23:30:31.345000+07:00 / 2026-09-17T23:19:05.072000+07:00 | BALANCED_LINE |
| 2026-09-17 | Lillestroem SK – SCU Torreense / pinnacle | 2026-09-17T15:00:00+07:00 | -0.75 | 1.826 / 2.1 | 2026-09-17T14:29:30.032000+07:00 / 2026-09-17T14:29:30.032000+07:00 | BALANCED_LINE |
| 2026-09-17 | Lillestroem SK – SCU Torreense / pinnacle | 2026-09-17T18:00:00+07:00 | -1.0 | 2.07 / 1.847 | 2026-09-17T17:36:09.912000+07:00 / 2026-09-17T17:36:09.912000+07:00 | BALANCED_LINE |
| 2026-09-17 | Lillestroem SK – SCU Torreense / pinnacle | 2026-09-17T21:00:00+07:00 | -1.0 | 2.11 / 1.819 | 2026-09-17T20:59:25.754000+07:00 / 2026-09-17T20:59:25.754000+07:00 | BALANCED_LINE |
| 2026-09-17 | Lillestroem SK – SCU Torreense / pinnacle | 2026-09-18T00:00:00+07:00 | -1.0 | 2.1 / 1.826 | 2026-09-17T23:20:50.586000+07:00 / 2026-09-17T23:26:18.056000+07:00 | BALANCED_LINE |
| 2026-09-17 | Real Sociedad San Sebastian – AFC Bournemouth / pinnacle | 2026-09-17T15:00:00+07:00 | 0.25 | 1.909 / 2.0 | 2026-09-17T14:56:38.003000+07:00 / 2026-09-17T14:56:38.003000+07:00 | BALANCED_LINE |
| 2026-09-17 | Real Sociedad San Sebastian – AFC Bournemouth / pinnacle | 2026-09-17T18:00:00+07:00 | 0.25 | 1.925 / 1.98 | 2026-09-17T17:51:28.950000+07:00 / 2026-09-17T17:51:28.950000+07:00 | BALANCED_LINE |
| 2026-09-17 | Real Sociedad San Sebastian – AFC Bournemouth / pinnacle | 2026-09-17T21:00:00+07:00 | 0.25 | 1.884 / 2.02 | 2026-09-17T20:58:12.498000+07:00 / 2026-09-17T20:58:12.498000+07:00 | BALANCED_LINE |
| 2026-09-17 | Real Sociedad San Sebastian – AFC Bournemouth / pinnacle | 2026-09-18T00:00:00+07:00 | 0.25 | 1.877 / 2.04 | 2026-09-17T23:59:52.733000+07:00 / 2026-09-17T23:36:08.327000+07:00 | BALANCED_LINE |
