# Report 1 — Scan coverage audit


EXPLORATORY / NO PROVEN EDGE. Flat stake 1 unit, price 1.80–2.20; AH contemporaneous favorite, OU Over. This benchmark is not a validated betting strategy. WR uses winning/losing stake fractions; pushes excluded. CLV unavailable: last observed quote is not a verified closing quote. All times Asia/Bangkok; football-day cutoff 05:00.

Retrospective discovered in-scope universe during study dates: 4610 IDs; 2773 have no current primary quote. Discovery is incomplete and includes post-event records; this is not the decision-time opportunity universe. See discovered_fixture_coverage.csv and daily_slot_coverage.csv for missing observations before outcome filtering.

|Cohort|Snapshots|Fixtures|With FT|
|---|---:|---:|---:|
|PRIMARY_PINNACLE_CURRENT|5137|1837|1817|
|ALL_ACCEPTED_SEPARATE_COHORTS|6638|2467|2335|

Historical recovery excluded from live analysis: 1602 rows / 685 IDs. Exact fixture-ID result join only; other provider cohorts are not pooled as independent fixtures.

Exclusions: `{"MISSING_TEAMS": 20, "SCOPE:YOUTH_OUT_OF_SCOPE": 124, "SCOPE:USER_APPROVED_FT_UNMATCHED_OUTSIDE_SELECTED_MASTER_SCOPE": 196, "SCOPE:WOMEN_OUT_OF_SCOPE": 93, "UNTRUSTED_SNAPSHOT": 83, "AT_OR_AFTER_KICKOFF": 7, "SCOPE:USER_REVIEWED_FIXTURE_OUT_OF_SCOPE": 18, "SCOPE:REVIEWED_LEAGUE_OUT_OF_SCOPE": 3, "INCONSISTENT_FIXTURE_IDENTITY": 5, "FUTURE_QUOTE_TIMESTAMP": 7, "SCOPE:USER_REVIEWED_COMPETITION_OUT_OF_SCOPE": 4, "HISTORICAL_RECOVERY_SEPARATE": 1602}`.

All committed data inventoried; historical git deletions and expired Actions artifacts not recovered; dashboard HTML returned HTTP 200 in separate verification; rendered UI and all deployed data not independently reconciled. Raw receipts retained: 21; current endpoint contract was inspected, but every raw market was not independently revalidated. Missing quote-change timestamps are explicitly flagged, never replaced with invented freshness. Scope removals are reported, not silently dropped.

See input_manifest.csv (all data hashes), master_research_dataset.csv (including excluded and historical rows), league_coverage.csv, scan_ledger.csv, exclusions.csv and 01_coverage.json. Archives, cached provider responses and result evidence are inventoried; existing normalized quotes are the analysis layer, not regenerated from all raw payloads.
