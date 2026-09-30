# Research V2 completion audit — 30 September 2026

## Changes completed

PR #231 closes the overnight Football Day gap in PinnWire collection. Upcoming matches before 06:00 Bangkok remain in the preceding Football Day; started matches and the exclusive 06:00 boundary remain excluded. Operational counts use the same Football Day as the dashboard. Raw historical observations are not rewritten or backdated.

Scheduled recovery checks run 37 minutes after the existing slots. They read local attempt timestamps first and suppress duplicate collection after any recorded attempt, including a 429. They do not fetch provider data outside a valid recovery window. This adds a bounded number of GitHub jobs; GitHub scheduling still cannot guarantee exact delivery time. Transport cooldown remains authoritative. No threshold or provider-semantic protection was weakened.

The full suite passes **323 tests**. Regression cases cover overnight fixtures, kickoff exclusion, the 06:00 boundary, midnight operational counts, missed-slot recovery, and no duplicate/out-of-slot provider calls.

## Completion matrix

| Component | Status | Before | After | Evidence | Remaining blocker | Next automatic action |
|---|---|---|---|---|---|---|
| Legacy quarantine | 🟡 WAITING / PARTIAL | 84 suspicious observations | 84 retained with individual reasons; 0 invented replacements | legacy_propline_recovery.json, full per-record ledger | Verified historical odds unavailable | Recheck local archives on rebuild |
| PinnWire | 🟡 WAITING / PARTIAL | 429 and missing overnight fixtures | Cooldown respected; Football Day fixed; scheduled recovery guarded | Provider report, PR #231, boundary tests | External 429; no current live output | Retry on next eligible scheduled slot after cooldown |
| OddsPapi | 🟡 WAITING / PARTIAL | Exhausted quota | Metered requests blocked; separate account health | provider_request_budget.py and quota report | Monthly quota, remaining 0 | Unmetered account refresh every six hours |
| FT backlog | 🟡 WAITING / PARTIAL | Missing results and 2 AET scores misclassified as FT | Strict normal-time FT; AET quarantined; repeated free-source backfill | Canonical results, conflict ledger, runner report | Exact identity/normal-time results missing | Four daily free-result backfills |
| Daily sync | 🟢 GREEN | Dependency on exhausted fixture provider | Local state preserved; independent results and rebuild path executed | Free backfill runner, daily status and deployed statistics | Broader coverage is incomplete | Reuse local fixtures and verified results |
| Redundancy | 🟡 WAITING / PARTIAL | No qualified free execution provider | PinnWire RESEARCH_ONLY; PropLine FALLBACK; no false execution promotion | Capability and actual-response reports | Fallback has no usable quotes for this Football Day | Validate new responses in each eligible scan |
| Forward validation | 🟡 WAITING / PARTIAL | 10 / 4 / 0 settled | Minimum 150 retained; PAPER_RESEARCH_ONLY | Forward readiness and performance reports | Real future observations | Scheduled forward collection and exact settlement |
| O/U 2.5 | 🟢 GREEN | Integrity framework present | Exact 2.5/two-sided/prematch prices only; frequency N separate from priced N | Tests and actual deployed statistical groups | Small samples cannot establish an edge | Recompute on verified FT updates |
| Dashboard | 🟡 WAITING / PARTIAL | Overnight counts could reset; conflicts could reappear | Data guards deployed; counts aligned to Football Day | Deployed files and Node checks below | Interactive browser unavailable | Normal Pages deployment; browser QA when available |
| Workflow health | 🟢 GREEN for implemented recovery controls | Delayed scheduler could miss a collection slot | Bounded recovery and persisted attempt deduplication; data health stays separate | CI and actual collector/backfill runs | Scheduling precision and provider availability remain external | Automatic recovery check after each existing slot |

## Integrity and limitations

All four AH price buckets remain unchanged. “Price win” remains actual Asian Handicap settlement. Both quarantined AET result IDs are absent from canonical results and blocked against secondary-source reinsertion. The 84 legacy PropLine observations remain excluded; two additional post-kickoff observations are also quarantined. No odds, timestamps, fixture IDs, normal-time scores or forward observations were fabricated.

The cloud browser could not load the dashboard reliably. No rendered click/interaction testing is claimed. Actual deployed HTML, JavaScript and data are checked separately. No zero-cost provider is qualified for execution, and no current betting edge or production promotion is asserted.

## Actual final result recovery

Run **36747798445** collected one additional verified identity-bridge result, reduced its matured backlog **514 → 513**, used **3** FotMob requests and **9** cache hits, rejected **0** ambiguous matches, and retained **507** unmatched identities plus **6** exact-but-unfinished fixtures. No approximate kickoff-only match was accepted. Overall unresolved FT decreased **526 → 525**, settled fixtures increased **335 → 336**, and core-price settled fixtures **313 → 314**.

Raw snapshots remain **1,222**, verified **1,136**, quarantined **86** (84 legacy plus 2 post-kickoff). Recovered legacy remains **0**. Movement remains **110 fixtures / 652 numeric deltas**. Football Day 30 September has **36 valid observations / 1 distinct scan timestamp**. Forward candidates remain **10 / 4 / 0**, each requiring at least **150**. Two unsafe AET results remain separately quarantined.

No healthy execution provider is available: PinnWire is rate-limited, PropLine transport works but has no qualifying quotes for this Football Day, and OddsPapi reports **281/250**, remaining **0**. FotMob result retrieval is operational. Health remains **WAITING_EXTERNAL_DATA**, while data-integrity assertions pass.

## Deployment verification

Final Pages run **36748012253** completed successfully, publishing source `3e6555c9e4fc5a88f2168846ddb55b6e568208e2`. Downloaded live artifacts report audit schema **1.1**, Football Day **2026-09-30**, **336 settled / 314 core**, and passing data assertions. The newly executed collector run **36747940645** recorded **0 PinnWire requests** because the persisted cooldown remained active; its fresh report is present on the live site. No new live odds were invented to validate the overnight fix during cooldown. That collection path remains subject to the external provider becoming available.

Actual deployed JavaScript data guards passed under Node: **1,136 trusted snapshots**, **2 blocked FT result IDs**, and correct AH -1.5 settlement for a 1–0 FT score. All **82** O/U groups have over+under counts equal to N and priced N no greater than frequency N. See `reports/completion_verification.json` for machine-readable evidence.
