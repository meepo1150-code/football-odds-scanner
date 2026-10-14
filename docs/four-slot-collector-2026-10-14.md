# Four daily observations: incident, correction, and limits

## Baseline and incident evidence

Audited main a4aec8ccc7689435f184126d1008be47d1626825 and the attached
September 9 project instructions. No AGENTS.md is present. Current user scope
supersedes the historical 6/day, 180/month research allocation.

Baseline: independent watchdog run
https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38532301243
was started by `Validation v2 Pipeline Health` completion. Job 115746786297
collected at 2026-10-14 15:02:30 Bangkok. Its receipt contains 27 extracted rows;
canonical slot validation accepts 26 distinct fixtures. Preserve both counts and
all original rows; the 26-fixture slot is the comparison baseline.

At the 18:00 incident audit (18:27–18:31 Bangkok), Actions lists showed no new
collector run after 15:02 and the persisted ledger had no October 14 18:00
receipt. This is missing scheduler invocation evidence, not a demonstrated
provider API error or quota denial. The 15:00 report marked later slots UPCOMING
because that report was generated at 15:02; that stale label does not establish
that 18:00 had run.

Historical schedule events for Europe Pinnacle Research V2, Free Research V2,
and scheduled recovery repeatedly started outside the 150-minute collection
window. For example, Europe run 38462759023 started October 13 at 20:25 UTC;
its job printed DEGRADED_DATA_COVERAGE, not a new quote. Old overlapping cron
heartbeats created 180+ scheduled collector wakeups/day. GitHub's internal
reason for late or absent schedule events is not exposed by these logs; reducing
wakeups and avoiding minute zero is a mitigation, not a punctuality guarantee.
The prior midnight receipts explicitly show SKIPPED_QUOTA under the old budget.

## Change

- One primary cron at UTC 08:03, 11:03, 14:03, 17:03 every day. These observe
  Bangkok 15:00, 18:00, 21:00 and next-calendar-day 00:00 canonical targets.
- Shared guarded recovery at +23/+53/+83/+113 minutes and last chance +133.
  The manually accessible Free Research workflow no longer duplicates the cron.
- Primary work is locally gated before setup and installs. All automatic paths
  call research_v2_slot_recovery, retain the same collector concurrency lock,
  require a durable quota grant before billable HTTP, and preserve actual time.
- The independent watchdog also wakes on hourly Scan Health Monitor completion.
  No upstream subscribes back to watchdog; PR events cannot trigger collection.
- Research ceiling 8/UTC day, 240/UTC month, max 2 requests/run. Discovery plus
  one market request per future slot and future day remain reserved. Optional
  breadth yields to monthly minimum capacity. 31*8=248 does not fit 240.
- All shared OddsPapi transports leave 10 requests of the observed 250 plan
  unused. Unmetered /account can still prove reset; failed requests consume
  capacity conservatively. Optional second batches also yield to measured
  remaining account capacity for later days. Reports expose the forecast deficit.

## Safety and verification

Tests execute four real collector code paths against offline provider fixtures,
verify actual observation time, midnight football-day identity, append-only raw
history, no duplicate billable calls, durable grants, failed-attempt counting,
UTC/month rollover, every-day schedules and 30/31-day budget simulations.
Shared-account tests block before HTTP at 240, including failed reservations.
No fixture/team mapping, frozen validation gate, price eligibility, FT result,
production pattern registry, or historical raw file is modified by this PR.

An automatic wakeup cannot reconstruct earlier market prices. An authorized
push-token recovery within the current window proves collection functionality,
not successful future cron delivery. Four daily observations still depend on
GitHub starting a runner, remaining account capacity, mapping coverage and
provider markets. A free account already used 170/250 at 05:01 UTC October 14;
there may be insufficient capacity for every remaining day's five-request
minimum. Forecast deficits must remain visible rather than promising coverage.
