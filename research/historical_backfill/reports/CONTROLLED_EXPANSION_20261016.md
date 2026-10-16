# Controlled Historical Expansion — 16 October 2026

Run: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38830015043
Executed commit: `92fc6326c0e032f32b014cb1b46306816e3b405d`. Status: **COMPLETED**.
Errors: [].

## Price quality and execution

Cache-only calibration PASS: ten fixtures, original 163 line snapshots reproduced,
19 balanced target slots, 6 unresolved, zero provider requests. Sporting regression
-2.00 at 1.892 / 1.990 verified. Full calibration evidence is in
`PRICE_QUALITY_CALIBRATION_20261016.md` and `.json`.

Expansion planned 100 total fixtures; original ten must be immutable cache hits.
Final resume cache hits: **93** (initial expansion used 10 cache hits). Original cached bytes unchanged after
expansion: **True**. Expansion started: True.

## Measured coverage

- Planned fixtures: 100; evaluated: **100**.
- Fixtures with Historical AH: **100**.
- Fixtures with a balanced representative: **73**.
- Complete all-line snapshots: **1176**. Of these **142** have both prices in the
  balanced range; **129** are selected representatives and 13 are eligible alternatives.
- Selected BALANCED_LINE fixture-slots: **129/235**.
- MAINLINE_UNRESOLVED slots: **106**; untested slots: **0**.
- Rejected candidate line/slot rows: 2004; reasons: {'INACTIVE_OR_UNKNOWN': 323, 'STALE_QUOTE': 382, 'PRICE_OUTSIDE_BALANCED_RANGE': 1034, 'NO_HISTORICAL_DATA': 265}.

Every selected record has both decimal odds in [1.80,2.20], explicit active states,
reviewed market ID and quarter line, and independent real quote timestamps at/before
its target and strictly before kickoff (maximum age 3,600 seconds).
BALANCED_LINE is a research rule, not a claim of official bookmaker mainline.
Multiple slots and ladder lines do not constitute independent matches.

## Requests and production checks

- **279 actual HTTP requests across the controlled expansion** = **90 historical +
  185 research account + 4 production account**. Calibration replay used zero requests.
- First expansion run: 83 historical + 169 research account + 2 production account = 254;
  stopped at 93/100 fixtures on PRODUCTION_HEALTH_STALE after 15 minutes. All 93 had
  validated receipts and raw bodies; no orphan response or price-quality anomaly.
  Run: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38828132875
- Fresh manual resume: **7 historical + 16 research account + 2 production account = 25**.
  Required all first 93 verified cached responses before any history call; no refetch.
  Health was recomputed from a fresh read-only main checkout without relaxing its age gate.
- Final dataset: 100 distinct live historical responses (10 earlier pilot + 90 new),
  100 valid raw-body hashes and 100 matching cache receipts. No repeated history request.
- Production verification status: **PASS**; monthly usage
  **189 → 189**;
  delta **0**.
- Research monthly usage before: 0;
  final historical before/after comparison: {'request_limit': 250, 'request_count': 0, 'subscription_fingerprint': '4bbd1880891d3c28d2c169b69ccc58f9be9c0879e83bc8037c52f3066284395e', 'entitled_bookmakers': ['bet365'], 'rate_limit': None}.
- Production key was limited to account-only identity/quota steps. Historical requests
  used HISTORICAL_ODDSPAPI_KEY in historical-research; no credential fallback.
- No retries, schedule addition, production data write, collector/scheduler/dashboard
  change, merge or deploy. Full run raw/cache and sanitized report are retained as artifact.
- Fresh production health: WARNING, issues ['FT_DELAY', 'FT_IDENTITY_CONFLICT', 'UNMATCHED_IDENTITY_CANDIDATES', 'LATEST_SCAN_WARNING']; input hashes unchanged
  True; source quote timestamps unchanged.
- Base expansion commit passed all three CI checks: **927 tests and 42 subtests**.
  Resume guard and full targeted safety suite: **87 tests passed**. All three CI checks also passed at commit df6a0611 (same resume code), including
  **928 tests and 42 subtests**, full offline run 38830042062; final report-only head checks are in the PR. No gate was weakened for coverage.

## Coverage limitations

