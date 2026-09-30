# Research V2 operational audit — 30 September 2026

Audit scope: fixes merged in PRs #226, #227, #228. All values below are observed outputs, not estimates. Local suite: 312 tests passed. PR CI passed before each merge. Research remains PAPER_RESEARCH_ONLY.

## Component matrix

| Component | Status | Before | After | Evidence | Remaining blocker | Next automatic action |
|---|---|---|---|---|---|---|
| Legacy PropLine recovery | 🟡 WAITING | 84 unreliable legacy observations | 0 recovered; all 84 retained with individual reasons | reports/legacy_propline_recovery.json; separate empty staging artifact | No verified contemporaneous historical Pinnacle mainline source; later quotes cannot reconstruct earlier prices | Recheck local archives during each data rebuild |
| PinnWire collection | 🟢 GREEN for observed run | HTTP 429; repeated attempts | One request returned 694 events and 36 valid current-day observations | reports/pinnwire_research_v2_status.json, 2026-09-30T01:15:33Z | Shared demo quota may rate-limit future runs | Persist Retry-After/cooldown; use validated PropLine fallback |
| OddsPapi dependency | 🟡 WAITING_EXTERNAL_DATA | 280/250 account usage; exhausted | Non-account requests fail closed; archive cursor preserved; core scan/result paths work independently | reports/oddspapi_quota_health.json; provider_request_budget.py; oddspapi_history_state.json | Monthly provider quota | Unmetered account health every six hours; only resume gated requests when availability is proven |
| FT backlog | 🟡 PARTIAL | 519 unresolved in original statistical population | 491 matured unresolved; 36 new/recent unresolved; 527 total | reports/research_v2_operational_audit.json and missing FT ledger | 488 FotMob identity misses plus 3 exact identities not finished in latest run; cannot match merely by kickoff | Exact-ID/verified-identity free backfill four times daily |
| Daily result synchronization | 🟢 GREEN for verified local/result path | Stale 26 September report, 429 | Local coverage preserved; free sources run; canonical results merged; AH statistics rebuilt | Free Result Backfill runs 36654161880 and 36655506991 succeeded and produced persisted outputs | Full external fixture discovery remains incomplete; no completeness claim | 08:15/14:15/20:15/02:15 Bangkok backfills, refresh statistics and Pages |
| Provider redundancy | 🟡 PARTIAL | No qualified zero-cost execution source | PinnWire live Research V2 data; PropLine validated fallback; others explicitly not execution-qualified | Provider health reports; primary run above | Research collection does not establish execution freshness/capability | Primary weekday 18:00/21:00 Bangkok; weekends 12:00/15:00/18:00–22:00, fallback on primary failure |
| Forward validation | 🟡 COLLECTING | 10 / 4 / 0 settled | 10 / 4 / 0; minimum remains 150 per candidate; duplicate inflation guarded | reports/v2_forward_readiness.json; forward tests | 140 / 146 / 150 additional settlements; frozen OddsPapi/Bet365 preregistration remains quota-dependent | Retain frozen entry definition; collect when provider is available; exact result backfills continue |
| O/U 2.5 | 🟢 GREEN for data path | Alternate totals could enter priced 2.5 ROI | Exact 2.5, two valid prices, prematch time and provenance required; separate priced N | Schema 2.6 deployed; regression tests; actual groups expose n and ou25_priced_n | Small samples remain descriptive | Rebuild from verified data on each scan/result update |
| Dashboard | 🟡 PARTIAL verification | Potential stale day; inconsistent quarantine guards | Deployed HTML and data verified; newest day default; same Python/JS trust counts; exact AH settlement; null/conflict guards | Live deployment manifest run 36655584168, source 0b1039655b20b24a0099e6b0a3d98d29cc0f1c88; deployed JSON/HTML downloaded and checked | Cloud browser navigation stalled and only initial Loading state was observed; interactive filters/sorting not claimed tested | Deployment follows collector/result/statistics workflows; interactive browser verification still required |
| Workflow persistence/health | 🟢 GREEN for verified repaired paths | Duplicate scheduled collectors, stale file replacement, missing deployment triggers | One primary schedule with fallback; raw exact-record union; recompute against latest main; data assertions separate from provider health | PRs #226–228, workflow runs and regression tests | Unrelated historical workflow definitions are not a blanket guarantee of future health | Persist evidence, rebuild and check counts after each relevant run |

