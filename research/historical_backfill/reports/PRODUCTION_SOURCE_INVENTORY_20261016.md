# Production source inventory and historical slot policy — initial verified audit (2026-10-16)

Read-only audit of `main` source files; no provider calls or production writes.

## Authoritative code paths
- `src/odds_scanner/research_v2_slots.py` defines historically versioned `targets(day)`: before 2026-10-12 weekdays 18,21 and weekends 12,15,18,19,20,21,22; 2026-10-12 weekdays 18,21; from 2026-10-13 daily 15,18,21 plus 00:00 following football day. Verify the exact historical commit for every older date; current code constants are not sufficient proof of when each rule was actually deployed.
- `src/odds_scanner/daily_scan_cohort.py`: fixed 15:00 fixture cohort `EFFECTIVE_DAY=2026-10-14`; requires successful 15:00 receipt with `coverage_tournament_ids` and a prior raw `/fixtures` response; **returns None rather than guessing**.
- `src/odds_scanner/master_schedule_plan.py`: append-only raw fixture responses in `data/normalized/research_v2_provider_responses.jsonl`; fixture IDs and kickoff are sourced from `fixtureId` and `startTime`, not fuzzy team-name matching.
- `src/odds_scanner/research_v2_slots.py` validates fixture-level AH snapshots from `data/normalized/europe_pinnacle_research_v2_snapshots.jsonl`, using `scheduled_target_at`, `observed_at`, `kickoff` and AH prices. `research_v2_slot_ledger.jsonl` is round-level only.
- `docs/four-slot-collector-2026-10-14.md` documents the four canonical target times, quota and recovery constraints. GitHub scheduled invocation is not guaranteed on time.

## Data access observations
- `research_v2_slot_ledger.jsonl`: 97 parsed records, 74 unique scheduled target instants in previous audit.
- `v2_mainline_snapshots.jsonl`: 555 rows in previous audit; not equivalent to full canonical collector snapshot archive.
- `five_dollar_snapshots.jsonl`: 297 rows; different fixture namespace, opening/closing only, no ticks.
- `europe_pinnacle_research_v2_snapshots.jsonl`: connected fetch returned empty; cannot infer that no production snapshots exist across archived artifacts, reports, or other stores.
- `research_v2_daily_fixtures.jsonl`: connected fetch returned empty; authoritative fixture inventory must be reconstructed from immutable `/fixtures` responses and persisted 15:00 cohorts, not this file alone.
- `oddspapi_history_ticks.jsonl` and its shards exist, but these may represent different date scopes and are not automatically equivalent to observed 15/18/21/00 slots.

## Blocking next verification
Pin exact production SHA and historical deployment intervals; inspect schema and date coverage of raw provider responses, persisted collector reports and history tick shards; establish which files are complete or partial. Build canonical fixture×expected-slot table **only for provable cohort membership**, marking uncertain membership UNKNOWN. Then join exact observed snapshot records; do not infer missing scans from round-level receipts or 5dollar source.

**No request queue is authorized yet.**
