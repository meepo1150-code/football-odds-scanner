# Historical AH Staging / Integration Dry Run — Execution Contract

Status: RESEARCH ONLY; no production promotion authorized.
Base: research/historical-backfill-isolated-20261015.
Source report: research/historical_backfill/reports/CONTROLLED_EXPANSION_20261016.json.

## Immutable input and admission
- Preserve all 1,176 complete two-sided all-line historical records and their original response hashes/receipts in isolated research storage. These are not 1,176 unique scan slots.
- The only preliminary promotion candidates are 129 BALANCED_LINE representatives over 73 fixtures, from 235 target fixture-slots. Quarantine 106 MAINLINE_UNRESOLVED slots. Recompute and validate from raw receipts; never trust summary counts as row-level evidence.
- Retain exact canonical fixture ID, bookmaker, reviewed market/outcome IDs, signed AH quarter line, home/away decimal odds, active state, actual home and away quote timestamps, requested target slot, retrieval time, and immutable source hash. Explicit origin=HISTORICAL_BACKFILL; never OBSERVED_LIVE.
- Quote timestamp must be <= target, < kickoff, age <= 3600 seconds; odds on both sides in [1.80,2.20]. Reject unresolved, missing, conflicting, stale, inactive, mismatched or fabricated data.

## Production reconciliation (read-only)
- Load the actual production slot ledger and fixture identity/quarantine data at a pinned commit. Never assume 235 slots are actual missed scans.
- For each candidate, label exactly one: MISSING_EXISTING_FIXTURE_SLOT, DUPLICATE_OBSERVED_SLOT, NO_PRIOR_OBSERVED_FIXTURE, AMBIGUOUS_IDENTITY, FT_UNAVAILABLE_OR_CONFLICTED, OTHER_REJECTED. Include reason and original evidence.
- Never replace or rewrite observed prices, raw historical files, quote timestamps or settlement history. Use a deterministic idempotency key (fixture, target slot, bookmaker, market, line, source hash).
- Only classify genuine missing slots as potential statistical additions after validating FT identity, kickoff, and Asian Handicap quarter-line settlement (win, half-win, push, half-loss, loss). Keep observed-only and observed+backfilled metrics side by side; never silently pool sources.

## Required deliverables and gates
1. Reproducible offline staging loader and row-level validation/rejection ledger.
2. Fixture-by-fixture production reconciliation using read-only snapshots of actual main.
3. Deterministic, reversible before/after dry-run report: counts by classification, league, bookmaker, scan slot, AH settlement and FT availability; source-specific denominators.
4. Regression tests for duplicate slot, idempotency, conflicting identity/FT, sign inversion, quarter-lines, timestamp freshness and preservation of existing snapshots.
5. Run tests and CI, publish exact artifact/commit/run links. Mark NOT VERIFIED if actual production evidence is unavailable; never invent a pass.
6. NO API requests, workflow schedule, merge, deploy, dashboard changes, or production writes. Require separate approval before any promotion.

User authorization: isolated staging and dry-run only.
