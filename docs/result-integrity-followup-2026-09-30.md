# Research V2 completion audit — 30 September 2026, evening Bangkok

PRs #229 and #230 are merged. The full suite passes **319 tests**. Research and independent-confirmation CI passed before the final merge. No production promotion is allowed: **PAPER_RESEARCH_ONLY**.

## Actual corrections and output

Original FotMob responses proved that FC Osaka–Avispa Fukuoka (event 6189150, canonical `pinnwire:1637178704`) and Sagan Tosu–Tokyo Verdy (6217283, `pinnwire:1637183976`) had after-extra-time scores stored as normal FT. Both complete original records and source evidence are retained in `data/normalized/oddspapi_finished_results.conflicts.jsonl`. No normal-time score was inferred. Statistics and dashboard both exclude ledger IDs, including if another result file supplies them again.

FotMob responses now persist with retrieval provenance and conservative cache lifetimes (recent dates 1 hour; older dates 24 hours). The real local repeat changed 12 network requests to 0 with 12 cache hits. Scheduled GitHub run **36723646840** subsequently used 3 requests plus 9 cache hits and recovered **3 verified identity-bridge results**, reducing that run's matured backlog **508 → 505**. Existing raw cached responses survived checkout and workflow persistence. Earlier correction temporarily reduced settled counts 334 → 332; subsequent real results brought them to **335**, core-price **313**. Historical corrections may be delayed by the cache TTL; stale fallback is explicitly labelled.

PR #230 adds a push-token recovery trigger to the serialized collector and deploys Pages for conflict-ledger-only changes. It adds no repeated provider probe. Actual recovery run **36731047781** succeeded as a workflow but PinnWire returned **HTTP 429**, with cooldown until **2026-09-30T23:59:59.748532Z** (approximately 07:00 Bangkok on 1 October). The validated PropLine fallback returned 195 source rows but **zero usable current-Football-Day rows**. Therefore collection health is **WAITING_EXTERNAL_DATA**, not GREEN.

## Final matrix

| Component | Status | Before | After | Evidence | Remaining blocker | Next automatic action |
|---|---|---|---|---|---|---|
| Legacy PropLine | 🟡 WAITING / PARTIAL | 84 unreliable observations | 0 recovered; all 84 quarantined, per-record reasons retained | legacy_propline_recovery.json | Verified historical Pinnacle odds unavailable | Recheck archives on rebuild; promote only verified recovery |
| PinnWire | 🟡 WAITING / PARTIAL | Previous 429; morning availability | Live 429 confirmed; provider cooldown persisted; no retry storm | Run 36731047781; provider status report | Provider rate limit | Next scheduled collector respects cooldown, then retries once |
| OddsPapi | 🟡 WAITING / PARTIAL | Quota exhausted | 281/250, remaining 0; metered paths fail closed | Unmetered account report at 12:26 UTC | External monthly quota | Scheduled account check must prove reset before metered calls |
| FT recovery | 🟡 WAITING / PARTIAL | 2 AET scores incorrectly counted; missing results | 2 results quarantined; later 3 verified results added; 526 unresolved total, 505 matured | Conflict ledger; FotMob report; statistics | 499 no exact identity and 6 exact-but-unfinished in FotMob pass | Scheduled free-source backfill and cache reuse |
| Daily result sync | 🟢 GREEN | Exhausted-provider dependency | Local coverage preserved; free results collected; statistics rebuilt and published | Run 36723646840; LOCAL_FIXTURE_COVERAGE_SYNCED | Broader discovery and unresolved identities remain partial | Four daily free-result runs |
| Provider redundancy | 🟡 WAITING / PARTIAL | No qualified free execution provider | PinnWire RESEARCH_ONLY; PropLine FALLBACK with current-day coverage gap | Live responses and capability reports | No execution-ready provider with current verified evidence | Validate actual quotes at each collection; never promote on documentation |
| Forward validation | 🟡 WAITING / PARTIAL | Samples 10 / 4 / 0 | Still 10 / 4 / 0; minimum 150 unchanged | v2_forward_readiness.json | Future settled observations | Scheduled entry, result, CLV and performance collection |
| O/U 2.5 | 🟢 GREEN | Integrity protections implemented | Exact 2.5/two-sided/prematch/provenance policy retained; percentages carry N | 319 tests; deployed statistics and JS | Sample size limits inference | Rebuild on new verified observations/results |
| Dashboard data | 🟢 GREEN | Result conflicts could reappear through another file | Deployed JS consumes conflict ledger; actual data excludes both blocked scores | Pages run 36731124536; downloaded JS/data checks | Browser interaction not verified | Deploy after collection, backfill and conflict-only changes |
| Dashboard interaction | 🟡 WAITING / PARTIAL | Browser unavailable | Pure JS tested; no claim of rendered click testing | Cloud browser navigation hung and was aborted | Browser responsiveness | Retest dates, filters and header clicks when browser works |
| Workflow health | 🟡 WAITING / PARTIAL | Evening scheduled collector absent from observed runs | Recovery trigger tested; data assertions pass; provider failure accurately visible | PR #230 and run 36731047781 | Scheduler delivery and provider availability are not guaranteed | Existing weekday/weekend schedules; explicit recovery trigger available |

## Final counts

| Metric | Actual output |
|---|---:|
| Raw snapshots | 1,222 |
| Verified/usable snapshots | 1,136 |
| Quarantined snapshots | 86: 84 legacy plus 2 post-kickoff observations |
| Recovered legacy snapshots | 0 |
| Separately quarantined FT results | 2 AET results; not part of the 86 snapshot count |
| Unresolved FT fixtures | 526: 505 matured plus 21 future/recent |
| Settled statistical fixtures | 335 |
| Core-price settled fixtures | 313 |
| Movement fixtures / numeric deltas | 110 / 652 |
| Current-day valid observations / distinct scan timestamps | 36 / 1 |
| Forward settled samples | 10 / 4 / 0 |

PinnWire is rate-limited. PropLine transport is available but has zero usable rows for today. FotMob result collection works with persisted caches. OddsPapi is quota-blocked. No provider is represented as execution-ready. Latest Pages deployment is run **36731124536**; actual published status must remain WAITING_EXTERNAL_DATA despite the successful deployment.

The HTML/data were downloaded from the deployed GitHub Pages URL, and its actual JavaScript data guards were executed with Node. Raw/trusted counts were 1,222/1,136 and both blocked result IDs stayed excluded even under attempted reinsertion. This is artifact/function verification, not a browser interaction test.
