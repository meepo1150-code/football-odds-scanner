# Report 6 — Final recommendation


EXPLORATORY / NO PROVEN EDGE. Flat stake 1 unit, price 1.80–2.20; AH contemporaneous favorite, OU Over. This benchmark is not a validated betting strategy. WR uses winning/losing stake fractions; pushes excluded. CLV unavailable: last observed quote is not a verified closing quote. All times Asia/Bangkok; football-day cutoff 05:00.

Primary current Pinnacle cohort: 5137 observations / 1837 fixtures; 1817 fixtures joined to FT.


1. **Do multiple scans improve selection?** They increase observed fixture/time coverage. No validated improvement in betting selection is established. Benchmarks and exploratory prediction tests do not pass frozen promotion gates.

2. **Does movement predict FT?** See controlled out-of-time MSE tests in Report 3; any descriptive association is distinct from incremental prediction. None is proof of positive tradable EV or causation.

3. **How different are first and last?** Report 2 provides paired same-side/same-line ROI differences and intervals, separately from independent decisions. First/last availability is selective and closing coverage is not proven.

4. **What lead time is optimal?** NOT ESTABLISHED. Matched T6–12 versus T1–3 tests are reported; bin ROI ranking cannot remove different fixture populations and sparse timing coverage.

5. **What is lost at 15/18 only?** A covers 1586 fixtures; B covers 1185; 401 A-covered fixtures lack B coverage. Later movement and opportunities after 18 are unavailable to B; exact missing fixtures are listed.

6. **Is 15→18 sufficient for real bets?** NOT PROVEN. Only 1066 fixtures have both operational receipts. New scan data arriving after 18:00 cannot support an exact-18:00 decision. Missing/incomplete validation and zero frozen validated patterns prevent EV selections.

7. **Two, three or multiple rounds?** Keep current schedule while shadow-testing two and three rounds. Benefit: retain information and avoid premature loss; drawback: higher request and storage cost. Risk: quota failures may impair coverage; request savings must be measured on actual billing receipts.

8. **If restricted to two, which times?** No statistically defensible optimal pair established. 15/18 is an operational hypothesis for shadow mode, not a recommended performance optimum. It sacrifices late information and pre-18 fixtures; 15/21 or kickoff-relative alternatives need prospective matched evaluation.

## Future shadow trial and limitations

Do not change production. Freeze a selection model only after existing gates pass; log all candidate fixtures, actual request/receipt times, missing markets, result first-availability and tradable closing quotes. Use 18:15 as an explicit operational deadline or collect before 18:00; never backdate. Test B-A paired ROI against -1pp, coverage loss <=5%, with one-sided 95% CI and precommitted 90-day minimum / >=3 leagues. Multiple-testing correction and frozen multi-season requirements remain mandatory.

- AH: inspected pairs=1111, B-A difference=-0.59%, CI=[-2.09%, 0.84%]; estimated NEW paired fixtures required at 80% power for 1pp margin=3766. This is an SD-based planning estimate, not a proven adequate sample; no retrospective pairs count toward untouched forward evidence.

- OU: inspected pairs=1130, B-A difference=-0.21%, CI=[-0.65%, 0.21%]; estimated NEW paired fixtures required at 80% power for 1pp margin=331. This is an SD-based planning estimate, not a proven adequate sample; no retrospective pairs count toward untouched forward evidence.

Historical recovery can study price paths separately but cannot establish live receipt coverage. Archived snapshots, partial raw receipts, removed leagues, result recovery timing, short season coverage and bookmaker/provider differences constrain external validity. Existing normalized data are not independently reverified against every raw/API source. Repository coverage is not proof of all historically collected or expired-artifact coverage.

Reproduce with `python research/multiscan_20261101/analyze.py --output research/multiscan_20261101/results`. Dependencies pinned in requirements.txt. Input SHA-256 manifest identifies exact data; all outputs derive offline. Production schedule, collector, secrets, FT history and dashboard logic are unchanged.
