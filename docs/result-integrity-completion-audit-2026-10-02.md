# Completion audit — 2026-10-02 07:05 Asia/Bangkok

Scope: continue pending-result UI verification and repair the remaining API-Football result path. This is an honest operational checkpoint; external provider coverage and future samples remain incomplete.

## Shipped and verified
- PR #236: clear pending/overdue/conflict labels, remove user-facing UNCLASSIFIED, prevent conflict-ledger donors/targets from local result reuse.
- PR #237: explicit suspended account cooldown (24 hours, fixed boundary on skipped runs), stop request sequence immediately after suspension, skip targeted backfill, regulation-time FT only with integer nonnegative scores, both-team deterministic identity and exact kickoff.
- API-Football persistence now merges canonical results with conflict handling on fresh main and rebuilds statistics; it no longer overwrites independently collected odds snapshots.
- 347 local tests passed. PR CI 36943750431 and main CI 36943899322 succeeded.
- Real API-Football run 36943899170: both collection and targeted backfill ACCOUNT_SUSPENDED, requests_used=0. Retry boundary 2026-10-02T17:29:24.479897+00:00. This is an application retry boundary, not a promised account restoration time.
- Cached API-Football AET/PEN rows: 18. None of their provider fixture IDs was referenced by the canonical result store during this audit. They remain raw evidence but are excluded by the stricter consumer.
- Latest free backfill 36943899431: two more FotMob matches recovered using eight cache hits and zero FotMob requests. ESPN added zero this rerun. Earlier overnight run added 43 FotMob and 2 ESPN source identities; do not equate source IDs to distinct statistical fixtures.
- Live deployment 36943989115, source 835271cbf797236036dd102b08799ea937d1cac9. Downloaded public deployment manifest and operational report agree with this source.

## Final matrix

| Component | Status | Before | After | Evidence | Remaining blocker | Next automatic action |
|---|---|---|---|---|---|---|
| Legacy PropLine | 🟡 WAITING / PARTIAL | 84 unreliable legacy quotes | 0 recovered; all 84 remain quarantined | legacy_propline_recovery.json; quarantine assertions | Verified historical Pinnacle mainline evidence unavailable | Revalidate staged recovery evidence during rebuild |
| PinnWire | 🟡 WAITING / PARTIAL | HTTP 429 | Controlled cooldown, honest RATE_LIMITED health; PropLine fallback | operational audit/provider reports | External provider availability; limited fallback coverage | Bounded attempt at next eligible scan slot |
| OddsPapi budget | 🟢 GREEN | Previously exhausted 279/250 | Latest observed 7 used, 243 remaining of 250; budget safeguards preserved | oddspapi_quota_health.json at 2026-10-01T22:37Z | Current execution qualification is separate | Scheduled quota check and budgeted calls |
| FT recovery | 🟡 WAITING / PARTIAL | 352 settled, 584 canonical unresolved at previous checkpoint | 392 settled, 544 unresolved | Deployed audit and AH table | 102 active overdue, 3 future/recent, 439 archived unresolved | Free backfill schedule and cache reuse |
| Daily sync | 🟢 GREEN | Old exhausted-provider dependency | Local fixture coverage sync and multi-source free results run successfully | Free backfill 36943899431 and deployed statistics | Complete coverage remains partial | Next scheduled free backfill |
| Provider redundancy | 🟡 WAITING / PARTIAL | No qualified zero-cost execution provider | PropLine FALLBACK; FotMob/ESPN result recovery working; API-Football safely suspended | Actual provider outputs | No current execution-ready provider proven | Collect evidence; never auto-promote from documentation |
| Forward validation | 🟡 WAITING / PARTIAL | Samples 10/4/0 | 10/4/0; PAPER_RESEARCH_ONLY; minimum 150 unchanged | operational audit/forward reports | Real future settled observations | Continue forward entry/result collection |
| O/U 2.5 | 🟢 GREEN | Existing exact-line framework | Preserved; browser shows outcome N and separate priced N for ROI | 347-test suite and deployed O/U table | Small samples limit inference | Rebuild on verified results |
| Dashboard | 🟢 GREEN | Generic FT pending and UNCLASSIFIED | Explicit result-state labels, filters, 392 settled/369 core displayed | Live browser verification below; deployment manifest | Unverified matches intentionally remain pending | Deploy after result/scan workflows |
| Workflow integrity | 🟢 GREEN (repaired scope) | Suspended calls repeated; stale canonical/odds overwrite risk in API-Football workflow | Zero-call cooldown; conflict-aware result merge; fresh statistics; no odds overwrite | Actual runner, reports, regression tests | Cron punctuality and external source uptime cannot be guaranteed | Existing result and scan schedules |

## Actual output counts
- Raw snapshots: 1,312.
- Verified snapshots: 1,226.
- Quarantined: 86 (84 legacy and 2 other rejected observations).
- Recovered legacy odds snapshots: 0.
- Unresolved canonical FT fixtures: 544 = 439 archived + 102 active overdue + 3 future/recent.
- Settled statistical fixtures: 392; core-price settled fixtures: 369.
- Movement: 117 fixtures, 684 numeric deltas.
- October 2 valid scans at this early-morning audit: 0; weekday scan slots have not occurred.
- October 1: 90 raw scan observations, 76 canonical fixture groups, 83 provider IDs.
- Forward candidate sample sizes: 10, 4, 0.
- Provider state: PropLine AVAILABLE/FALLBACK at its latest quote fetch; FotMob/ESPN results usable; PinnWire RATE_LIMITED; API-Football ACCOUNT_SUSPENDED. Availability observations are timestamped, not guarantees of current live odds.
- Latest observed OddsPapi quota: 243/250 remaining.

## Browser checks and limits
Directly interacted with the deployed dashboard:
- Confirmed-results filter shows recovered FT and Asian Handicap results.
- Juve Stabia vs Palmese: FT 4–1 with selected AH −3 displays push (เสมอราคา), not an FT-winner substitute.
- Overdue filter shows unverified overdue fixtures.
- AH table N header sorts descending (23, 17, ... at the checked view).
- O/U 2.5 percentages include count fractions and separate O/U priced N.
- Final reload displays 392 settled, 369 core, 1,226 clean, 86 quarantined and 105 active pending.
The automatically generated audit's dashboard_browser_verified=false has not been falsely switched to true: these are scoped manual checks recorded here, not a continuously automated browser test.
Movement values were verified in deployed data; no separate movement-browser interaction was claimed.

## Trade-offs
Strict FT and two-team/exact-time guards can leave additional matches unresolved; this protects settlement integrity. A 24-hour suspension cooldown reduces pointless calls but can delay recognition of account restoration. Archived failures remain preserved and excluded, rather than deleted or assigned invented results. No forward thresholds, quarantine protections or production promotion gates were weakened.
