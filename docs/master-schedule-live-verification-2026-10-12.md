# Live Master recovery verification — October 12, 2026

PR #329 merged as 2c22497c6a569652d7c95c80a646e46c063e2dee after four successful CI workflows. The exact-AH group correction is PR #330; all four CI workflows passed and the local suite passed 550 tests, plus 27 Master unittest checks.

Manual run: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38270743976 — succeeded. Actual quote receipt: 2026-10-12 22:31:04.951721 Asia/Bangkok, 91.08 minutes after the 21:00 slot; this is a supplementary LATE observation, not reconstructed on-time history.

Before: five unique matches, five observations, three leagues; a rotated ten-competition request cohort. After: twelve unique matches, sixteen observations, six leagues. The supplementary run collected eleven snapshots; four were repeat observations of existing fixtures and seven were new fixtures. All eleven replay successfully offline from the original raw response timestamp with exact canonical competition and both club identities, and strict observation-before-kickoff semantics.

The live schedule endpoint returned 229 soccer fixtures. Forty-four were inside the approved Master scope in the football-day window, across 32 competitions. All 92 approved mappings were considered. The receipt reports 60 NO_MATCHES, nine KICKOFF_PASSED_OR_NOT_PREMATCH, five OBSERVED and eighteen QUOTA_SKIPPED competitions. The five queried leagues were Serie A, LaLiga 2, Allsvenskan, Ekstraklasa and Liga Leumit. LaLiga already had one prior-day-window quote, bringing total day coverage to six leagues. Eliteserien had one future fixture but was transparently QUOTA_SKIPPED.

Request accounting: one fixture-discovery request plus one five-tournament odds request, two new billable requests in total. The ledger already recorded four research requests today, so the six-request UTC-day ceiling was reached. Account health before collection reported 97 requests remaining. No additional market call was made to overcome the cap.

Preservation against baseline main 5ae70a7404c8978f3d25255bb6f85ef1b728f3e9: all 1,866 original snapshots and 1,123 original audit records remain exactly present, with eleven new records added to each; all 3,953 original result records remain unchanged. The pattern registry and provider mapping CSV are byte-identical. Both retained response hashes verify. No excluded league or fabricated team/competition ID was introduced.

Browser verification after Pages deployment run 38270921064: the real dashboard displayed twelve fixture cards, sixteen observations and 92 per-competition rows. Allsvenskan displayed two observed matches; Eliteserien displayed QUOTA_SKIPPED. WR, Over 2.5 and price histories were visible. Live FT is still awaited because the newly collected fixtures had not kicked off; no pending FT entered settled statistics.

An additional live UI issue separated integer/float/string AH line representations (-1 versus -1.0 and signed zero), causing incomplete WR and O/U sample groups. PR #330 formats only validated exact quarter-line grouping keys consistently, leaves raw snapshots intact and does not round invalid lines. Its regression checks complete N, full/half/push settlement counts, WR and raw preservation. Final deployed statistics verification follows that merge.

Limits: this closes the identified rotating-cohort recovery and identity/scope evidence work, not unrestricted market coverage or overall production certification. Quota-skipped leagues remain visible; a global provider schedule response does not independently certify every real-world fixture. Previous collector responses contained normalized quotes rather than full odds payloads, so missing historical pre-match prices cannot be manufactured. Frozen gates still permit no validated betting picks.
