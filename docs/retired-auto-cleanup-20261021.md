# Retired scanner cleanup — 21 October 2026

The working Auto scanner is `.github/workflows/auto-scan.yml`, dispatched by
cron-job.org. Manual remains `.github/workflows/manual-current-day-odds.yml`.
The successful 15:00 Bangkok run on 21 October is Actions run `39566009521`.

Remove the 22 remaining `Retired - ...` workflow stubs. Each was already a
dispatch-only placeholder whose only job had `if: false`; none was collecting
prices. Deleting them removes obsolete entrypoint files rather than changing the
working collector. The earlier Auto/recovery/watchdog entrypoints were already
deleted by the 18 October retirement.

Remove `apps/dashboard/automatic-rounds.js`, its two script includes and its
Pages build copy. It inserted an Old Auto Scanner panel backed by the retired
system's receipt files. It is not the current external dispatch status panel.

Keep all source modules, current Auto and Manual workflows, external schedule
configuration, provider credentials, quota behavior, result recovery, settlement,
statistics, normal monitoring and their active schedules unchanged. Historical
receipts, snapshots, FT results and retained raw evidence remain in the repository
and continue to be published for audit. Shared adapters are not obsolete merely
because an old workflow used them.

Legacy ChatGPT football automations were checked and are already disabled; no
new automation, retry, fallback, timer or recovery is introduced. This audit does
not enumerate the owner's jobs inside cron-job.org.

Workflow deletions and the retired panel can be recovered from Git history.
This replaces the old-panel display disposition in
`docs/retire-old-auto-20261018.md`; that document remains historical evidence.
