# Canonical schedule and FT integrity release

The forward collector still had seven weekend canonical times, and its primary timing helper added weekday midnight targets that the recovery gate did not recognize. The schedule is now one versioned source: football days from 2026-10-12 use Monday–Friday 18:00/21:00 and Saturday–Sunday 15:00/18:00/21:00 plus midnight immediately after that day. This gives 18 weekly slots. Earlier football days retain the seven-slot legacy weekend interpretation; archives are unchanged.

The main scanner, primary collector heartbeat, scheduled recovery and independent watchdog use matching UTC cron definitions. Midnight after Saturday/Sunday remains recoverable against the previous football day for 150 minutes. Recovery requires real persisted quotes or a successful empty response receipt; missed historical prices are never recreated. Shared collector concurrency and successful-slot deduplication remain in force.

The six-request UTC-day cap previously allowed three two-request weekend attempts to consume the whole budget before a fourth slot. New weekend days use one batch of five tournaments per attempt, retaining the same cohort throughout the UTC day. Weekdays retain two batches. Failed attempts still consume the cap; the shared account and 180/month research limits are unchanged. This deliberately trades coverage breadth for repeated observations and budget for midnight; it does not guarantee free-provider health or full-market coverage.

An empty rotating-cohort response is now recorded as `ZERO_COHORT`, not evidence that the whole football day has zero fixtures. It blocks duplicate requests after a successful cohort collection while the operational audit reports `DEGRADED_SCOPE`. Historical receipts are retained.

Match statistics now order timezone-aware observations chronologically, reject malformed/two-sided-invalid and at/after-kickoff quotes, and select the latest valid pre-match quote per identity group. A four-round fixture counts once. Unlinked cross-provider IDs remain disclosed; no fuzzy merge was introduced. WR explicitly means a positive settlement event (FULL_WIN or HALF_WIN) over all settled outcomes including PUSH; the five settlement counts and actual profit/ROI remain separate.

The old FT completeness value was hard-coded to 100% over a verified subset. The total metric now includes retired and conflicted unresolved identity groups. Conflicts and verified non-FT lifecycle states are disclosed. Retirement remains an active-queue decision, not settlement proof.

## Verified web recovery

- Marine FC–Warrington Town, 2026-10-03 14:00 UTC: 2–0, confirmed by the official Warrington Town match report. Marine's official draw announcement confirms FA Cup third qualifying round and 15:00 Europe/London (=14:00 UTC). Per-source assertions and identity support are stored, and the existing conservative importer added exactly one result.
- Levante UD–Athletic Bilbao, original 2026-09-16 fixture: official Athletic Club postponement notice confirms POSTPONED. A separate exact-identity lifecycle receipt records the status; no FT or ROI is invented and no historical quote is transferred to a rescheduled kickoff.

## Validation and remaining production gaps

520 offline tests passed on the release code, including quarter-lines, provider timeout/429, result conflict quarantine, new schedule conversion, midnight deduplication/expiration, price boundaries, browser JavaScript guards and raw-preservation tests. Protected pattern registry and raw Research V2 snapshot/audit files are byte-identical to the release baseline. There were zero odds/API requests for these tests and one result added from manual web evidence.

Rebuild: 783 settled / 1,031 eligible identity groups = 75.95% FT completeness; 248 groups still lack a verified result, including one known postponed fixture and two result conflicts. Their raw data remain intact. Last saved weekday observation at 19:35:55 Bangkok recovered 18:00 with 95.93 minutes lag, no in-day quotes, and only a rotating cohort. This is not an on-time or full-scope pass.

Master allowlist migration remains separate: PR #324 is documentation-only, and verified competition mappings currently exist only for OddsPapi. Unmapped PropLine/other producer coverage must not be called certified or silently mapped by similar names. The reviewed historical exclusion policy is unchanged by this release. New weekend live behavior and actual dashboard browser verification remain open; the remote browser timed out, local Chromium is absent, and direct Pages access failed. CI/deploy and final production certification must be checked separately from offline tests.

No frozen validation gates were changed. Movement remains `NO_VALIDATED_INCREMENTAL_MOVEMENT_EDGE`; no picks or edge claims were forced. See `reports/final_production_audit_2026_10_12.json` for per-gate evidence.
