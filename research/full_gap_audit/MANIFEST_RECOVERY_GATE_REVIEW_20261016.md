# Manifest gate review — 2026-10-16

Scope: read-only review of PR #384 pinned 23-row `missing_slot_manifest.jsonl` and `recovery_queue.jsonl`. This does **not** dispatch any historical API request or modify production.

## Verified observations
- Manifest has 23 rows with explicit exact-ID mapping evidence and target timestamps.
- 22 rows are FA Cup, scheduled 2026-10-03 20:00 Asia/Bangkok (13:00 UTC), with kickoff 21:00 Bangkok (14:00 UTC); reason `ACTUAL_ATTEMPT_AFTER_KICKOFF`, status `SCAN_FAILED`. A late collection attempt does not mean a valid historical quote at exactly 20:00 can necessarily be reconstructed.
- One row: `id1000019773369872`, FC RFS–SK Super Nova, 2026-10-15 18:00 Bangkok; status `NO_PRICE`, reason `BOOKMAKER_NOT_ACTIVE`. A historical request may legitimately return no active Pinnacle market.
- Every queued item is blocked on `BLOCKED_FRESH_RESEARCH_CREDENTIAL_AND_PREFLIGHT_REQUIRED`; there is no demonstrated research entitlement, quota headroom or executable manifest-scoped workflow. The original report's `recovery_eligible=true` is a *candidate flag*, not proof of API recoverability.
- The 23 rows are **not** a full missing-slot count; the global denominator remains unproven. Do not convert UNKNOWN_EVIDENCE rows to missing without new evidence.

## Next gate
1. Obtain a dedicated research-only credential **via GitHub Actions secret**, not by displaying or extracting a key.
2. Add an isolated research-only manual workflow on the research branch, no cron, no production ledger writes, no production quota allocator; ensure exact 23-row manifest checksum pinning and explicit dispatch confirmation.
3. First run a credential-presence + account entitlement/quota preflight, with **zero historical endpoint calls**; record result without secret disclosure.
4. If preflight passes, perform a capped 1-fixture pilot with cache-first, raw immutable receipt, no invented target quote; re-audit price quality and idempotency. Expand to remaining manifest only after pilot passes.
5. Keep PR #384 draft, no merge/deploy or dashboard/statistics modifications.

**Current status: research historical calls 0; production import 0.**
