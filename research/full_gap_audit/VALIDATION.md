# Validation and production isolation

- Recovered-session targeted audit/backfill tests: **107 passed, 61 subtests**.
- Full offline suite in detached test worktree at local checkpoint `4354f8ce`:
  **936 passed, 61 subtests**, 62.14 seconds.
- New tests exercise historical deployment boundaries, midnight cross-day,
  fixed-cohort cutover, kickoff changes, exact fixture identity, no-price vs
  compound rejection, missing-slot classification, quarter-line draw/half/push,
  manifest deduplication, future slots, output isolation and immutable idempotency.
  Existing backfill tests cover quota/entitlement, active-state handling, quality,
  provenance hashes, cache resume, stale/future quotes and credential isolation.
- Original full-suite tests wrote two derived files in the disposable checkout;
  `data/normalized/scan_health_history.jsonl` and `reports/scan_health_latest.json`
  were restored byte-for-byte to the research-parent version. These writes were
  never committed or sent to production. A separate detached worktree was used
  for the final full run. No protected file is included in this research change.
- Raw original cache response bytes were checked against all 100 receipts. The
  downloaded artifact ZIP hash matches the Actions artifact digest in README.
- Baseline normalized rows and historical-only rows are counted separately:
  **2,721** current rows, **323** historical-only evidence rows. The latter are
  never automatically restored or added to the dry-run production population.
- Before/after: **2,721 observed / 0 admitted backfilled**, unchanged. There are
  **0** staged new settlement-eligible observations and no WR/ROI/reliability delta.
- All newly authored files are under `research/full_gap_audit/`. Existing
  `data/`, `src/`, `config/`, `reports/`, dashboard and `.github/workflows/` are
  unchanged against research parent `564ec452b50725fb7b472b9f1c1068790a57beee`.
- No API credentials were extracted; the dedicated research key is absent from
  this local runtime. No account or historical request, workflow dispatch,
  production scan, merge or deploy occurred in this task.
- The Draft PR targets the **research staging branch**, not main. Existing offline
  CI triggers only for PRs targeting main, so CI may be absent for this research
  PR. Do not call absent CI green. No workflow was modified to force CI execution.
- Full recovery is **blocked and incomplete**: older cohort membership/global
  expected denominator remain unproven; the 23 uncached deficits require fresh
  dedicated-account entitlement/quota checks in an authorized isolated runner.
- Large research JSONL evidence is losslessly gzip-packaged with deterministic
  mtime=0. Unit tests accept the compressed matrix/inventory on a fresh clone.

Checked Actions evidence in the preceding audit session (read-only):

- Earliest retained 4-quote observer:
  https://github.com/meepo1150-code/football-odds-scanner/actions/runs/34483864722
- Late 3 October recovery (20:00 target; actual 21:12):
  https://github.com/meepo1150-code/football-odds-scanner/actions/runs/37128797477
- Concurrent free-provider scan, separate unresolved namespace:
  https://github.com/meepo1150-code/football-odds-scanner/actions/runs/37125385577
- 16 October 00:00 observed at 00:09:28:
  https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38774906568
- Existing cache expansion/resume:
  https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38830015043

These runs are supporting evidence, not an exhaustive export of every Actions log
or proof that all external/expired artifacts were searched.
