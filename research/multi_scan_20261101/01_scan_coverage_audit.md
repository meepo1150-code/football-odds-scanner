# Report 1 — Scan coverage audit

Pinned main `c75f7be2c87ea981487d0e4fb9b02a9e9f54dde8`. Actual-current-shaped input rows: 8800; historical recovery: 1602, kept separately. Clean current rows: 7083. Primary in-scope Pinnacle actual pre-match rows: 5137; same football day: 5137 across 1837 fixtures and 28 days, 98 league labels. Exact FT available: 1705. Date range: 2026-09-19–2026-10-31.

## Exclusions and denominator

| reason | rows |
| --- | --- |
| IDENTITY_UNRESOLVED_OR_CONFLICT | 25 |
| QUARANTINED_SOURCE_CONTRACT | 83 |
| AT_OR_AFTER_KICKOFF | 7 |
| HISTORICAL_RECOVERY_SEPARATE | 1602 |

All raw records are preserved. [coverage.csv](coverage.csv) breaks down fixture, slot, league, date, source and bookmaker. [exclusions.csv](exclusions.csv) has source row pointers. Master observations retain 1X2, both AH/OU sides, change time if present, actual observation time, flags and exact result source; master settlements expand the four sides using actual quarter-line settlement. Current league exclusions are flagged; not deleted. Retired/missing FT fixtures remain in coverage, not silently removed from denominators. Missing FT can bias settled ROI.

Raw receipts, provider caches, CSV archives and normalized mirrors are inventoried with SHA256. They are not independently added as new observations: parsing the same cache as a second observation would duplicate evidence. The versioned normalized scan files are the declared actual-scan population, not a claim that every past Actions artifact was retained. Unretained/deleted artifacts and pre-normalization missing scans cannot be recovered without new evidence. discovered_fixture_coverage.csv additionally enumerates the in-scope discovery universe with exact-ID current observation and FT flags. Discovery can occur after kickoff, so it is an audit denominator, not an ex-ante opportunity set. dashboard_audit.json reconciles dashboard source-population semantics; browser-rendered deployment was not re-certified. The daily-fixture discovery universe includes out-of-scope and unpriced fixtures; primary schedule coverage denominator is the union of observed in-scope fixtures, not all worldwide fixtures.

Historical tick audit is separate in historical_tick_audit.json; reconstructed AH slots are retained separately. FiveDollar opening/latest snapshots lack intra-day observation times and are unsuitable for schedule comparison. Current source sensitivity is in source_sensitivity.csv. No cross-provider names are fuzzy joined. Exact ID FT is inherited from existing verified result cache; external result provenance has not been independently re-certified. Conflicting identity/FT is quarantined. Repeated identical prices at distinct scan times remain valid observations; identical row/observation is deduplicated.

Current endpoint observations inherit the current active-market contract; this is evidence of polling time, not independent proof of execution availability. A quote unchanged for hours is not automatically stale. Missing source-change time/freshness receipt is a limitation, and no execution-ready EV is asserted. Post-kickoff or exactly-at-kickoff observations are excluded. Slots must meet nominal 15-minute completion SLA; actual times, not labels, determine availability.


EXPLORATORY — NO PROVEN EDGE. ROI is units per unit staked (0.01 = 1%). CLV N/A; latest observed price is not a certified close. See [protocol](PROTOCOL.md), [input inventory](data_inventory.csv), [statistical tests with Holm adjustment](statistical_tests.csv). No frozen promotion gate changed.