Price availability is uneven: Pinnacle has balanced coverage 119/170 slots (70%),
Bet365 10/65 (15.38%). This is a missingness-selected pilot, not a representative
comparison of bookmaker quality. The 8–14-day age band has no candidates; no
coverage is claimed for that band. Historical AH market presence (100/100) does
not imply a usable balanced price at every target (129/235, 54.89%).

## Coverage breakdown

Coverage below counts selected balanced fixture-slots, not all ladder rows. Age is
computed at actual execution from kickoff dates in Asia/Bangkok; original calibration
fixtures can be older than 30 days and are explicitly shown in 31_plus.

| Dimension | Value | Evaluated fixtures | AH fixtures | Balanced / tested slots | All-line snapshots |
|---|---|---:|---:|---:|---:|
| age_band_actual | 0_7 | 31 | 31 | 35 / 51 | 324 |
| age_band_actual | 15_30 | 67 | 67 | 91 / 178 | 821 |
| age_band_actual | 31_plus | 2 | 2 | 3 / 6 | 31 |
| age_window_actual | 14 | 31 | 31 | 35 / 51 | 324 |
| age_window_actual | 30 | 98 | 98 | 126 / 229 | 1145 |
| age_window_actual | 7 | 31 | 31 | 35 / 51 | 324 |
| bookmaker | bet365 | 28 | 28 | 10 / 65 | 30 |
| bookmaker | pinnacle | 72 | 72 | 119 / 170 | 1146 |
| football_day | 2026-09-14 | 1 | 1 | 3 / 4 | 25 |
| football_day | 2026-09-15 | 6 | 6 | 10 / 14 | 100 |
| football_day | 2026-09-16 | 2 | 2 | 4 / 6 | 36 |
| football_day | 2026-09-17 | 3 | 3 | 6 / 8 | 54 |
| football_day | 2026-09-18 | 2 | 2 | 2 / 8 | 6 |
| football_day | 2026-09-19 | 35 | 35 | 54 / 112 | 505 |
| football_day | 2026-09-20 | 20 | 20 | 15 / 32 | 126 |
| football_day | 2026-10-12 | 12 | 12 | 18 / 28 | 179 |
| football_day | 2026-10-13 | 13 | 13 | 12 / 14 | 106 |
| football_day | 2026-10-14 | 6 | 6 | 5 / 9 | 39 |
| league | 2. Bundesliga | 1 | 1 | 4 / 4 | 36 |
| league | Allsvenskan | 2 | 2 | 4 / 4 | 36 |
| league | Bulgarian Second League | 1 | 1 | 0 / 1 | 0 |
| league | Bundesliga | 10 | 10 | 9 / 24 | 58 |
| league | Championship | 8 | 8 | 8 / 8 | 72 |
| league | Czech First League | 1 | 1 | 1 / 2 | 9 |
| league | Ekstraklasa | 4 | 4 | 6 / 11 | 58 |
| league | Eredivisie | 3 | 3 | 8 / 11 | 91 |
| league | LaLiga | 16 | 16 | 21 / 38 | 213 |
| league | LaLiga 2 | 3 | 3 | 7 / 9 | 72 |
| league | League One | 1 | 1 | 2 / 3 | 18 |
| league | Liga Leumit | 3 | 3 | 2 / 6 | 14 |
| league | Liga Portugal | 1 | 1 | 4 / 4 | 36 |
| league | Ligue 1 | 9 | 9 | 11 / 28 | 118 |
| league | Ligue 2 | 2 | 2 | 5 / 8 | 47 |
| league | Maltese Premier League | 1 | 1 | 1 / 2 | 7 |
| league | Meistriliiga | 2 | 2 | 1 / 3 | 7 |
| league | Nemzeti Bajnoksag II | 1 | 1 | 1 / 1 | 7 |
| league | Premier League | 9 | 9 | 5 / 18 | 14 |
| league | Premiership | 1 | 1 | 2 / 2 | 18 |
| league | Pro League | 2 | 2 | 6 / 8 | 56 |
| league | Scottish Championship | 1 | 1 | 1 / 2 | 9 |
| league | Serie A | 11 | 11 | 11 / 24 | 97 |
| league | Serie B | 1 | 1 | 2 / 4 | 18 |
| league | Super League | 1 | 1 | 1 / 2 | 9 |
| league | Super League Greece 2 | 1 | 1 | 1 / 1 | 7 |
| league | Superettan | 1 | 1 | 1 / 1 | 9 |
| league | Superliga | 1 | 1 | 2 / 4 | 22 |
| league | TFF 1 Lig | 2 | 2 | 2 / 2 | 18 |
| scan_slot_bangkok | 0 | 42 | 42 | 34 / 42 | 344 |
| scan_slot_bangkok | 15 | 79 | 79 | 39 / 79 | 307 |
| scan_slot_bangkok | 18 | 71 | 71 | 34 / 71 | 298 |
| scan_slot_bangkok | 21 | 43 | 43 | 22 / 43 | 227 |

