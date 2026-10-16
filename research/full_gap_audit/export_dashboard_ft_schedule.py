"""Export the exact FT completeness population, reusing the dashboard's builder.

No second fixture discovery, no guessed identity joins. Operates in a disposable
checkout and writes only the requested CSV.
"""
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from odds_scanner import research_v2_pattern_stats as stats

def export(root=Path('.')):
    captured={}
    original=stats.json.dumps
    # Capture the already-computed population without modifying production stats logic.
    # The builder serializes the final payload only; capture its source-level outcomes
    # using a tracing hook on the build frame at return.
    import sys
    def trace(frame,event,arg):
        if frame.f_code is stats.build.__code__ and event=='return':
            captured['outcomes']=frame.f_locals['outcomes']
            captured['missing_rows']=frame.f_locals['missing_rows']
        return trace
    previous=sys.getprofile()
    try:
        sys.setprofile(trace)
        result=stats.build(root)
    finally:
        sys.setprofile(previous)
    settled=captured['outcomes'];unsettled=captured['missing_rows']
    assert len(settled)==result['settled_fixtures']
    assert len(settled)+len(unsettled)==result['ft_completeness_denominator']
    rows=[]
    for status,items in [('FT',settled),('NO_FT',unsettled)]:
        for r in items:
            kickoff=r.get('kickoff')
            local=datetime.fromisoformat(kickoff.replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Bangkok')) if kickoff else None
            rows.append(dict(date_bangkok=local.date().isoformat() if local else '',kickoff_bangkok=local.strftime('%Y-%m-%d %H:%M') if local else '',league=r.get('league') or '',home=r.get('home') or '',away=r.get('away') or '',canonical_fixture_id=r['fixture_id'],ft_status='FT' if status=='FT' else r.get('status','MISSING_FT'),ft_home_goals=r.get('ft_home_goals',''),ft_away_goals=r.get('ft_away_goals',''),football_day=r.get('football_day') or ''))
    rows.sort(key=lambda r:(r['kickoff_bangkok'],r['canonical_fixture_id']))
    dest=Path('research/full_gap_audit/results/dashboard-ft-898-fixture-schedule.csv')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(total=len(rows),ft=len(settled),non_ft=len(unsettled),dates=dict(sorted(Counter(r['date_bangkok'] for r in rows).items())),missing_kickoff=sum(not r['kickoff_bangkok'] for r in rows),output=str(dest)),ensure_ascii=False))
    if len(rows)!=898 or len(settled)!=893:raise SystemExit('DASHBOARD_POPULATION_DRIFT')
if __name__=='__main__':export()
