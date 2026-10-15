# Historical Pilot — measured 16 October 2026

Run: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38823349587
Executed commit: `9ad3352f174632645f48372fb25f87d109f71b26`. Completed 06:26 Asia/Bangkok.

Safety gate passed on exact research branch and environment `historical-research`.
Dedicated secret `HISTORICAL_ODDSPAPI_KEY` authenticated successfully. All 10 original
calibration fixtures returned live historical data, with 10/10 AH availability.
49 explicit fulltime soccer AH catalog entries reviewed; no catalog API request.

## Coverage and prices

Recovered **163 complete two-sided line snapshots**, covering **19/25 target fixture-slots (76%)**,
across all 10 fixtures. Nine fixtures have paired same-line historical/observed comparisons.
Calibration passed; no expansion beyond 10. Each snapshot is one fixture/slot/exact
AH line with home and away prices, not an independent match or a raw provider tick.
All 163 records, AH lines, prices, timestamps and provenance are in
`LIVE_PILOT_20261016.json`. Stale, inactive and missing quotes remain excluded.

The following prices are decimal odds, with the signed home AH line. Each example
uses the first recovered slot and its complete line nearest zero; ties use lower line.
This display rule does not identify the bookmaker mainline. Times below are UTC.

| Match | Recovered slots / targets | Snapshots | Example slot UTC | Home AH | Home / away odds |
|---|---:|---:|---|---:|---:|
| Mosta FC — Gzira United FC | 1/2 | 7 | 2026-10-14T14:00:00+00:00 | +0 | 1.934 / 1.826 |
| Bandirmaspor — Sivasspor | 1/1 | 9 | 2026-10-13T11:00:00+00:00 | +0 | 1.465 / 2.75 |
| GKS Katowice — Wieczysta Krakow | 3/3 | 25 | 2026-10-12T08:00:00+00:00 | +0 | 1.578 / 2.5 |
| Sporting CP — FC Arouca | 4/4 | 36 | 2026-09-19T08:00:00+00:00 | -1 | 1.229 / 4.21 |
| AFC Wimbledon — Milton Keynes Dons | 2/3 | 18 | 2026-09-17T08:00:00+00:00 | +0 | 2.16 / 1.751 |
| Levante UD — Athletic Bilbao | 1/3 | 9 | 2026-09-16T08:00:00+00:00 | +0 | 2.51 / 1.598 |
| Grasshopper Club Zurich — FC Sion | 1/2 | 9 | 2026-09-15T11:00:00+00:00 | +0 | 3.12 / 1.404 |
| Red Star FC — FC Metz | 3/4 | 25 | 2026-09-14T08:00:00+00:00 | -0.25 | 2.08 / 1.819 |
| SC Paderborn 07 — TSG Hoffenheim | 2/2 | 18 | 2026-09-20T14:00:00+00:00 | +0 | 3.37 / 1.362 |
| Olympiacos Piraeus B — Athens Kallithea FC | 1/1 | 7 | 2026-10-14T08:00:00+00:00 | +0 | 2.66 / 1.413 |

## Requests and quota isolation

- Actual requests: **34 total = 10 historical + 22 research account + 2 production account**.
- Historical responses: 10 live successes, cache hits 0; no retries.
- Research monthly count stayed **0/250 before and after every historical request**.
- Production monthly count stayed **189/250 → 189/250**, delta **0**.
- Distinct active subscription fingerprints verified; historical requests never used Production key.
- Observed monthly quota debit: **0**. These are real HTTP requests even with zero monthly debit.
- Distinct subscriptions and unchanged counters support separate monthly quota in this run;
  they do not establish that the provider has no shared infrastructure rate limit.

## Health, boundaries and validation

Main evidence at `c88381638c12e6663420ef8a9f447e7c8b3e6ef1` was copied read-only
into isolated storage and evaluated with main's health code at 06:24:37 Asia/Bangkok.
Health WARNING: FT_DELAY, FT_IDENTITY_CONFLICT, UNMATCHED_IDENTITY_CANDIDATES,
LATEST_SCAN_WARNING. Input hashes remained unchanged; source quote timestamps were
not replaced. The original production probe job was skipped.

The standalone `historical-research-pilot.yml` is manual only. The already registered
matchday workflow has a research-only sibling for branch dispatch; its original
main-only job is unchanged. No new scheduled trigger. No production scheduler or
collector code change, merge, deployment, production write or expansion.

Validation at executed commit: GitHub CI all 3 checks successful; full offline CI
917 passed plus 5 subtests; targeted safety tests 76 passed.

Original sanitized artifact digest:
`sha256:b39cdc7769fb8ebc2431ada60ccb55ba20fd62893bec36d08768f59738ad8d9d`.
The artifact wrapper's historical_access label remained PENDING due to a reporting
label bug; its LIVE_CLIENT results, 10 historical requests and successful quota
comparisons prove actual endpoint access. Original artifact is retained unchanged.
