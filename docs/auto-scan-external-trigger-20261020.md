# External Auto trigger cutover

Status: prepared, not activated. Do not merge the cron removal until the
external account and authenticated dispatch have been verified.

Only Auto's event source and its authorization condition change. All job steps,
environment variables, concurrency, permissions, Manual and scanner modules stay
unchanged. The dispatcher sends one request directly to the existing Auto
workflow; there is no proxy, retry workflow, watchdog, fallback or new collector.

## Service and configuration

Use cron-job.org with two jobs from
`config/auto-scan-external-schedules.json`. This file is a secret-free preparation
bundle, not a live service registration or a single API request. Each `jobs`
element is one job's configuration. Create each job disabled; for API creation,
wrap the individual element as `{"job": <element>}` and PUT it to `/jobs`.

The timezone is Asia/Bangkok. The daily job runs at 00:00, 15:00, 18:00 and
21:00; the weekend job adds Saturday/Sunday 12:00. Total: 30 dispatches/week.
Midnight is the calendar-day midnight, preserving the original schedule.

The endpoint is:
`https://api.github.com/repos/meepo1150-code/football-odds-scanner/actions/workflows/auto-scan.yml/dispatches`

Method: POST. JSON body:
`{"ref":"main","inputs":{"confirm_live_requests":true}}`.
Store a GitHub fine-grained token only in the scheduler's Authorization header,
replacing `Bearer REPLACE_IN_SCHEDULER_ONLY`. Limit repository access to this
repository and grant Actions write. Do not reuse an odds-provider key or put
credentials in this repository, a URL or chat. Account creation/login and token
entry require the account owner. Record the token expiry in the service setup.

## Test and cutover sequence

1. Sign into the scheduler and create the two disabled jobs. Confirm there are
   no other enabled external jobs targeting this Auto workflow.
2. Test authentication against the same endpoint with
   `{"ref":"main","inputs":{"confirm_live_requests":false}}`.
   A successful dispatch and a new Auto run with `observe` skipped verify the
   external request path without invoking the collector or odds API. Confirm
   that no snapshot or quota grant was created by that run. Restore true in the
   saved production job bodies and leave both jobs disabled.
3. Check for existing running/queued Auto runs. Do not cancel a running collector.
   Choose a quiet interval between rounds, merge the trigger-only cutover PR,
   and verify main no longer contains Auto schedule events. Any old pending Auto
   event must be resolved before enabling the external jobs.
4. Enable the two external jobs, verify their next predicted times in Bangkok,
   and record their actual service-assigned job IDs. Do not create duplicate jobs
   when resuming setup.
5. At the next scheduled round compare the service execution timestamp, GitHub
   Run creation/start, collection time and existing Dashboard evidence. The
   proposed acceptance target is collector start within five minutes, measured
   from the calendar slot, with a single Auto run for the invocation.

If authentication or scheduler setup is unavailable, keep this PR as a draft and
leave GitHub cron active. No service account or successful end-to-end dispatch
has been established merely by adding these files.

## Limits and rollback

External dispatch bypasses GitHub's cron wake-up but not GitHub runner allocation
or the existing collector concurrency lock. Neither the scheduler nor this change
guarantees a five-minute SLA or exactly-once delivery. HTTP dispatch acceptance
does not prove collection succeeded. Do not blindly repeat a timed-out dispatch;
inspect Actions first. No new automatic retries or recovery are installed.

To roll back, disable both external jobs first, then revert the trigger change
to restore the original GitHub cron. Leave Manual and all scanner code unchanged.

References:
- https://cron-job.org/en/
- https://docs.cron-job.org/rest-api.html
- https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
