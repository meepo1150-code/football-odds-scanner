# Expected-membership expansion audit — 2026-10-16

This is a read-only reasoning audit of the pinned PR #384 reconstruction, **not** a new measured missing count.

## Why the manifest stops at 23

The existing `audit.py` establishes `expected=True` only if the policy is scheduled **and** the fixture has an exact audit/snapshot/cohort entry at the target or membership in the fixed 15:00 cohort. A silent missing 18:00 scan can therefore remain `UNKNOWN_EVIDENCE` even if the same fixture has 15:00 and 21:00 evidence. This is a structural false-negative risk in the *expectation proof*, not proof that the missing quote exists.

The 23-item manifest consists of explicit `SCAN_FAILED` (22) and `NO_PRICE` (1). The 27 known-expected `UNKNOWN_EVIDENCE` and 70 `UNMATCHED` are not counted as recoverable. A missing file alone is not evidence of a missing expected scan.

## Safe expansion rule (proposal, not executed)

For each football day and fixture ID:
1. Determine the policy **actually deployed at the target instant**; do not retroactively impose four slots on old dates.
2. If an immutable deployed 15:00 cohort proves fixture membership for the day, enumerate all subsequent scheduled slots before kickoff and audit cutoff. A missing 18:00 fixture snapshot is an expected gap even if no collector attempt was logged, provided the cohort was valid and the slot was due.
3. Before fixed-cohort deployment, use an authoritative *day-level complete* fixture set or explicitly documented persistent cohort. **Do not** infer membership solely because the fixture appears in one or two price observations; that could represent selective discovery, a changed schedule, or separate collectors.
4. Reconcile raw tournament response completeness, round ledger, fixture attempts, AH quote evidence and exact provider namespace. If a whole-round outage is proven, label `MISSING_ROUND`; if round ran but fixture lacked valid AH, label `MISSING_FIXTURE_AH` or `NO_PRICE` as appropriate.
5. Quarantine kickoff reschedules, postponed matches, provider identity conflicts and unknown membership. Do not promote any row from `UNKNOWN_EVIDENCE` without an evidence pointer and deterministic replay test.

## Required next artifact

Create `membership_evidence_expansion.jsonl` with `fixture_id, football_day, target_slot, policy_commit, cohort_evidence, round_evidence, exact_id_evidence, evidence_quality, expected, actual, classification, exclusion_reason`. Include separate `newly_proven_expected`, `newly_proven_missing`, `still_unknown` totals, and hash-pinned source provenance. Do not overwrite the 23-row baseline manifest. A new manifest is versioned and must exclude unverified gaps.

## Current status

The pinned report still proves only 960 expected slots, with 23 candidate price deficits; the complete denominator is unknown. **No additional slots have yet been proven by this review.** No historical API calls, production writes, merges or deployments are authorized.
