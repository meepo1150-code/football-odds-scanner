# Auto Scan — direct Manual workflow copy

Approved 18 October 2026, Asia/Bangkok. This follows retirement PR #429.

## Implementation

`.github/workflows/auto-scan.yml` copies the working
`manual-current-day-odds.yml` job. The existing collector and every provider,
normalization, quota, snapshot and settlement library remain unchanged.

Only the workflow name, cron trigger, main-branch authorization condition,
temporary publication directory and data commit label differ. A parity test
compares the full jobs after normalizing these permitted differences. The
Manual workflow and its protected dependencies retain their existing hashes.

| Bangkok calendar day | Scan times | UTC cron |
| --- | --- | --- |
| Every day | 00:00 / 15:00 / 18:00 / 21:00 | `0 8,11,14,17 * * *` |
| Saturday and Sunday additionally | 12:00 | `0 5 * * 6,0` |

This yields 30 scheduled invocations per week. Midnight is 17:00 UTC on the
previous calendar day. Weekend noon is 05:00 UTC on that Saturday/Sunday.

The schedule is the timer; it runs this workflow once per round. No extra
dispatcher, recovery schedule, watchdog, fallback account or ChatGPT automation
is installed. Manually dispatching Auto retains the original confirmation input.
Cron authorizes the scheduled run automatically, on main only.

## Manual safety and publication

Both jobs keep `research-v2-collectors` concurrency with cancellation disabled,
so they cannot run their collector simultaneously. Both keep the same configured
`HISTORICAL_ODDSPAPI_KEY` reference, fresh account checks, durable quota guards,
minimum observation spacing and the original single-attempt odds request path.
The original bounded git push retry is copied unchanged in behavior; it retries
publishing already collected evidence, never recollects odds.

Pages listens to Auto completion as it already listens to Manual, including
failed runs with partial evidence. No Manual event handling is removed. Odds,
FT and statistics use the existing shared append-only data path. The collector's
existing manual supplementary classification is retained because this is the
same collection path; Actions identifies whether Auto or Manual triggered it.

## Limits and acceptance

GitHub cron can start late. This change does not promise a 10–15-minute scheduling
SLA. The user runs Manual when a round is late; a queued Auto may still start
later, with the existing Manual spacing/quota checks applied. No quote is backdated:
the copied job uses its actual execution time for the observation target.

API quota is shared with Manual. More invocations do not increase provider quota;
the existing guards may skip collection when insufficient. The 30-invocation
weekly schedule must not be interpreted as guaranteed funded coverage.

Fixture discovery and selection are exactly the Manual behavior. This does not
add the retired Auto's immutable 15:00 fixture-set requirement. No automatic
cross-account failover, synthetic price, timestamp rewrite, frozen research-gate
change or live API test is part of this change.

Offline acceptance covers job parity, all seven days of timezone conversion,
Manual hash protection, publication triggers and a mocked Sunday-noon collection.
CI and master integrity must pass before merge. Live collection acceptance needs
the next scheduled run's actual snapshots and receipts; deployment alone is not
proof that a scheduled price scan succeeded.
