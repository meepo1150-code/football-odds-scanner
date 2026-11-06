"""Network-free daily editorial review; production files are read-only inputs."""
import json, hashlib, argparse
from pathlib import Path
from datetime import datetime, timezone
from .engine import append_ledger, read_ledger, summarize

def rows(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def weighted(x, prefix=''):
    w=x.get(prefix+'full_win',0)+.5*x.get(prefix+'half_win',0)
    l=x.get(prefix+'full_loss',0)+.5*x.get(prefix+'half_loss',0)
    return round(100*w/(w+l),2) if w+l else None
def bucket(x):
    return '<1.80' if x<1.8 else '>2.20' if x>2.2 else '1.80-1.89' if x<1.9 else '1.90-1.99' if x<2 else '2.00-2.09' if x<2.1 else '2.10-2.20'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--date',required=True);ap.add_argument('--source-commit',required=True);a=ap.parse_args()
    now=datetime.now(timezone.utc);ep=Path('youtube_prediction/episodes')/a.date;ep.mkdir(exist_ok=True)
    if (ep/'daily.json').exists(): raise ValueError('Existing episode must be reviewed before resume')
    report=Path('reports/research_v2_pattern_statistics.json');stats=json.loads(report.read_text())
    assert datetime.fromisoformat(stats['generated_at'])<now
    def find(k,**kw):
        return next((x for x in stats[k] if all(float(x[t])==float(v) if t.endswith('line') else x[t]==v for t,v in kw.items())),{})
    slots=rows(Path('data/normalized/research_v2_slot_ledger.jsonl'))
    slot=next((x for x in slots if x.get('football_day')==a.date and 'T15:00:' in x.get('scheduled_target_at','') and x.get('state')=='OBSERVED'),None)
    if not slot: raise ValueError('SCAN_DATA_UNAVAILABLE')
    snaps=[x for x in rows(Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')) if x.get('football_day')==a.date and x.get('scheduled_target_at')==slot['scheduled_target_at']]
    assert len(snaps)==slot['strict_snapshots'] and len({s['fixture_id'] for s in snaps})==len(snaps)
    health=json.load(open('reports/scan_health_latest.json'))
    h=next((x for x in health['recent_reports'] if x.get('scheduled_target_at')==slot['scheduled_target_at']),{})
    predictions=[];review=[]
    for s in snaps:
        reasons=[];picks=[]
        if not s.get('mainline_verified') or datetime.fromisoformat(s['observed_at'])>=datetime.fromisoformat(s['kickoff']): reasons.append('UNVERIFIED_PREMATCH')
        if datetime.fromisoformat(s['kickoff'])<=now: reasons.append('KICKOFF_PASSED')
        side='HOME_FAVORITE' if s['favorite_side']=='H' else 'AWAY_FAVORITE';line=s['ah']['selected_side_line'];ou=s['ou']['line']
        b=find('baseline_by_market_side_line',market_side=side,ah_line=line)
        p=find('market_state_by_side_line_price',market_side=side,ah_line=line,ah_price_bucket=bucket(s['ah']['selected_side_price']))
        c=find('real_ou_combo_by_ah_line_and_ou_line',market_side=side,ah_line=line,ou_line=ou)
        q=find('real_ou_paired_by_line_over_price_bucket',ou_line=ou,over_price_bucket=bucket(s['ou']['over_price']))
        evidence=dict(section_1_line=b,section_1_price=p,section_2_ou=q,section_3_4_context=c,ah_price_band=bucket(s['ah']['selected_side_price']),over_price_band=bucket(s['ou']['over_price']),baseline_weighted_wr=weighted(b),price_weighted_wr=weighted(p),ou_over_weighted_wr=weighted(q,'over_'),ou_under_weighted_wr=weighted(q,'under_'),context_over_weighted_wr=weighted(c,'over_'),context_under_weighted_wr=weighted(c,'under_'))
        ah=b.get('n',0)>=100 and p.get('n',0)>=40 and c.get('ah_n',0)>=20 and (weighted(b) or 0)>=55 and (weighted(p) or 0)>=55 and c.get('ah_favorite_win_pct',0)>=53
        if ah:picks.append(('AH','HOME' if s['favorite_side']=='H' else 'AWAY',line))
        for d in ['over','under']:
            if q.get('n',0)>=60 and c.get('n',0)>=30 and (weighted(q,d+'_') or 0)>=55 and (weighted(c,d+'_') or 0)>=55:picks.append(('OU',d.upper(),ou))
        for market,selection,ln in picks if not reasons else []:
            pred={k:s[k] for k in ['fixture_id','home','away','league','kickoff']}
            pred.update(id=a.date.replace('-','')+'-'+s['fixture_id']+'-'+market,episode_id='matchledger-'+a.date,market=market,selection=selection,line=ln,tier='EDITORIAL_RESEARCH_LEAN',confidence='CAUTIOUS',snapshot_at=s['observed_at'],source_commit=a.source_commit,snapshot_sha256=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest(),evidence=evidence)
            predictions.append(pred)
        review.append(dict(snapshot=s,evidence=evidence,eligible=not reasons,exclusions=reasons,editorial_ah_pass=ah,selected_markets=[v[0] for v in picks] if not reasons else [],decision='SELECTED_EDITORIAL_LEAN' if picks and not reasons else 'NO_PICK'))
    predictions.sort(key=lambda p:(p['kickoff'],p['home'],p['market']))
    data=dict(date=a.date,published_at=now.isoformat(),source_type='REVIEWED_PREDICTION',episode_id='matchledger-'+a.date,statistics_generated_at=stats['generated_at'],source_commit=a.source_commit,predictions=predictions,scan=slot)
    append_ledger(ep/'prediction-ledger.jsonl',data,snaps)
    ledger=read_ledger(ep/'prediction-ledger.jsonl'); byid={r['prediction']['id']:r for r in ledger}
    for p in predictions:p['actual_recorded_at']=byid[p['id']]['recorded_at']
    previous=[]
    for d in sorted(ep.parent.iterdir()):
        if d.name<a.date and (d/'prediction-ledger.jsonl').exists():previous+=read_ledger(d/'prediction-ledger.jsonl')
    ids={r['prediction']['fixture_id'] for r in previous}
    results=[x for x in rows(Path('data/normalized/oddspapi_finished_results.jsonl')) if x['fixture_id'] in ids]
    conflicts=rows(Path('data/normalized/oddspapi_finished_results.conflicts.jsonl'))
    assert not ({x['fixture_id'] for x in conflicts}&ids)
    settlement=summarize(previous,results,a.date)
    qa=dict(strict_snapshots=len(snaps),cohort_fixtures=slot['football_day_fixtures'],eligible_fixtures=sum(x['eligible'] for x in review),selected_predictions=len(predictions),selected_fixture_ids=sorted({p['fixture_id'] for p in predictions}),scan_health=h.get('status',h.get('scan_health','NOT_RECOVERED_FOR_15_SLOT')),source_commit=a.source_commit,statistics_generated_at=stats['generated_at'],statistical_cutoff='PRE_EXISTING_REPORT_BEFORE_SCAN',recorded_at=now.isoformat(),reviewed_all_snapshots=True,prior_chat_coverage='Search found no additional evidenced picks; cannot certify every historical chat was recovered.',historical_scope='Verified ledgers 2026-11-04 and 2026-11-05 only',editorial_filters='Unchanged from 2026-11-05: AH baseline N>=100/WR>=55, price N>=40/WR>=55, context N>=20/positive-return>=53. OU N>=60 and context N>=30, both weighted WR>=55. Not frozen promotion gates.')
    for name,obj in [('daily.json',data),('prediction-manifest.json',data),('all-fixture-analysis.json',review),('ft-settlement-report.json',settlement),('ft-source-evidence.json',results),('data-qa.json',qa),('scan-evidence.json',dict(slot=slot,health=h))]:
        (ep/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
    print(json.dumps(dict(qa=qa,picks=[dict(match=p['home']+' v '+p['away'],market=p['market'],selection=p['selection'],line=p['line'],kickoff=p['kickoff']) for p in predictions],results=settlement),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
