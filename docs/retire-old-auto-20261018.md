# Old Auto retirement — 18 October 2026, Asia/Bangkok

The user cancelled the previous Auto scanner, fallback and 30-minute recovery
system. Manual Current-Day Odds Observation is the protected reference:
`.github/workflows/manual-current-day-odds.yml`. Its workflow, credential binding,
collector, request budgets and transport are unchanged.

## Audited components and disposition

| Component | Previous behavior | Disposition |
| --- | --- | --- |
| Automatic Four-Round Odds Observation | 15:00/18:00/21:00/00:00, cron retries at +7/+17/+27 and +35 reconciliation; 30-minute admission deadline | Workflow and six dedicated Auto modules deleted |
| Automatic Scanner Account Audit | Primary/secondary account audit; secondary current endpoint entitlement unverified | Workflow, module and control deleted; no fallback enabled |
| Scheduled Slot Recovery | Legacy primary then Propline fallback within recovery window | Disabled workflow and executable recovery module deleted |
| Independent Slot Watchdog | Legacy independent wakeups/recovery | Disabled workflow deleted |
| Canonical Slot Deadline Audit, Scan Health Monitor, Pipeline Health | Legacy deadline/monitor orchestration | Disabled workflow entrypoints deleted |
| Legacy Live/Validated/Free/Europe odds scanners and Master Schedule Manual Recovery | Retired scanner entrypoints | Disabled workflow entrypoints deleted |
| Mainline Observer, Europe Discovery, Five Dollar Live Research, Propline/Pinnwire probes | Obsolete disabled collection/probe buttons | Workflow entrypoints and obsolete scanner control tokens deleted; shared normalization/research libraries retained |
| Football Scanner Scan Alerts | ChatGPT check at +30 minutes | Disabled on 18 October; no replacement recovery automation |
| PR #421 | Unmerged low-quota improvement for old Auto | Closed without merge |
| Dashboard/Monitor | Display old Auto evidence | Labelled retired; historical receipts and manifests remain published |
| FT recovery, statistics, historical research, Pages | Process collected evidence, including Manual | Retained |

The modules used by Manual, normalization, shared budget checks, historical slot
interpretation and research adapters remain intact. Removing them would change
Manual or prevent historical evidence from being interpreted. No API secret was
deleted or changed. No raw data, snapshots, FT records, manifests or ledgers were
deleted. Deleted code remains recoverable through Git history.

## Operating policy

No new Auto replacement or timer is included in this retirement. A later
replacement can copy the protected Manual at the user's direction. The previous
30-minute automatic recovery commitment is withdrawn. Under the user's new
policy, if a future Auto has not run after 10–15 minutes, the user runs Manual;
this does not install another automatic retry, fallback or alert system.

## Verification

Regression contracts require the old entrypoints to be absent, prohibit scheduled
odds collection/recovery, check SHA-256 identity of the Manual workflow and its
collector/quota/transport, and retain Manual-triggered Dashboard publication and
historical evidence. Full offline tests and master QA must pass before merge.
No live price request is needed for this removal.

This document supersedes the Auto schedule/recovery and restored +30 alert status
in `system-maintenance-20261017.md`. That earlier report remains historical.
