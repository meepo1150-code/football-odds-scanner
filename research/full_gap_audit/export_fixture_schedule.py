"""Export every known fixture kickoff from pinned historical inventory, Bangkok time."""
import argparse,csv,gzip,json
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
BKK=ZoneInfo('Asia/Bangkok')
def build(rows):
    out=[];seen=set()
    for r in rows:
        fid=r.get('provider_fixture_id');ko=r.get('current_kickoff_utc')
        if not fid or not ko or fid in seen:continue
        seen.add(fid)
        t=datetime.fromisoformat(ko.replace('Z','+00:00')).astimezone(BKK)
        day=(t-timedelta(hours=6)).date().isoformat()
        out.append(dict(football_day=day,calendar_date_bangkok=t.date().isoformat(),kickoff_bangkok=t.strftime('%Y-%m-%d %H:%M'),fixture_id=fid,league=r.get('league') or '',home=r.get('home') or '',away=r.get('away') or '',production_evidence=bool(r.get('production_evidence')),kickoff_changed=bool(r.get('kickoff_changed')),identity_conflict=bool(r.get('identity_conflict')),lifecycle=r.get('lifecycle') or ''))
    return sorted(out,key=lambda r:(r['kickoff_bangkok'],r['fixture_id']))
def main():
    p=argparse.ArgumentParser();p.add_argument('--inventory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parent
    if not a.output.resolve().is_relative_to(root):raise SystemExit('RESEARCH_OUTPUT_ONLY')
    opener=gzip.open if a.inventory.suffix=='.gz' else open
    with opener(a.inventory,'rt',encoding='utf-8') as f:rows=build(json.loads(s) for s in f if s.strip())
    if a.output.exists():raise SystemExit('OUTPUT_ALREADY_EXISTS')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    days=Counter(r['football_day'] for r in rows)
    print(json.dumps(dict(fixtures=len(rows),with_production_evidence=sum(r['production_evidence'] for r in rows),football_days=len(days),per_day=dict(sorted(days.items())),missing_team_names=sum(not r['home'] or not r['away'] for r in rows)),ensure_ascii=False))
if __name__=='__main__':main()