## Per fixture and example prices

All times Asia/Bangkok. Example is earliest selected balanced target for each fixture;
full selected records and both quote timestamps are in the JSON report.

| Fixture | Bookmaker | Kickoff | Balanced / target slots | All-line snapshots | Example target | Home AH | Home / away odds | Actual home / away quote times |
|---|---|---|---:|---:|---|---:|---:|---|
| Mosta FC — Gzira United FC | pinnacle | 15/10/2026 00:00:00 | 1 / 2 | 7 | 14/10/2026 21:00:00 | +0 | 1.934 / 1.826 | 14/10/2026 20:23:04 / 14/10/2026 20:23:04 |
| Bandirmaspor — Sivasspor | pinnacle | 13/10/2026 18:30:00 | 1 / 1 | 9 | 13/10/2026 18:00:00 | -0.5 | 2.009 / 1.847 | 13/10/2026 17:54:16 / 13/10/2026 17:44:19 |
| GKS Katowice — Wieczysta Krakow | pinnacle | 13/10/2026 01:30:00 | 3 / 3 | 25 | 12/10/2026 15:00:00 | -0.25 | 1.826 / 2.07 | 12/10/2026 14:48:15 / 12/10/2026 14:48:15 |
| Sporting CP — FC Arouca | pinnacle | 20/09/2026 02:30:00 | 4 / 4 | 36 | 19/09/2026 15:00:00 | -2 | 1.892 / 1.99 | 19/09/2026 14:34:32 / 19/09/2026 14:34:32 |
| AFC Wimbledon — Milton Keynes Dons | pinnacle | 18/09/2026 02:00:00 | 2 / 3 | 18 | 17/09/2026 15:00:00 | +0.25 | 1.826 / 2.08 | 17/09/2026 14:01:54 / 17/09/2026 14:01:54 |
| Levante UD — Athletic Bilbao | pinnacle | 17/09/2026 02:30:00 | 1 / 3 | 9 | 16/09/2026 15:00:00 | +0.25 | 2.02 / 1.909 | 16/09/2026 14:52:28 / 16/09/2026 14:52:28 |
| Grasshopper Club Zurich — FC Sion | pinnacle | 16/09/2026 00:00:00 | 1 / 2 | 9 | 15/09/2026 18:00:00 | +0.5 | 2.04 / 1.869 | 15/09/2026 17:15:12 / 15/09/2026 17:15:12 |
| Red Star FC — FC Metz | pinnacle | 15/09/2026 01:45:00 | 3 / 4 | 25 | 14/09/2026 15:00:00 | -0.25 | 2.08 / 1.819 | 14/09/2026 14:14:41 / 14/09/2026 14:09:42 |
| SC Paderborn 07 — TSG Hoffenheim | pinnacle | 21/09/2026 00:30:00 | 2 / 2 | 18 | 20/09/2026 21:00:00 | +0.75 | 2.009 / 1.917 | 20/09/2026 20:33:47 / 20/09/2026 20:40:28 |
| Olympiacos Piraeus B — Athens Kallithea FC | pinnacle | 14/10/2026 18:45:00 | 1 / 1 | 7 | 14/10/2026 15:00:00 | +0.5 | 1.854 / 1.9 | 14/10/2026 14:49:12 / 14/10/2026 14:49:12 |
| AS Monaco — Racing Club De Lens | bet365 | 19/09/2026 01:45:00 | 1 / 4 | 3 | 19/09/2026 00:00:00 | -0.5 | 1.865 / 1.865 | 18/09/2026 23:02:49 / 18/09/2026 23:02:49 |
| JK Narva Trans — FC Kuressaare | pinnacle | 14/10/2026 20:00:00 | 0 / 1 | 0 | — | — | — | — |
| Bohemians Prague 1905 — FK Mlada Boleslav | pinnacle | 14/10/2026 23:00:00 | 1 / 2 | 9 | 14/10/2026 21:00:00 | -0.5 | 1.961 / 1.909 | 14/10/2026 20:35:27 / 14/10/2026 20:35:27 |
| Hapoel Rishon Lezion FC — Maccabi Kabilio Jaffa | pinnacle | 12/10/2026 23:00:00 | 1 / 2 | 7 | 12/10/2026 15:00:00 | -1 | 1.877 / 1.909 | 12/10/2026 14:46:24 / 12/10/2026 14:46:24 |
| IF Elfsborg — Halmstads BK | pinnacle | 13/10/2026 00:00:00 | 2 / 2 | 18 | 12/10/2026 15:00:00 | -1.5 | 1.961 / 1.925 | 12/10/2026 14:52:19 / 12/10/2026 14:53:21 |
| FC Metz — AS Saint-Etienne | pinnacle | 20/09/2026 01:00:00 | 2 / 4 | 22 | 19/09/2026 18:00:00 | +0.5 | 1.884 / 2.009 | 19/09/2026 17:18:53 / 19/09/2026 17:18:53 |
| CS Universitatea Craiova — Fotbal Club FCSB | pinnacle | 20/09/2026 00:30:00 | 2 / 4 | 22 | 19/09/2026 21:00:00 | -1 | 2.009 / 1.862 | 19/09/2026 20:32:45 / 19/09/2026 20:32:45 |
| Cadiz CF — Girona FC | pinnacle | 20/09/2026 02:00:00 | 3 / 4 | 27 | 19/09/2026 15:00:00 | +0.5 | 1.819 / 2.11 | 19/09/2026 14:08:06 / 19/09/2026 14:08:06 |
| Ascoli Calcio 1898 — US Avellino | pinnacle | 20/09/2026 00:30:00 | 2 / 4 | 18 | 19/09/2026 21:00:00 | -0.25 | 1.826 / 2.1 | 19/09/2026 20:30:38 / 19/09/2026 20:30:38 |
| Grazer AK 1902 — FK Austria Wien | pinnacle | 20/09/2026 00:30:00 | 2 / 4 | 18 | 19/09/2026 21:00:00 | +0 | 2.08 / 1.84 | 19/09/2026 20:32:24 / 19/09/2026 20:32:24 |
| Dynamo Dresden — Hertha BSC | pinnacle | 20/09/2026 01:30:00 | 4 / 4 | 36 | 19/09/2026 15:00:00 | +0 | 2.02 / 1.909 | 19/09/2026 14:08:06 / 19/09/2026 14:08:06 |
| RSC Anderlecht — SV Zulte Waregem | pinnacle | 20/09/2026 01:45:00 | 3 / 4 | 29 | 19/09/2026 15:00:00 | -0.75 | 1.99 / 1.917 | 19/09/2026 14:47:00 / 19/09/2026 14:47:00 |
| Willem II Tilburg — Fortuna Sittard | pinnacle | 20/09/2026 02:00:00 | 1 / 4 | 28 | 19/09/2026 15:00:00 | +0 | 1.961 / 1.943 | 19/09/2026 14:47:27 / 19/09/2026 14:47:27 |
| Venezia FC — Lazio Rome | pinnacle | 20/09/2026 01:45:00 | 4 / 4 | 36 | 19/09/2026 15:00:00 | +0.5 | 1.961 / 1.961 | 19/09/2026 14:45:25 / 19/09/2026 14:45:25 |
| Diosgyori VTK — Szentlorinc SE | pinnacle | 13/10/2026 23:00:00 | 1 / 1 | 7 | 13/10/2026 15:00:00 | -1 | 1.884 / 1.869 | 13/10/2026 14:05:12 / 13/10/2026 14:05:12 |
| PFC Montana 1921 — PFC Ludogorets Razgrad II | pinnacle | 13/10/2026 22:00:00 | 0 / 1 | 0 | — | — | — | — |
| Queens Park FC — Inverness Caledonian Thistle FC | pinnacle | 14/10/2026 01:45:00 | 1 / 2 | 9 | 14/10/2026 00:00:00 | +0.75 | 2.07 / 1.8 | 13/10/2026 23:47:33 / 13/10/2026 23:47:33 |
| IFK Norrkoping FK — GIF Sundsvall | pinnacle | 14/10/2026 00:00:00 | 1 / 1 | 9 | 13/10/2026 15:00:00 | -2 | 1.854 / 2 | 13/10/2026 14:06:27 / 13/10/2026 14:06:27 |
| Wrexham AFC — West Bromwich Albion | pinnacle | 14/10/2026 01:45:00 | 1 / 1 | 9 | 14/10/2026 00:00:00 | -0.25 | 1.925 / 1.98 | 13/10/2026 23:45:04 / 13/10/2026 23:45:04 |
| Manchester City — Sunderland AFC | bet365 | 20/09/2026 20:00:00 | 0 / 2 | 0 | — | — | — | — |
| Motherwell FC — Aberdeen FC | pinnacle | 16/09/2026 01:45:00 | 2 / 2 | 18 | 15/09/2026 15:00:00 | -0.5 | 1.869 / 2.04 | 15/09/2026 14:46:25 / 15/09/2026 14:46:25 |
| Paide Linnameeskond — Tartu JK Tammeka | pinnacle | 14/10/2026 23:00:00 | 1 / 2 | 7 | 14/10/2026 15:00:00 | -0.75 | 1.819 / 2.009 | 14/10/2026 14:56:36 / 14/10/2026 14:56:36 |
| Batman Petrolspor — Istanbulspor AS | pinnacle | 14/10/2026 18:30:00 | 1 / 1 | 9 | 14/10/2026 18:00:00 | -0.75 | 2 / 1.862 | 14/10/2026 17:43:50 / 14/10/2026 17:43:50 |
| Hapoel Kfar Shalem FC — Hapoel Ra`anana FC | pinnacle | 12/10/2026 23:00:00 | 1 / 2 | 7 | 12/10/2026 18:00:00 | +0.25 | 1.854 / 1.934 | 12/10/2026 17:20:51 / 12/10/2026 17:20:51 |
| Hapoel Kfar Saba FC — MS Ashdod | pinnacle | 12/10/2026 23:00:00 | 0 / 2 | 0 | — | — | — | — |
| RKS Radomiak Radom — LKP Motor Lublin | pinnacle | 12/10/2026 23:00:00 | 0 / 2 | 0 | — | — | — | — |
| Malmo FF — Kalmar FF | pinnacle | 13/10/2026 00:00:00 | 2 / 2 | 18 | 12/10/2026 15:00:00 | -0.75 | 1.961 / 1.925 | 12/10/2026 14:41:31 / 12/10/2026 14:41:31 |
| Levante UD — Sevilla FC | pinnacle | 13/10/2026 02:00:00 | 2 / 3 | 25 | 12/10/2026 15:00:00 | +0 | 1.934 / 1.99 | 12/10/2026 14:57:27 / 12/10/2026 14:57:27 |
| LKP Motor Lublin — Gornik Zabrze | pinnacle | 20/09/2026 01:15:00 | 3 / 4 | 27 | 19/09/2026 15:00:00 | +0.25 | 2.05 / 1.847 | 19/09/2026 14:49:57 / 19/09/2026 14:49:57 |
| Lommel SK — Yellow-Red KV Mechelen | pinnacle | 20/09/2026 01:45:00 | 3 / 4 | 27 | 19/09/2026 15:00:00 | +0 | 1.97 / 1.934 | 19/09/2026 14:31:13 / 19/09/2026 14:31:13 |
| Ajax Amsterdam — Excelsior Rotterdam | pinnacle | 20/09/2026 01:00:00 | 4 / 4 | 36 | 19/09/2026 15:00:00 | -2 | 2.009 / 1.884 | 19/09/2026 14:20:19 / 19/09/2026 14:27:49 |
| Toulouse FC — Le Havre AC | pinnacle | 20/09/2026 01:45:00 | 2 / 4 | 18 | 19/09/2026 18:00:00 | -0.75 | 1.909 / 2.02 | 19/09/2026 17:42:50 / 19/09/2026 17:20:11 |
| Olympique Lyon — Stade Rennais FC | pinnacle | 20/09/2026 01:45:00 | 2 / 4 | 21 | 19/09/2026 18:00:00 | -0.25 | 1.934 / 1.99 | 19/09/2026 17:10:10 / 19/09/2026 17:10:10 |
| Le Mans FC — FC Lorient | pinnacle | 20/09/2026 01:45:00 | 1 / 4 | 30 | 19/09/2026 18:00:00 | +0 | 2.06 / 1.877 | 19/09/2026 17:09:48 / 19/09/2026 17:09:47 |
| Angers SCO — ESTAC Troyes | pinnacle | 20/09/2026 01:45:00 | 2 / 4 | 18 | 19/09/2026 18:00:00 | -0.5 | 2.12 / 1.819 | 19/09/2026 17:34:56 / 19/09/2026 17:34:56 |
| Sevilla FC — FC Barcelona | pinnacle | 20/09/2026 02:00:00 | 4 / 4 | 36 | 19/09/2026 15:00:00 | +1.75 | 1.961 / 1.925 | 19/09/2026 14:08:06 / 19/09/2026 14:08:06 |
| Malaga CF — Villarreal CF | pinnacle | 18/09/2026 02:30:00 | 3 / 3 | 27 | 17/09/2026 15:00:00 | +0.5 | 1.952 / 1.952 | 17/09/2026 14:33:08 / 17/09/2026 14:33:08 |
| Real Betis Seville — Getafe CF | pinnacle | 18/09/2026 00:00:00 | 1 / 2 | 9 | 17/09/2026 15:00:00 | -0.75 | 1.854 / 2.06 | 17/09/2026 14:54:36 / 17/09/2026 14:54:36 |
| FC Barcelona — Racing Santander | pinnacle | 17/09/2026 02:30:00 | 3 / 3 | 27 | 16/09/2026 15:00:00 | -3.25 | 1.9 / 1.99 | 16/09/2026 14:45:21 / 16/09/2026 14:45:21 |
| RKS Rakow Czestochowa — Zaglebie Lubin | pinnacle | 15/09/2026 23:00:00 | 0 / 2 | 6 | — | — | — | — |
| Ajax Amsterdam — Willem II Tilburg | pinnacle | 16/09/2026 01:00:00 | 3 / 3 | 27 | 15/09/2026 15:00:00 | -2.5 | 1.917 / 1.97 | 15/09/2026 14:44:42 / 15/09/2026 14:44:42 |
| Rayo Vallecano — Espanyol Barcelona | pinnacle | 16/09/2026 00:00:00 | 2 / 2 | 18 | 15/09/2026 15:00:00 | -0.25 | 2.05 / 1.884 | 15/09/2026 14:46:35 / 15/09/2026 14:46:35 |
| Deportivo Alaves — Valencia CF | pinnacle | 16/09/2026 01:00:00 | 2 / 3 | 22 | 15/09/2026 15:00:00 | -0.75 | 2.009 / 1.917 | 15/09/2026 14:56:00 / 15/09/2026 14:56:00 |
| Wolverhampton Wanderers — Bolton Wanderers | pinnacle | 14/10/2026 01:45:00 | 1 / 1 | 9 | 14/10/2026 00:00:00 | -1.25 | 1.877 / 2.029 | 13/10/2026 23:47:24 / 13/10/2026 23:47:24 |
| Stoke City — Middlesbrough FC | pinnacle | 14/10/2026 02:00:00 | 1 / 1 | 9 | 14/10/2026 00:00:00 | +0.5 | 1.943 / 1.961 | 13/10/2026 23:08:56 / 13/10/2026 23:08:56 |
| Millwall FC — Swansea City | pinnacle | 14/10/2026 01:45:00 | 1 / 1 | 9 | 14/10/2026 00:00:00 | -0.25 | 2.04 / 1.869 | 13/10/2026 23:46:46 / 13/10/2026 23:46:46 |
| Cardiff City — Watford FC | pinnacle | 14/10/2026 01:45:00 | 1 / 1 | 9 | 14/10/2026 00:00:00 | -1 | 2.04 / 1.869 | 13/10/2026 23:46:47 / 13/10/2026 23:46:47 |
| Burnley FC — Charlton Athletic | pinnacle | 14/10/2026 01:45:00 | 1 / 1 | 9 | 14/10/2026 00:00:00 | -0.75 | 1.833 / 2.08 | 13/10/2026 23:46:54 / 13/10/2026 23:46:54 |
| Bristol City — Blackburn Rovers | pinnacle | 14/10/2026 01:45:00 | 1 / 1 | 9 | 14/10/2026 00:00:00 | -0.25 | 1.909 / 1.99 | 13/10/2026 23:59:58 / 13/10/2026 23:59:58 |
| Birmingham City — Preston North End | pinnacle | 14/10/2026 02:00:00 | 1 / 1 | 9 | 14/10/2026 00:00:00 | -1.25 | 2.09 / 1.833 | 13/10/2026 23:57:26 / 13/10/2026 23:59:16 |
| Tenerife CD — Girona FC | pinnacle | 13/10/2026 02:00:00 | 2 / 3 | 27 | 12/10/2026 15:00:00 | +0 | 2.05 / 1.862 | 12/10/2026 14:04:49 / 12/10/2026 14:04:49 |
| Real Oviedo — SD Eibar | pinnacle | 12/10/2026 23:30:00 | 2 / 2 | 18 | 12/10/2026 15:00:00 | -0.25 | 2.029 / 1.884 | 12/10/2026 14:52:19 / 12/10/2026 14:03:40 |
| Torino FC — Udinese Calcio | pinnacle | 13/10/2026 01:45:00 | 1 / 3 | 16 | 12/10/2026 15:00:00 | -0.25 | 2.09 / 1.847 | 12/10/2026 14:57:40 / 12/10/2026 14:57:40 |
| Atalanta BC — Venezia FC | pinnacle | 12/10/2026 23:30:00 | 2 / 2 | 18 | 12/10/2026 15:00:00 | -1 | 2.02 / 1.9 | 12/10/2026 14:59:55 / 12/10/2026 14:59:55 |
| Schalke 04 — SV 07 Elversberg | pinnacle | 20/09/2026 22:30:00 | 1 / 1 | 9 | 20/09/2026 21:00:00 | -0.5 | 1.98 / 1.943 | 20/09/2026 20:09:43 / 20/09/2026 20:09:43 |
| Bayer Leverkusen — RB Leipzig | bet365 | 20/09/2026 20:30:00 | 0 / 2 | 0 | — | — | — | — |
| OGC Nice — Lille OSC | pinnacle | 20/09/2026 22:15:00 | 1 / 1 | 9 | 20/09/2026 21:00:00 | +0.25 | 2.029 / 1.892 | 20/09/2026 20:30:52 / 20/09/2026 20:58:57 |
| Olympique Marseille — Paris Saint-Germain | pinnacle | 21/09/2026 01:45:00 | 2 / 2 | 18 | 20/09/2026 21:00:00 | +1.25 | 2.009 / 1.917 | 20/09/2026 20:50:15 / 20/09/2026 20:50:15 |
| AJ Auxerre — Stade Brest 29 | bet365 | 20/09/2026 20:00:00 | 0 / 2 | 0 | — | — | — | — |
| Parma Calcio — Genoa CFC | bet365 | 20/09/2026 20:00:00 | 0 / 2 | 1 | — | — | — | — |
| AC Milan — US Lecce | pinnacle | 21/09/2026 01:45:00 | 2 / 2 | 18 | 20/09/2026 21:00:00 | -1.75 | 1.952 / 1.952 | 20/09/2026 20:54:54 / 20/09/2026 20:54:54 |
| Juventus Turin — Atalanta BC | pinnacle | 20/09/2026 23:00:00 | 1 / 1 | 7 | 20/09/2026 21:00:00 | -0.75 | 1.952 / 1.97 | 20/09/2026 20:56:49 / 20/09/2026 20:56:49 |
| Frosinone Calcio — Como 1907 | bet365 | 20/09/2026 20:00:00 | 0 / 2 | 0 | — | — | — | — |
| ACF Fiorentina — SSC Napoli | bet365 | 20/09/2026 17:30:00 | 1 / 1 | 1 | 20/09/2026 15:00:00 | +0.25 | 1.84 / 1.89 | 20/09/2026 14:09:31 / 20/09/2026 14:09:31 |
| Leeds United — Crystal Palace | bet365 | 20/09/2026 20:00:00 | 1 / 2 | 1 | 20/09/2026 18:00:00 | -0.75 | 1.815 / 1.915 | 20/09/2026 17:04:56 / 20/09/2026 17:04:56 |
| Fulham FC — Manchester United | pinnacle | 20/09/2026 22:30:00 | 1 / 1 | 9 | 20/09/2026 21:00:00 | +0.5 | 1.884 / 2.04 | 20/09/2026 20:40:27 / 20/09/2026 20:40:27 |
| AFC Bournemouth — Liverpool FC | bet365 | 20/09/2026 20:00:00 | 0 / 2 | 0 | — | — | — | — |
| Villarreal CF — Levante UD | pinnacle | 20/09/2026 23:30:00 | 0 / 1 | 0 | — | — | — | — |
| Valencia CF — Real Sociedad San Sebastian | pinnacle | 21/09/2026 02:00:00 | 2 / 2 | 18 | 20/09/2026 21:00:00 | +0 | 2.07 / 1.862 | 20/09/2026 20:59:40 / 20/09/2026 20:59:40 |
| Getafe CF — Malaga CF | bet365 | 20/09/2026 19:00:00 | 0 / 2 | 1 | — | — | — | — |
| RC Deportivo de A Coruna — Real Betis Seville | pinnacle | 20/09/2026 23:30:00 | 0 / 1 | 7 | — | — | — | — |
| Atletico Madrid — Real Madrid | pinnacle | 20/09/2026 21:15:00 | 1 / 1 | 9 | 20/09/2026 21:00:00 | +0.5 | 1.9 / 2.029 | 20/09/2026 20:58:20 / 20/09/2026 20:58:20 |
| Werder Bremen — FC Augsburg | bet365 | 19/09/2026 20:30:00 | 0 / 2 | 2 | — | — | — | — |
| Hamburger SV — 1. FC Cologne | bet365 | 19/09/2026 20:30:00 | 0 / 2 | 2 | — | — | — | — |
| Borussia Monchengladbach — FSV Mainz | bet365 | 19/09/2026 20:30:00 | 1 / 2 | 1 | 19/09/2026 15:00:00 | +0.25 | 1.865 / 1.865 | 19/09/2026 14:32:12 / 19/09/2026 14:32:12 |
| Eintracht Frankfurt — SC Freiburg | bet365 | 19/09/2026 20:30:00 | 2 / 2 | 2 | 19/09/2026 15:00:00 | +0 | 1.815 / 1.915 | 19/09/2026 14:13:40 / 19/09/2026 14:13:40 |
| VfB Stuttgart — Borussia Dortmund | bet365 | 19/09/2026 23:30:00 | 0 / 3 | 3 | — | — | — | — |
| Paris FC — Strasbourg Alsace | bet365 | 19/09/2026 22:15:00 | 0 / 3 | 1 | — | — | — | — |
| Udinese Calcio — Cagliari Calcio | bet365 | 19/09/2026 20:00:00 | 0 / 2 | 0 | — | — | — | — |
| AS Roma — Inter Milano | bet365 | 19/09/2026 23:00:00 | 0 / 3 | 0 | — | — | — | — |
| Bologna FC — Torino FC | bet365 | 19/09/2026 20:00:00 | 0 / 2 | 0 | — | — | — | — |
| Tottenham Hotspur — Aston Villa | bet365 | 19/09/2026 18:30:00 | 2 / 2 | 2 | 19/09/2026 15:00:00 | -0.5 | 1.865 / 1.865 | 19/09/2026 14:30:37 / 19/09/2026 14:30:37 |
| Nottingham Forest — Coventry City | bet365 | 19/09/2026 23:30:00 | 0 / 3 | 0 | — | — | — | — |
| Newcastle United — Hull City | bet365 | 19/09/2026 21:00:00 | 0 / 2 | 1 | — | — | — | — |
| Everton FC — Ipswich Town | bet365 | 19/09/2026 21:00:00 | 0 / 2 | 0 | — | — | — | — |
| Brighton & Hove Albion — Arsenal FC | bet365 | 19/09/2026 21:00:00 | 1 / 2 | 1 | 19/09/2026 15:00:00 | +0.75 | 1.865 / 1.865 | 19/09/2026 14:20:29 / 19/09/2026 14:20:29 |
| CA Osasuna — Rayo Vallecano | bet365 | 19/09/2026 19:00:00 | 0 / 2 | 2 | — | — | — | — |
| RC Celta de Vigo — Racing Santander | bet365 | 19/09/2026 23:30:00 | 0 / 3 | 3 | — | — | — | — |
| Athletic Bilbao — Deportivo Alaves | bet365 | 19/09/2026 21:15:00 | 0 / 3 | 0 | — | — | — | — |
| Bayern Munich — Union Berlin | bet365 | 19/09/2026 01:30:00 | 1 / 4 | 3 | 18/09/2026 15:00:00 | -3.5 | 1.815 / 1.915 | 18/09/2026 14:31:10 / 18/09/2026 14:31:10 |
