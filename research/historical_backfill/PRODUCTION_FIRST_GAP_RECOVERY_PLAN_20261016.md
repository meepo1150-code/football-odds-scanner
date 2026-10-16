# Production-first Historical Gap Recovery — execution plan (2026-10-16)

## Goal
Enumerate **all actual production fixtures and their scheduled pre-kickoff scan slots**, reconcile with all observed collector snapshots, then request historical odds **only** for verified missing AH-price slots. The earlier 129 BALANCED_LINE selections are cache candidates, not a recovery target or import authorization.

## Phase 0: Freeze source and semantics
Pin main SHA and immutable checksums of every source. Read AGENTS.md, active scheduler, 15:00 fixture-set persistence, 00:00 cross-day policy, collector outputs, snapshot schemas, slot ledger, kickoff revisions, FT/lifecycle records, and provider quota contracts. Inventory sources with scope, date coverage, fixture-ID namespace, observation timestamp meaning, and completeness. Never interpret a round-level ledger as fixture-level proof.

## Phase 1: Canonical fixture inventory
Create one record per canonical fixture/event with provider ID mapping evidence, league, teams, original/current kickoff in UTC, football day Asia/Bangkok, lifecycle status, reschedule lineage, and 15:00 fixture-set membership. Include every production-covered date, not only historical research's 100 fixtures. Quarantine identity conflicts.

## Phase 2: Expected slot matrix
Reconstruct *actual production policy for that historical date* (not retroactively impose today's rules): scheduled 00:00/15:00/18:00/21:00 Asia/Bangkok, fixed 15:00 daily fixture set where applicable, kickoff cutoff, fixtures added/removed, and UTC day transitions. Explicitly record whether each fixture-slot was expected, not expected, or unknown, with reason and policy version. Examples: 19:00 local kickoff generally 15:00+18:00; 23:00 generally 15:00+18:00+21:00. 00:00 and postponed/rescheduled fixtures need policy-specific treatment.

## Phase 3: Observed matrix and classification
Join exact canonical fixture ID + scheduled slot ID + bookmaker + market + actual observed quote metadata across ALL production collector stores and raw append-only history. Count both attempted scans and complete two-sided AH prices. Classify COMPLETE, NO_PRICE, SCAN_FAILED, MISSING_SLOT, UNMATCHED, POSTPONED, CANCELLED, ABANDONED, NOT_EXPECTED, UNKNOWN_EVIDENCE. No historical provider requests yet. Missing is established only when expected membership and source completeness are proven.

## Phase 4: Recovery manifest and quota gate
Generate deterministic, sorted, immutable manifest with canonical ID, provider mapping, target slot UTC, kickoff UTC, missing evidence, required bookmaker/market, priority, raw hashes and exclusion reason. Exclude ambiguous/rescheduled/no-proof items. Deduplicate across research cache and existing production rows. Report count of fixtures, expected slots, complete slots, incomplete slots, confirmed recoverable slots, unknown slots, and projected requests/cooldown. Check provider entitlement, UTC daily/monthly quotas and production health.

## Phase 5: Cache-first isolated recovery
Use historical cache first; call historical endpoint ONLY for manifest-listed gaps with exact mapped IDs, pacing, budget and resumable checkpoints. Save immutable raw response and provider timestamps; do not fabricate a scan at target time. Keep all AH lines, select representative BALANCED_LINE only when both prices active and 1.80–2.20; otherwise MAINLINE_UNRESOLVED.

## Phase 6: Quality/settlement gates
Check market catalog and home/away sign, quarter-lines, quotes <= target and < kickoff with freshness threshold, raw hashes, lifecycle/FT exact-ID status and settlement (FULL/HALF WIN/LOSS, PUSH). Postponed Levante–Athletic Sep 16 must not be settled from missing FT; independently verify reschedule before updating lifecycle.

## Phase 7: Deterministic read-only dry-run
Produce before/after counts split OBSERVED vs HISTORICAL_RECONSTRUCTED; duplicate detection and idempotency (run twice, zero new rows second time); effects on AH outcomes and dashboard stats; list every excluded row and why. No overwriting raw history or changing scan success rates.

## Phase 8: Controlled production promotion (separate approval)
Only after manifest evidence, tests, CI and dry-run pass, request explicit authorization for a production import PR. Append-only import, transaction safety, rollback, post-import audit and dashboard verification. **This planning commit does not authorize a production write.**

## Immediate implementation milestones
1. Source inventory report and historical scheduler policy mapping.
2. Offline canonical fixture and slot reconstruction code + fixtures/tests for 19:00, 22:00, 23:00, 00:00, kickoff revisions and postponements.
3. Full collector observed join; missing manifest with row-level evidence and unknown-evidence quarantine.
4. Cache intersection, request estimate and dry-run. API requests remain disabled until manifest validated.

## Existing evidence
Partial reconciliation: 129 research candidates; 10 fixture+bookmaker matches in one v2 mainline source, 47 UTC round targets in research-v2 ledger, 128 verified exact-ID FT and one FT missing. These are **not** missing-slot counts. 5dollar data has a different fixture-ID namespace and is not slot-level. Existing staging research remains isolated.
