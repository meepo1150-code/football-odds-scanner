# Pilot result — BLOCKED / REVISE

Baseline: `2ff67333b5c65bd1d4ca24020750a7260f59201e`. Original research head: `ba8bd821341e35ece16e6b7b774b023df6da8b95`.

## Delivered result

10 exact-ID candidates across 9 football days and 10 competitions. 9 have one observed snapshot. 25 target slots lack observed snapshots; legacy targets are counterfactual as labelled. One fixture is FT_MISSING. No FT is invented.

**Actual requests: 0. Backfilled slots: 0. Real historical coverage: NOT TESTED, not zero coverage.** No observed/historical price comparison or live performance measurement was possible.

## Candidate manifest

| Fixture ID | League | Football day | Observed snapshots | Existing target slots | Missing targets | FT |
|---|---|---|---:|---:|---:|---|
| id1000062975208868 | Maltese Premier League | 2026-10-14 | 1 | 1 | 2 | VERIFIED_EXACT_ID |
| id1000009872735814 | TFF 1 Lig | 2026-10-13 | 1 | 1 | 1 | VERIFIED_EXACT_ID |
| id1000020274128332 | Ekstraklasa | 2026-10-12 | 1 | 1 | 3 | VERIFIED_EXACT_ID |
| id1000023872530942 | Liga Portugal | 2026-09-19 | 1 | 0 | 4 | VERIFIED_EXACT_ID |
| id1000002472341166 | League One | 2026-09-17 | 1 | 1 | 3 | VERIFIED_EXACT_ID |
| id1000000872478578 | LaLiga | 2026-09-16 | 1 | 1 | 3 | FT_MISSING |
| id1000021574374474 | Super League | 2026-09-15 | 1 | 1 | 2 | VERIFIED_EXACT_ID |
| id1000018274100008 | Ligue 2 | 2026-09-14 | 1 | 0 | 4 | VERIFIED_EXACT_ID |
| id1000003572513218 | Bundesliga | 2026-09-20 | 5 | 2 | 2 | VERIFIED_EXACT_ID |
| id1000018675178678 | Super League Greece 2 | 2026-10-14 | 1 | 1 | 1 | VERIFIED_EXACT_ID |

Full kickoff, teams, exact mapping confidence, target timestamps and withheld request objects are in `candidate_manifest.json`. FT status means conflict-free explicit scores in the pinned result store; this task did not independently refetch results.

## Offline statistics

Observed-only eligible target rows: 9 across 8 fixtures. FT-missing rows do not enter settlement counts. Extra legacy scan hours and unslotted observations are excluded.

| Water band | Side observations | Unique fixtures | Half-stake WR excluding pushes |
|---|---:|---:|---:|
| [1.80,1.90) | 6 | 5 | 40.0% |
| [1.90,2.00) | 6 | 3 | 50.0% |
| [2.00,2.10) | 4 | 4 | 60.0% |
| [2.10,2.20] | 0 | 0 | N/A |

BACKFILLED ONLY: no rows. COMBINED OFFLINE: unchanged from observed-only. Added independent fixtures: 0. Bands are left-closed/right-open except the last includes 2.20. WR uses win stake / (win stake + loss stake), with half wins/losses weighted 0.5. Full settlement categories and counts remain in pilot.json. These are selected missingness samples, not evidence of an edge.

## QA and safety

- 52 unittest cases passed: latest-state/suspension, timestamps, quarter lines, staleness, malformed data, same-time conflict, immutable raw bytes, symlink escape, exact mapping, FT conflicts, band boundaries, dedup, observed precedence, and synthetic end-to-end integration with networking disabled.
- 4 original production settlement test functions passed by direct execution (pytest is unavailable locally). No full-repository pytest or CI pass is claimed at preparation time.
- Actual pinned-data offline integration completed; every input Git blob identity matched baseline; SHA256 input values before/after are unchanged in pilot.json.
- AGENTS.md not found in either complete repository tree. Uploaded instructions read; their September state was treated as stale where current main differs.
- Original research branch: 10 commits ahead / 5 behind; research paths do not overlap main changes. Branch synchronization will use baseline main tree plus research-only paths, preserving both parents.
- No scheduler, collector, budget, ledger, recovery, fixture mapping, raw history, FT, statistics or dashboard changes are included.
- Read-only recent Actions: preparation-era watchdog, quota-health, validation health and dashboard deployment were successful. Workflow success is not proof of Scan Health PASS. Latest collector report at baseline: 18:20:12 Bangkok for 18:00 target. Live dashboard retrieval was unavailable through the web tool; no visual/live health claim is made.
- Evidence: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38726555310 (watchdog), https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38726444416 (quota health), https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38726633756 (dashboard deployment).

## Expansion decision

**REVISE; live pilot BLOCKED. Do not expand to 50–100.** Benefit of current work: deterministic, reviewable preparation with no production quota/data impact. Trade-off: no real historical recovery or coverage proof yet. Main risks: historical active/time semantics, incomplete ticks, provisional one-hour staleness, exact catalog/entitlement verification, and correlated/selection-biased samples.

The provider must clarify historical state semantics and the execution environment must support isolated, authorized credentials and a quiet request window. Then run only the ten prepared requests, with a live account check, cache-first behavior, 5.2-second spacing, no retries and stop-on-429. Request-count billing documentation is verified, but actual measured cost/latency and production impact cannot be extrapolated before a real pilot. No production integration merge/deploy is authorized in this task.

Full-suite CI initially exposed stdlib statistics name shadowing. Renamed the research module to offline_stats.py and added a subprocess import regression. No production code was changed.
