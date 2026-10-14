# Midnight readiness guard follow-up

Base: 4ffef991c76e53c3d721ffc1ce0cab9964f2c137, after merged PR 368.
PR 368 already reconciles 42 deterministic PinnWire aliases, quarantines the
changed-kickoff FT identity, imports two reviewed FT results, and publishes
fixture diagnostics plus next-slot readiness. Do not duplicate those changes.

The readiness report can incorrectly say READY_FROM_RETAINED_EVIDENCE when
an earlier canonical durable grant has no finalized receipt. The actual
collector correctly blocks such a duplicate transport (PR 365). Make readiness
honor that same gate, show the grant IDs and explicit blocker reasons, and keep
runtime_verified=false. A failed/cancelled grant is never refunded.

Use strict kickoff > target + 3 minutes for the forecast, matching the existing
primary wakeup. A fixture starting at or before the primary cannot provide a
new prematch snapshot. Calculate current ledger usage in UTC even when the
caller supplies a Bangkok-aware clock. Missing or future-dated account evidence
must not produce a ready status. Account remaining stays an estimate and the
live collector must recheck /account before paid transport.

No scheduler, collector transport, grant allocator, quota ceiling, mappings,
prices, results, raw histories, or frozen validation gates change. Only the
offline readiness function, its Monitor rendering and four regression tests
change. All four focused regressions and related quota/reliability tests pass.
Full suite: 641 tests pass. JavaScript syntax and whitespace checks pass.

At the audited 21:00 receipt, actual scan=21:04:08 Bangkok, valid core=22.
Original 15:00 cohort=27, expected midnight primary prematch=11, tournament
IDs 7/18, one request required. UTC research usage=5/6 daily and 87/180
monthly. Last current collector account response before 21:00=75 remaining,
after its durable grant estimate=74. The remaining one daily call cannot fund
an extra paid retry if midnight's request fails. GitHub cron punctuality and
provider market availability remain unverified future runtime conditions.

PR 368 evidence remains authoritative for FT recovery. Sabadell–Andorra's
changed kickoff and Primorje–Triglav's reversed home/away remain quarantined;
a verified symmetric score does not repair reversed odds selection identity.
Public sources were checked again: NZS confirms Triglav–Primorje 1–1 on
September 26; AS reports the October 3 Sabadell postponement and October 4
rescheduling. These facts do not authorize a guessed raw identity rewrite.
