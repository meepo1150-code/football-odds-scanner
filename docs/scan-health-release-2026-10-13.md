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
