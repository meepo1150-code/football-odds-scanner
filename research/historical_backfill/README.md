# Historical Backfill — isolated research track

Status: RESEARCH ONLY; not enabled in production.
Branch: research/historical-backfill-isolated-20261015

## Non-negotiable boundaries
- Never call OddsPapi, including its historical endpoint.
- Never modify production collector, scheduler, quota ledger, fixture mapping, raw history, dashboard, or deployed workflows in this track.
- No scheduled workflows, secrets, provider credentials, or network requests until an independent free data source is verified.
- No writes to existing normalized production files.
- Separate raw historical imports from live-captured snapshots. No promotion into unified statistics without a review gate.

## Provider qualification gate
Document license/automated-use permission, free-tier history access, request limits, historical depth, supported leagues, bookmaker identity, AH line and BOTH prices, source quote timestamps, kickoff, and missing-data behavior.
Test samples across 7, 30, 90 and 180 days, multiple leagues and fixtures. Count complete, partial, missing, stale, and ambiguous snapshots. Do not confuse closing-only data with intraday ticks.
No provider is approved yet.

## Canonical data contract (proposed)
fixture_source_id, source, bookmaker, league_source_id, home_source_id, away_source_id, kickoff_utc,
market_type, ah_home_line, selection, decimal_price, quote_at_utc, imported_at_utc,
requested_slot_bangkok, source_record_id, raw_record_hash, provenance=HISTORICAL_RECONSTRUCTED,
quality_status.

AH lines must be exact 0.25 increments. Preserve both selection prices with independently
recorded quote times. For each requested slot select only the latest quote with quote_at <= slot,
and slot < kickoff; reject stale quotes using an explicit maximum age selected after sampling.
Never use post-kickoff ticks or fill gaps with fabricated/interpolated odds.

## Data integrity
- Raw immutable imports, normalized output and QA reports live under a separate historical namespace.
- Deduplicate on source fixture + bookmaker + market + line + selection + quote timestamp + source id/hash.
- Resolve to master IDs only with auditable exact evidence; unresolved matches remain excluded.
- Fixture count and independent FT outcomes are separate from snapshot counts.
- FT settlement uses existing tested Asian settlement functions without changing production code.
- Never combine bookmaker prices blindly; keep separate league, source, bookmaker and era diagnostics.
- Train/validation/holdout must be chronological and prevent look-ahead and duplicate fixture leakage.

## Work sequence
1. Read-only audit of current main and approved league registry.
2. Independent free-source licensing and API capability research.
3. Offline fixture/tick samples and adapter tests on this branch.
4. 7–30-day backfill dry-run with QA, zero production writes.
5. Review coverage, timestamp integrity, quota and licensing; only then propose integration.
6. Separate PR and explicit QA gate before any statistics merge.

## Abort conditions
No legally reusable free timestamped AH history; provider cannot prove both sides and times;
inadequate coverage; any risk to production quota or scheduled scanning.
