# October 14 scan reliability and quota protection

## Evidence and root cause

Audited main 69cf2d1b805af59e5d48348787c358806cc5339d, the supplied September 9
project instructions, and merged PRs #338/#339/#340. No AGENTS.md exists.
The current user instruction explicitly restores the research ceiling to
6 requests per UTC day and 180 per UTC month; later main changes had raised
these to 8/240. Raw receipts retain the policy under which they were created.

- The 15:00 setup came from watchdog workflow_run
  https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38532301243
  (job 115746786297). Actual observation 15:02:30 Bangkok: 27 real quotes,
  26 distinct core AH fixtures, five queried tournaments, two research requests.
- Actions schedule-event inventory for October 14, and the incident interval
  11:00–12:00 UTC, show no canonical collector schedule invocation at 18:00.
  This establishes absent invocation evidence, not a diagnosed provider error,
  quota skip, or collector exception at that time. GitHub's internal reason for
  an absent/delayed cron is unavailable. Cron does not provide a punctuality SLA.
- Push recovery
  https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38557858239
  (job 115831347950) observed at 18:37:42, using one request for tournaments
  14189/178/186/172/629. Only five quotes passed core validation. This was a
  different population from the setup's 7/22/98/18/682. The coverage prioritizer
  had sought uncaptured tournaments instead of repeat observations.
- Watchdog 38558517463 (job 115833531353) reached its gate at 18:43 and skipped
  collection. The 18:37 transport was within minimum spacing; old population
  completion and retry gates could also hide the intended cohort gap.
- Push recovery
  https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38562246945
  (job 115845954216) observed the original cohort at 19:14:10, 74.17 minutes late:
  25 valid core quotes and two KICKOFF_PASSED fixtures. The earliest kickoff
  (FC Irtysh Pavlodar–FC Astana, 17:00) was already outside core at 15:00;
  Batman Petrolspor–Istanbulspor started at 18:30. No price is backdated.
- Some simultaneous push collectors were cancelled as pending runs under the
  common concurrency group. This demonstrates pending-trigger replacement,
  but not a lock conflict causing the missing 18:00 schedule invocation.

## Changes and trade-offs

Keep the latest main's fixed 15:00 ID cohort and the shared coordinator/lock.
Primary remains +3 minutes; independent watchdog gains +13 minutes for every
canonical slot, retaining +133 last chance and event wakeups. Recovery remains
+23/+53/+83/+113. Remove redundant legacy PinnWire cron; its manual/push entry
still uses the coordinator. These independent wakeups mitigate missed primary
runs but all scheduled Actions remain dependent on GitHub runner delivery.

Restore research ceilings 6/day and 180/month. Keep the shared account reserve
of 10 on the 250-request plan. Manual breadth reserves the current unobserved
canonical slot as well as future slots. An unfinished durable grant for a
canonical target blocks another grant; the first HTTP request may already have
been sent before cancellation. This trades automatic retry availability for
conservative quota safety. A paid attempt's 60-minute retry cooldown survives
latest-report replacement because the append-only ledger remains authoritative.

Fixed-cohort failure cannot fall back to an unrelated provider population
without verified cross-provider fixture mapping. It remains a visible gap.
Partial cohorts now count as missing in health. A completed query with no valid
core quote displays CHECKED_NO_VALID_CORE_ODDS, never OBSERVED. The Dashboard
shows the restored policy and highlights partial/no-valid-quote slots.

At the audited 19:14 receipt, research usage is 4/6 for October 14 UTC and
86/180 in October. Offline allocation proves the remaining two requests fit
21:00 and 00:00, one each, with no manual breadth. Account health at 18:42 was
174/250; the later receipt reports 76 remaining before its one market request (75 after).
This historical account observation is not a fresh provider-account promise.
The collector still checks /account immediately before transport. Remaining
month account capacity is insufficient to guarantee every remaining day's
five-request minimum; report the deficit rather than borrowing reserved calls.

## Validation and live status

Local full suite: 630 passed. An additional no-valid-snapshot presentation
regression passed separately (11 urgent reliability tests). CI must pass before
merge; no test-generated health files are included in this change.

Offline tests cover all four real collector code paths, fixed IDs and raw
append-only history, missing primary at first watchdog, duplicate zero-call
wakeups, failed/CAS quota checkpoints, cancelled grants, UTC midnight/month
rollover, full 30/31-day capacity, current/future manual reservations, immutable
retry pacing, unrelated fallback prevention, partial health and honest UI state.
No frozen validation gates, mappings, source prices or results are changed.

Before future runtime evidence, 21:00 and 00:00 are PENDING LIVE VERIFICATION.
A passing CI or deployed workflow is not proof that their cron fired on time.
