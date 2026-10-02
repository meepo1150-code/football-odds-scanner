# Pending-zero request: verified checkpoint, 2026-10-02 14:10 Bangkok

The requested zero pending count has NOT been reached. No results were invented and no recent match was discarded solely to reach zero.

PR #240 merged as 41725a40d9b4b24c0801da1c4eefe56f63823b2e. 353 local tests passed; PR CI 36976808273, main CI 36976915298 and actual backfill 36976915395 succeeded. Deployment 36976980267 succeeded. Public deployed statistics were checked.

## Actual changes
Twenty API-Football records had missing team names, twelve distinct recorded recovery rounds from two sources, and no matching identity metadata in local caches. Their records satisfy the existing 72-hour age and 24-hour attempt-span gates. Previously the retirement condition required nonempty team names and therefore could never close this class of exhausted recovery.

They now retire with reason MISSING_TEAM_IDENTITY_AFTER_EXHAUSTED_RECOVERY. Raw observations are preserved, no canonical result is created, and settled statistics are unchanged. A verified result obtained later automatically removes retirement on review. Pending records now expose unmet_gates and age_eligible_at.

## Verified counts
- Active overdue queue: 102 → 82.
- Archived unresolved: 439 → 459.
- Total unresolved including archive: 541 → 541. This is queue retirement, NOT result recovery.
- Settled statistical fixtures: 395, core-price settled: 372; unchanged.
- Raw/verified/quarantined snapshots: 1312 / 1226 / 86; unchanged.
- Legacy odds recovered: 0.
- Movement: 117 fixtures / 684 deltas.
- Forward samples: 10 / 4 / 0; threshold 150 unchanged.

## Remaining 82
All 82 are still younger than the 72-hour retirement gate at this checkpoint.
- 26 reach the age boundary on October 2 UTC (24 ordinary unresolved, 2 blocked AET result identities).
- 22 reach it on October 3 UTC.
- 34 reach it on October 4 UTC.
Thirty-four also lack the required 24-hour evidence span; one lacks four attempts and two source attempts. Passing an age boundary alone does not guarantee retirement. Existing free-result workflows continue recovery and lifecycle review automatically.

The two AET identities remain blocked because regulation-time score evidence has not been promoted. Additional focused web review found the Osaka match and its extra-time scoring timeline; no explicit normal-time result was accepted. A second general result page resolved to a different historical fixture and was rejected. No source/date mismatch was used as a result.

## Trade-off
Closing old missing-name loops prevents endless unproductive retries. Keeping recently played and conflicted matches unresolved delays zero but protects against losing recoverable results or contaminating AH/O-U statistics. This checkpoint verifies deployed data artifacts; it does not claim a new browser interaction test during this specific retirement change.
