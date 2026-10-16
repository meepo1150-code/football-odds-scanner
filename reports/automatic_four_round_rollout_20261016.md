# Automatic four-round scanner — rollout evidence

Status: DEPLOYED; SUCCESSFUL SCHEDULED PRICE OBSERVATION NOT YET VERIFIED.
Timezone: Asia/Bangkok. Evidence checked 2026-10-16 approximately 17:36.

## 1. Files created / modified
Created `.github/workflows/automatic-four-round-odds.yml`, `src/odds_scanner/automatic_scan.py`, `automatic_scan_budget.py`, `automatic_scan_checkpoint.py`, `automatic_scan_collector.py`, `automatic_scan_manifest.py`, `automatic_scan_persistence.py`, `tests/test_automatic_scan.py`, `apps/dashboard/automatic-rounds.js`, `docs/automatic-four-round-scanner.md`.
Modified `.github/workflows/pages.yml`, `apps/dashboard/index.html`, `apps/dashboard/monitor.html`, `tests/test_ci_production_isolation.py`.
Rollout controls: `controls/automatic_scan_dry_run.txt`, `controls/automatic_scan_live.txt`.
Runtime writes: append-only Auto slot ledger/manifests and observation evidence; derived latest reports. This report is additional documentation.

## 2. Manual regression
Original workflow blob SHA remains `446366d65db1d31fd8a78d7a47a5350877f66e5c`.
Original collector blob SHA remains `83be9daf49a09ff907ae19626a166de5a67bd91d`.
Both were read again from main after deployment and are unchanged. Existing manual quota/transport modules and historical modules are unchanged. Clone imports the same AH/OU extractors and shared guarded transport. Existing manual regression tests pass.

## 3. Schedule
| UTC cron | Bangkok target | Football day |
| --- | --- | --- |
| 08:00 | 15:00 | D |
| 11:00 | 18:00 | D |
| 14:00 | 21:00 | D |
| 17:00 | 00:00 next day | D |

Primary cron: `0 8,11,14,17 * * *`. Recovery/reconciliation/deadline cron: `7,17,27,35 8,11,14,17 * * *`.
Explicit IDs: D/1500, D/1800, D/2100, D/0000. Cron and queue latency are measured, not guaranteed by GitHub.

## 4. Daily fixture set
Only complete validated 15:00 preparation can append the immutable exact-ID manifest. Follow-ups filter the same fixture IDs; already-started fixtures receive truthful reasons. No manual supplement is relabelled as 15:00 preparation. October 16 original 15:00 receipt has coverage_complete=false; the successful manual baseline happened at 17:10:45. Therefore no valid Auto manifest exists for October 16, and its follow-ups must fail closed. First normal preparation target: October 17 15:00.

## 5. Recovery
Up to three attempts; same-slot successful raw batches are reconciled without repeating their requests or changing observed timestamps. Invalid response batches remain retryable. Unconfirmed durable grants block duplicate transport. No prices are collected for a slot after +30 minutes; overdue slots publish DELAYED/FAIL. +35 is a deadline audit wakeup. GitHub queueing can delay that audit too.

## 6. Quota and duplicate safety
No artificial research 6/day or 180/month cap in Auto. Actual /account quota and unchanged provider transport guard, including the 10-request reserve and cooldown, remain mandatory. Manual/Auto share `research-v2-collectors` concurrency and durable shared grant evidence. Legacy odds workflows were already retired and were not enabled or modified. Independent result-only schedules remain.

## 7. CI
875 local offline tests passed, including 23 Auto tests; master validation and 27 master tests passed.
Exact head c207eb779aea01f451e1cc60c9a497b7dd882b12 CI passed:
- Offline PR Validation: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38887732198
- Football Master Offline QA: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38887732269

## 8. PR and merge
https://github.com/meepo1150-code/football-odds-scanner/pull/394
Merge commit: `2fefbcbb55e27d3c550c07f4e742399338280893`.

## 9. Actual production executions
- Dry-run SUCCESS: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38888140177 — DRY_RUN, requests_used=0, manifest_available=false; persistence correctly skipped.
- Current-slot production safety check: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38888209440 — executed at 17:35:28 Bangkok, target 15:00, 155.48 minutes late. Business status DELAYED, Scan Health FAIL, actual_scan_time=null, requests_used=0, api_errors=0, complete=false. No successful price observation is claimed. Failure evidence was committed to main (84fdf3b) and the artifact uploaded successfully.

## 10. Dashboard and notification verification
Pages publication after the failed scan succeeded: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38888254377
Live UI https://meepo1150-code.github.io/football-odds-scanner/ was reloaded and the Auto panel visibly displayed October 16, no validated 15:00 fixture manifest, 155.48-minute delay, 0 requests, FAIL and the actual production run URL.
The existing ChatGPT alert automation was successfully rescheduled to 00:30/15:30/18:30/21:30 Bangkok with read-only checks of actual evidence. Two conflicting legacy weekend tasks were paused. This is scheduled checking, not immediate GitHub webhook delivery; arrival of the newly configured reports is not yet verified. A separate October 17 15:25 acceptance/repair follow-up was created successfully.

## 11. Remaining risks / unfinished acceptance
- A real successful Auto preparation and subsequent scheduled price observations are still pending. Tests and a failed-safe production run do not satisfy that acceptance gate.
- October 16 follow-ups cannot collect under the strict manifest rule; the original Manual workflow remains available unchanged.
- Four equally broad 9-request rounds would cost about 36 requests/day and cannot be sustained by a 250/month plan. The scanner reports actual quota limits rather than bypassing them.
- GitHub schedule/queue delays and provider outages can exceed 30 minutes; the code measures and reports failures but cannot guarantee external delivery or uptime.
- Unknown grant outcomes intentionally block recovery until reconciled, trading coverage for duplicate-request safety.
- Immediate per-completion ChatGPT push is not connected. Scheduled reporting configuration is confirmed; actual future delivery still needs observation.
