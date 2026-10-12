"""Bounded public-result recovery. The separate collector job owns all odds calls."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .europe_pinnacle_discovery import _football_day_bounds
from .result_recovery_lifecycle import rows, RESULTS, SNAP, review
from .web_result_recovery import build_queue

REPORT=Path('reports/daily_preparation_status.json')


def recovery_days(root, now, backlog_days=3):
    previous=(datetime.fromisoformat(_football_day_bounds(now)[2]).date()-timedelta(days=1))
    recent={ (previous+timedelta(days=d)).isoformat() for d in (-1,0,1) }
    known={str(r.get('fixture_id')) for r in rows(root/RESULTS)}
    historical=set()
    for r in rows(root/SNAP):
        if str(r.get('fixture_id')) in known:continue
        try:ko=datetime.fromisoformat(str(r.get('kickoff')).replace('Z','+00:00'))
        except ValueError:continue
        if not ko.tzinfo or now-ko<timedelta(hours=3):continue
        for d in (-1,0,1):
            day=(ko+timedelta(days=d)).date().isoformat()
            if day not in recent and day<=now.date().isoformat():historical.add(day)
    days=sorted(historical)
    offset=(now.date().toordinal()*backlog_days)%len(days) if days else 0
    batch=[days[(offset+i)%len(days)] for i in range(min(backlog_days,len(days)))]
    return sorted(recent|set(batch)),previous.isoformat(),len(days)


def run(root=Path('.'),now=None):
    now=now or datetime.now(timezone.utc)
    days,previous,backlog=recovery_days(root,now)
    from .web_result_evidence import import_evidence
    from .local_result_reuse import run as reuse
    from .fotmob_result_backfill import run as fotmob
    from .espn_result_backfill import run as espn
    from .daily_fixture_result_backfill import run_backfill
    before={str(r.get('fixture_id')) for r in rows(root/RESULTS)}
    reports={};errors=[]
    steps=[('reviewed_web',lambda:import_evidence(root)),('local_reuse',lambda:reuse(root)),
           ('fotmob',lambda:fotmob(root,include_retired=True,max_requests=6,day_filter=days)),
           ('espn',lambda:espn(root,include_retired=True,max_requests=6,day_filter=days)),
           ('exact_flashscore',lambda:run_backfill(root,max_requests=20))]
    for name,call in steps:
        try:
            reports[name]=call()
            failures=reports[name].get('errors') or reports[name].get('request_failures') or []
            if failures:errors.append({'source':name,'failures':failures})
        except Exception as exc:errors.append({'source':name,'error':type(exc).__name__+': '+str(exc)})
    review(root,now)
    queue=build_queue(root,limit=10000,include_retired=True)
    after={str(r.get('fixture_id')) for r in rows(root/RESULTS)}
    report={'generated_at':datetime.now(timezone.utc).isoformat(),
            'football_day':_football_day_bounds(now)[2],'previous_football_day':previous,
            'recovery_days':days,'backlog_days_total':backlog,'backlog_batch_policy':'THREE_ROTATING_HISTORICAL_DAYS_PLUS_PREVIOUS_DAY_NEIGHBORS',
            'ft_recovered':len(after-before),'ft_unresolved':queue['unresolved_total'],
            'retired_unresolved':queue['retired_unresolved_total'],
            'odds_api_requests_used':0,'public_requests_limit':32,
            'public_requests_used':sum(r.get('requests_used',r.get('requests',0)) for r in reports.values()),
            'status':'PARTIAL_SOURCE_FAILURE' if errors else 'RECOVERY_GAPS_REMAIN' if queue['unresolved_total'] else 'RECOVERY_COMPLETE',
            'source_reports':reports,'errors':errors,'production_ready':False}
    path=root/REPORT;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    r=run();print(json.dumps({k:v for k,v in r.items() if k!='source_reports'},ensure_ascii=False))