## Actual data counts

| Metric | Original known state | Verified deployed state |
|---|---:|---:|
| Raw snapshots | 1,177 | 1,222 |
| Verified snapshots | 1,093 | 1,136 |
| Quarantined snapshots | 84 | 86 |
| Recovered legacy snapshots | 0 | 0 |
| Unresolved FT fixtures | 519 | 527 = 491 matured + 36 future/recent |
| Settled statistical fixtures | 306 | 334 |
| Core-price settled fixtures | 286 | 312 |
| Movement fixtures / numeric deltas | 110 / 652 | 110 / 652 |
| Valid scans observed on 30 September | — | 36 observations at one scan timestamp |

The extra two quarantined observations were previously labelled verified PropLine mainlines but observed at 16:49Z after 16:00Z kickoff. They remain raw forensic evidence and are excluded from statistics. No legacy record was fabricated, clamped or promoted.

One completed FotMob backfill added 46 exact-identity bridge results to the raw canonical result store (report preserved at commit f610ac89e3108a338f5aa0054fd9c408f3559780). This is not 46 newly settled valid statistical fixtures: some results belong to quarantined observations or overlap other populations. The original valid statistical population gained 28 settlements; 36 newly collected fixtures increased the total unresolved counter. Latest repeat backfill added zero and preserved prior results.

## Provider qualification

| Provider | Observed evidence | Capability |
|---|---|---|
| PinnWire / Pinnacle | AVAILABLE, 694 events, 36 accepted observations, one request, zero 429 in latest run | RESEARCH_ONLY current collector; not execution-promoted |
| PropLine / Pinnacle | AVAILABLE, 189 source rows, zero in current football-day window in latest early-morning run; earlier validated observations retained | FALLBACK |
| OddsPapi | QUOTA_EXHAUSTED, limit 250, count 280, remaining 0 | WAITING_EXTERNAL_DATA |
| InferSports | Runner 36655846676: NO_USABLE_MARKETS, six missing event IDs, zero events probed and zero odds; health classification repaired to prevent misleading OK | HEALTH_ONLY, not execution-ready |
| Five Dollar Football | Latest inspected health NO_ROWS; current quote freshness not qualified | RESEARCH_ONLY |
| Singapore Pools / sgodds | Historical/opening data, no verified current-day execution data in inspected report | OPENING_ONLY |
| API-Football | Latest inspected shadow report SHADOW_FAILED | HEALTH_ONLY / unavailable for current collection |

No provider is advertised as a fully qualified zero-cost execution provider. No betting edge is asserted. More accepted data reduces missing coverage, but does not establish predictive validity or profitability.

Final follow-up runs all completed successfully: universe persistence 36655846647, archive 36655846626, provider health 36655846676, research CI 36655846550. The universe health artifact records requests_sent=0 and existing_candidates_preserved=true. Archive state records billable_requests_this_run=0, free_history_requests_this_run=0 and the original 2026-07-27 discovery cursor. These are correct external-wait states, not healthy OddsPapi data availability.

## Verification limits

Actual deployed raw JSONL, canonical results, schema 2.6 statistics, audit JSON and HTML were retrieved over HTTP. The deployed JavaScript trust function counted exactly 1,136 valid and 86 quarantined records, matching the deployed Python-derived statistics; no quarantined @3.xx/@4.xx/@5.xx PropLine quote entered the valid population. A 1–0 home win at AH −1.5 was verified as FULL_LOSS. The live HTML contains the newest-football-day selection fix. Pure JavaScript header sorting, conflict handling and null formatting have regression coverage. Full interactive browser verification was not completed, so dashboard verification remains partial.
