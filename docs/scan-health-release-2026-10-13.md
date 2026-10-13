# Immutable Scan Health and production verification

Daily Preparation Scan already runs at 15:00 Asia/Bangkok on main (effective October 13). Existing weekday 18:00/21:00 and weekend 18:00/21:00 plus 00:00 after the football day remain. Weekend 15:00 shares the canonical slot and lock; no duplicate market request is needed. Recovery heartbeats use the same completed-slot gate and 150-minute window.

The primary collector retains a complete provider schedule response when available and plans all 92 approved competition mappings by exact IDs. It preserves per-competition fixture IDs even when requests cannot cover all markets. Its rolling day follows the existing football-day definition (12:00 through next 06:00 Bangkok). A provider schedule is evidence of provider coverage, not independent proof of all real-world fixtures. Cached schedule evidence is reused for 18 hours. Missing historical prices are not reconstructed.

New outputs:

- `data/normalized/scan_health_history.jsonl`: immutable per-provider reports and separate control checks; includes source observation time, target, count semantics, coverage, API error counts and GitHub Actions run URL for future runtime records.
- `reports/scan_health_latest.json`: latest actual scan separately from subsequent deduplication/cooldown checks; recent 30 reports and full archive pointer.
- `reports/scan_health_monitor.json`: current missing-slot evidence, overdue unresolved FT including approved retired conflicts, separate postponed lifecycle count and rejected identity bridge candidates.

Counts are distinct fixtures, with valid quotes required to pass strict pre-match, verified mapping and exact AH core price 1.80–2.20. Missing schedule evidence is UNKNOWN, never zero. Unqueried fixtures are not confirmed absent markets. Exceptions are reduced to counts; new public health history does not retain credential-bearing exception text. A rejected cross-provider bridge is not itself a missing FT. Known postponed/cancelled/abandoned fixtures are separate from FT delay. Raw records, approved unresolved fixtures, result conflicts and frozen research gates are retained.

The initial three receipts are explicitly `IMPORTED_EXISTING_REPORT`; they retain their old observation times and do not claim a new live scan. The latest October 12 primary receipt found 44 approved scheduled fixtures, of which 9 had valid core quotes in this attempt; 18 unqueried competitions remained. Two other strict research quotes were outside core odds. WARNING is appropriate, despite a successful Actions job.

All collector persistence workflows stage and union the health archive against current main before rebuilding derived reports. Scan Health Monitor refreshes hourly at :05 UTC (= :05 Bangkok), after relevant collection workflows, and on explicit control-token runs. It uses zero provider calls, saves both JSON reports in GitHub, publishes an Actions summary and a named artifact, and fails its check on data-health FAIL. Workflow success and health status remain distinct. Pages publishes the same reports/history and renders them in System Monitor.

Validation: 572 pytest tests and 27 Master unittest checks passed; offline Master QA reports 50 associations / 81 divisions / 1,203 active clubs / 92 mapped competitions, with zero mapping errors. JavaScript syntax passes. Live deployment and Actions proof are recorded separately after merge. An on-time 15:00 October 13 run cannot be certified before that future slot occurs.

Free-tier trade-off: unchanged 6 research requests per UTC day / 180 per month, account reserve and slot deduplication. Broad schedule preparation does not guarantee odds for every approved competition within this allowance. API-Football account suspension and unavailable verified fallback mapping remain disclosed external/source blockers.

## Completed runtime and deployed verification

PR #336 merged as 373fdec80142f8246f06653a6c8882f698df1057 after all four CI checks succeeded.

- Daily Preparation: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38338275097 — success. FT recovery report at 02:44:42 UTC: zero new recoveries, three retained unresolved queue items, six public requests, zero odds requests, errors empty. First-odds job correctly skipped collection before the future 15:00 slot.
- Quota: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38338270991 — success. Account observation at 02:44:02 UTC: 157/250 used, 93 remaining.
- Health: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38338274861 — success. Artifact `scan-health-38338274861-1` exists; health status is WARNING, separate from workflow conclusion.
- Final Pages: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38338398224 — success, including Build, Upload and Deploy steps.

Live browser verification after this deployment showed the updated preparation timestamp, Scan Health history and latest receipt ID cf24c2b389a8e905d97e39a8668647702f6e332a9cb00ccfd0c2cf730fa60df6. The actual latest odds observation remains October 12 at 22:31 Bangkok; today 15:00/18:00/21:00 are explicitly UPCOMING. The old odds report was imported with its original timestamp, not turned into new evidence. The browser also verified twelve October 12 match cards, FT scores, r1/r2 histories, WR, Over 2.5 and half-settlement rendering.

Audit classification: 12 criteria, 8 PASS / 4 WARNING / 0 implementation FAIL. Warnings are provider readiness (suspended API-Football and unavailable verified fallback), partial market coverage under quota, retained FT conflict/postponement and rejected identity bridge candidates. FT statistics: 843 settled groups, 99.76% completeness; one identity conflict and one postponed fixture. The recovery queue additionally retains one derivative market excluded from FT statistics. The 43 rejected bridge candidates must not be interpreted as 43 missing scores.

This certifies deployment and tested configuration; the first actual scheduled 15:00 October 13 collection remains a future runtime check. Hourly monitor :05 and free FT recovery :15 continue without changing the canonical scan slots or paid API limits. Machine-readable completion evidence: `reports/scan_health_release_verification_2026_10_13.json`.
