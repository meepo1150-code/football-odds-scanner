# FT recovery, 12 October 2026

Recovered all 78 active overdue fixture IDs from the 2196533 baseline using reviewed website results; 249 previously retired unresolved IDs remain archived. These are provider identity groups, not a claim of 78 unique matches. Raw snapshots and the empty production registry are unchanged.

Evidence is stored in data/research/web_result_evidence.jsonl. Import requires one official source or two distinct reputable source hosts, FT status, team identity, UTC match date and integer scores. It refuses conflicts. Website scores never overwrite a trusted non-web result.

## Causes and changes

- FotMob's prior report recorded 78 no-exact-identity cases. Provider team names differ, e.g. Como 1907 versus Como and FC Twente Enschede versus FC Twente. Add explicitly reviewed competition-scoped aliases; retain exact kickoff and uniqueness checks. This covers reviewed aliases, not arbitrary future names.
- At least one snapshot kickoff differs from the result feed (Casa Pia), so exact timestamp matching correctly refuses it. Manual dated evidence recovers the score without changing raw kickoff or odds.
- Free recovery ran every six hours. Add hourly cached FotMob/ESPN checks; keep quota-sensitive recovery on the original six-hour cadence. Scheduled GitHub jobs can be delayed and source publication can lag; three hours after kickoff is an alert threshold, not guaranteed final status.
- ESPN cache incorrectly required leagues instead of events. Recent saved envelopes happened to contain both, so this is a real compatibility bug but not evidence that every current miss was caused by it. Correct validation and report stale fallback as partial failure.
- Unmatched is specific to the API-Football join, not missing FT across all sources. Clarify dashboard wording.
- WR counts profitable matches: (full win + half win) / all settled outcomes, including pushes. ROI uses actual five-way Asian settlement. For -0.25 and a draw, favorite HALF_LOSS returns -0.5 stake; underdog HALF_WIN returns (decimal odds - 1)/2.

## Validation

506 tests passed before the additional competition-scoping regression; targeted final validation and hosted checks are recorded in the pull request. Offline coherent evidence rebuild passed with 782 settled identity groups and zero active missing FT.
