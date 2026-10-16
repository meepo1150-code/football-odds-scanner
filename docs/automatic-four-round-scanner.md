# Automatic four-round scanner

The source manual workflow and all existing manual, transport, quota, and historical
modules remain byte-for-byte unchanged. `automatic_scan_collector.py` is an isolated
copy of the successful manual collector at `4150f928`, retaining the same AH/OU
extractors and shared provider guard. Auto-specific differences are the actual-quota
planner, durable reservation adapter, 30-minute deadline, immutable daily manifest,
and reconciliation of successful batches using their original observation times.

## Scheduling and integrity

- UTC 08:00 / 11:00 / 14:00 / 17:00 = Bangkok 15:00 / 18:00 / 21:00 / next-day 00:00.
- Football day D has slot IDs D/1500, D/1800, D/2100 and D/0000. The last target is
  D+1 00:00 Bangkok. No future target is selected.
- Only complete validated 15:00 preparation can append an immutable manifest.
  Missing preparation is a hard failure for later rounds; a manual supplement cannot
  be relabelled as 15:00 preparation. Provider IDs are drawn from retained exact-ID
  schedule evidence and approved master mappings. Unmapped markets remain no-price.
- Later rounds filter exact manifest fixture IDs. Started fixtures are reported as
  KICKOFF_PASSED, without fetching their prices. No synthetic/historical substitution.
- Shared `research-v2-collectors` concurrency serializes Manual and Auto. Existing
  legacy odds workflows are already retired (dispatch-only with jobs blocked);
  none are enabled or modified. Result-only schedules remain independent.
- Auto has no 6/day or 180/month research cap. Actual /account entitlement and the
  unchanged shared transport reserve of 10 requests are mandatory. Whole-run grants
  are persisted via CAS before transport. Failed calls conservatively consume grants.
  Unconfirmed grants block retry until evidence is reconciled, rather than risking
  duplicate paid requests. Manual retains its original reservation implementation.

## Recovery, publication and notification

- Wakeups at +7, +17, +27 minutes reconcile successful same-slot cached batches and
  retry missing work, maximum three attempts. +35 minutes publishes DELAYED/FAIL if
  not complete. Account/429 cooldowns and transport guards cannot be bypassed.
- Reused cached quotes retain their true response observation timestamps. A cache
  from another slot cannot stand in for the current slot.
- Persistence unions raw JSONL with latest main, rejects manifest conflicts, preserves
  concurrent history, and retains an artifact when publication fails. Automatic
  workflow completion triggers Pages even when the scan fails, so failure is visible.
- Actions summary and dashboard carry slot/target/actual/delay, fixtures/priced/no-price,
  requests/errors, health, recovery and run URL. ChatGPT push is not a GitHub webhook
  destination supplied by this repository; it must be separately verified. Never
  claim immediate ChatGPT delivery from the Actions summary alone.
- GitHub cron and queue delays are outside this code's control. The 30-minute SLA is
  measured and enforced; it is not a guaranteed GitHub scheduling service.

## Rollout constraints

2026-10-16's original 15:00 receipt has `coverage_complete=false`. Its successful
manual supplement was observed at 17:10:45 Bangkok (72 strict snapshots, 9 requests),
so it cannot be promoted to a validated 15:00 Auto manifest. First normal daily
preparation must run at the next 15:00 target. Until then follow-ups must report
missing validated preparation rather than fabricate a fixture set.

The last stored quota report is not a current entitlement guarantee. A broad scan
like the manual baseline can spend about 9 requests per round; four equally broad
rounds would cost about 36/day and cannot be sustained by a 250/month plan. The
scanner must report real quota exhaustion, never promise full-month coverage.

## Validation

`PYTHONPATH=src python -m pytest -q`

`PYTHONPATH=src python -m odds_scanner.automatic_scan --dry-run`

The dry-run performs no provider calls, no quota grant, and no evidence writes.
Production acceptance still requires a real validated preparation and subsequent
scheduled observations; failed-safe execution is not proof of successful coverage.
