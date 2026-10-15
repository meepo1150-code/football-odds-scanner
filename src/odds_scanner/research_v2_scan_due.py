"""Local-only scheduled recovery gate: never fetch provider data here."""
import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BKK = ZoneInfo('Asia/Bangkok')
from .research_v2_slots import targets as canonical_targets, read_ledger, read_snapshots, completed


def due(now, report, event='schedule', fallback=None, ledger_rows=None, snapshots=None):
    # Pushes and automatic workflow triggers must obey the same slot/evidence
    # gate as cron; a code change is not permission to collect another quote.
    local = now.astimezone(BKK)
    from .europe_pinnacle_discovery import _football_day_bounds
    targets = [t for t in canonical_targets(_football_day_bounds(now)[2])
               if timedelta(0) <= local-t <= timedelta(minutes=150)]
    targets = [max(targets)] if targets else []
    if ledger_rows is not None:
        from .research_v2_slots import stamp,provider_attempt_receipt
        recent=[stamp(r.get("request_completed_at") or r.get("actual_observed_at")) for r in ledger_rows
                if provider_attempt_receipt(r) and stamp(r.get("request_completed_at") or r.get("actual_observed_at"))]
        if recent and timedelta(0)<=now-max(recent)<timedelta(minutes=15):return False
        targets = [t for t in targets if not completed(t, local, ledger_rows, snapshots or [])]
    if not targets:
        return False
    for output in (() if ledger_rows is not None else (report, fallback or {})):
        try:
            stamp = datetime.fromisoformat(output['generated_at'].replace('Z', '+00:00'))
            if (output.get('status') == 'RESEARCH_V2_OBSERVED'
                    and output.get('strict_snapshots_this_run', 0) > 0
                    and stamp.tzinfo and max(targets) <= stamp <= now):
                return False
        except (ValueError, TypeError, KeyError):
            pass
    # An earlier quote of the wrong population must not impose the 60-minute
    # retry delay on the newly required fixed-cohort observation. The common
    # 15-minute transport spacing above still applies.
    if ledger_rows is not None and max(targets).hour != 15 and local.date().isoformat() >= '2026-10-14':
        setup_target = canonical_targets(_football_day_bounds(now)[2])[0].isoformat()
        master_setup = any(r.get('scheduled_target_at') == setup_target
                           and r.get('collection_succeeded') is True
                           and r.get('master_competitions_considered') for r in ledger_rows)
        master_setup = master_setup or any(r.get('scheduled_target_at') == setup_target
                                          and r.get('home_club_id') and r.get('away_club_id') for r in snapshots or [])
        if master_setup and report.get('daily_cohort_policy') != 'FIXED_1500_FIXTURE_COHORT_V1':
            return True
    if ledger_rows is not None:
        # Control checks may overwrite the latest report. The immutable ledger
        # still governs retry pacing and prevents another paid call on a wakeup.
        attempts = [stamp(r.get('request_completed_at') or r.get('actual_observed_at'))
                    for r in ledger_rows if provider_attempt_receipt(r)
                    and (r.get('requests_used', 0) or r.get('http_requests_attempted', 0))
                    and stamp(r.get('scheduled_target_at')) == max(targets)]
        attempts = [t for t in attempts if t and max(targets) <= t <= now]
        if attempts and now - max(attempts) < timedelta(minutes=60):
            return False
    try:
        attempted = datetime.fromisoformat(report['generated_at'].replace('Z', '+00:00'))
        if (attempted.tzinfo and max(targets) <= attempted <= now
                and (ledger_rows is None or provider_attempt_receipt(report))
                and (ledger_rows is None or report.get('scheduled_target_at') == max(targets).isoformat())):
            return now-attempted >= timedelta(minutes=60)
    except (ValueError, TypeError, KeyError):
        pass
    return True


def needs_finalization(now, ledger_rows, snapshots):
    """Allow one local-only pass to record expired slots as MISSED."""
    from .europe_pinnacle_discovery import _football_day_bounds
    from .research_v2_slots import RECOVERY_MINUTES, stamp
    for target in canonical_targets(_football_day_bounds(now)[2]):
        if now <= target + timedelta(minutes=RECOVERY_MINUTES):
            continue
        if completed(target, now, ledger_rows, snapshots):
            continue
        if not any(stamp(r.get('scheduled_target_at')) == target and
                   r.get('state') == 'MISSED' for r in ledger_rows):
            return True
    return False


if __name__ == '__main__':
    try:
        report = json.loads(Path('reports/pinnwire_research_v2_status.json').read_text())
    except (OSError, ValueError):
        report = {}
    try:
        fallback = json.loads(Path('reports/propline_research_v2_status.json').read_text())
    except (OSError, ValueError):
        fallback = {}
    now = datetime.now(timezone.utc)
    ledger, snapshots = read_ledger(), read_snapshots()
    collect = due(now, report, os.getenv('SCAN_EVENT', 'schedule'), fallback, ledger, snapshots)
    if os.getenv('SCAN_FINALIZE_MISSED') == 'true':
        collect = collect or needs_finalization(now, ledger, snapshots)
    print('collect=' + str(collect).lower())
    # Observability only: do not replace the authoritative due() decision.
    from .research_v2_gate_diagnostics import explain
    from .europe_pinnacle_discovery import _football_day_bounds
    diagnostic = explain(now, canonical_targets(_football_day_bounds(now)[2]), ledger, snapshots)
    reason = diagnostic['reason']
    if collect and not diagnostic['collect']:
        reason = 'COLLECT_ALLOWED_BY_EXISTING_GATE_OR_MISSED_FINALIZATION'
    elif not collect and diagnostic['collect']:
        reason = 'BLOCKED_BY_EXISTING_GATE_OR_REPORT_COOLDOWN'
    print('gate_reason=' + reason)
    print('gate_target=' + (diagnostic['target'] or 'NONE'))
    print('gate_diagnostic_only=true')
    summary = os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as handle:
            handle.write('\nSlot gate at '+now.isoformat()+': collect='+str(collect).lower()+
                         '. Ledger evidence and transport cooldown checked; no provider calls in gate.\n')
