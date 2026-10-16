"""Offline fixture-slot reconstruction. Unknown membership is never a gap.

Inputs come from Git blobs, not a mutable checkout. Outputs are exclusive-created
inside this research package. No network, credentials, scheduler or live writes.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, time, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

BASE='b6976e2f667ab7e245e4e091f6ef352bd6b65d15'
START='564ec452b50725fb7b472b9f1c1068790a57beee'
ASOF='2026-10-16T08:52:42+07:00'
BKK=ZoneInfo('Asia/Bangkok')
P='data/normalized/'
SNAPS=['europe_pinnacle_research_v2_snapshots.jsonl','v2_mainline_snapshots.jsonl','europe_discovery_snapshots.jsonl']
AUDIT='europe_pinnacle_research_v2_audit.jsonl'
LEDGER='research_v2_slot_ledger.jsonl'
RAW='research_v2_provider_responses.jsonl'
DAILY='research_v2_daily_fixtures.jsonl'
LEVANTE='id1000000872478578'
POLICIES=[
 ('2026-09-23T15:26:06+07:00','LEGACY','2cc081de1b62ee2c5299b12f9aed15ada64cb89a'),
 ('2026-10-12T20:53:32+07:00','V2','deb33d81d49474de5442ac876fccfa12303a07da'),
 ('2026-10-12T23:21:22+07:00','V3','5983b6314ae53074c9db5f26ebe649f2f2dcd93a'),
 ('2026-10-13T21:47:16+07:00','V4','23714e8a0629de61c20df745f10d4a7cd73c2e02'),
 ('2026-10-14T19:13:44+07:00','FIXED_1500','6503f0a7ec397c3dd10eb339c0681d31cce66bcc')]

def stamp(v):
    try:
        d=datetime.fromisoformat(str(v).replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError,TypeError):return None

def enc(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def sha(v):return hashlib.sha256(v if isinstance(v,bytes) else enc(v).encode()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a])
def blob(ref,path):
    r=subprocess.run(['git','show',ref+':'+path],capture_output=True)
    return r.stdout if r.returncode==0 else b''

def parse(data):
    out=[];dec=json.JSONDecoder()
    for i,line in enumerate(data.decode().splitlines(),1):
        s=line.strip()
        while s:
            r,end=dec.raw_decode(s)
            if not isinstance(r,dict):raise ValueError('NON_OBJECT')
            out.append((i,r));s=s[end:].lstrip()
            if s.startswith('\\n'):s=s[2:].lstrip()
    return out

def collect(name,history=False):
    path=P+name;refs=[BASE]
    if history:refs+=git('log','--first-parent','--format=%H',BASE,'--',path).decode().splitlines()
    result={};versions=[];seen=set()
    for ref in refs:
        b=blob(ref,path);h=sha(b)
        if h in seen:continue
        seen.add(h);rr=parse(b)
        versions.append(dict(commit=ref,path=path,sha256=h,bytes=len(b),rows=len(rr)))
        for line,r in rr:
            rh=sha(r)
            result.setdefault(rh,dict(row=r,baseline=ref==BASE,evidence=dict(commit=ref,path=path,line=line,row_sha256=rh)))
    return list(result.values()),versions

def policy(t):
    pp=[p for p in POLICIES if stamp(p[0])<=t]
    return pp[-1] if pp else (None,'UNKNOWN_POLICY',None)

def scheduled(t):
    _,v,_=policy(t);loc=t.astimezone(BKK);weekend=(loc-timedelta(hours=6)).weekday()>=5;h=loc.hour
    if v=='UNKNOWN_POLICY':return None
    if v=='LEGACY':return h in ((12,15,18,19,20,21,22) if weekend else (18,21))
    if v=='V2':return h in ((15,18,21,0) if weekend else (18,21))
    if v=='V3':return h in (15,18,21) or (h==0 and weekend)
    return h in (15,18,21,0)

def targets(day):
    d=datetime.fromisoformat(day).date()
    return [datetime.combine(d,time(h),BKK).astimezone(timezone.utc) for h in (12,15,18,19,20,21,22)]+[datetime.combine(d+timedelta(days=1),time(0),BKK).astimezone(timezone.utc)]

def valid(r):
    try:
        a=r['ah'];hl,al,hp,ap=[a[k] for k in ('home_line','away_line','home_price','away_price')]
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (hl,al,hp,ap)):return False
        if r.get('provider')=='propline' and r.get('source_semantics')!='PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE':return False
        return abs(hl+al)<1e-8 and abs(hl*4-round(hl*4))<1e-8 and hp>1 and ap>1 and stamp(r['observed_at'])<stamp(r['kickoff'])
    except (KeyError,TypeError,ValueError):return False

def classify(expected,t,ko,now,complete=False,reasons=(),conflict=False):
    if t>now:return 'NOT_EXPECTED','FUTURE_NOT_DUE'
    if t>=ko:return 'NOT_EXPECTED','KICKOFF_CUTOFF'
    if conflict:return 'UNMATCHED','IDENTITY_CONFLICT'
    if complete:return 'COMPLETE','EXACT_TWO_SIDED_AH'
    if expected is False:return 'NOT_EXPECTED','POLICY_OR_COHORT_EXCLUSION'
    if expected is None:return 'UNKNOWN_EVIDENCE','UNKNOWN_EXPECTED_MEMBERSHIP'
    if 'KICKOFF_NOT_FUTURE' in reasons:return 'SCAN_FAILED','ACTUAL_ATTEMPT_AFTER_KICKOFF'
    if set(reasons)&{'MASTER_CLUB_UNMAPPED','AMBIGUOUS_OR_MISSING_1X2','NOT_PREMATCH_WITH_ODDS'}:return 'UNKNOWN_EVIDENCE','REJECTION_NOT_AH_ABSENCE_PROOF'
    if set(reasons)&{'AH_OUTSIDE_CORE_PRICE','AH_CORE_PRICE','PROPLINE_AH_SEMANTICS_UNVERIFIED'}:return 'UNMATCHED','PRICE_OR_SEMANTICS_QUARANTINE'
    if set(reasons)&{'API_FAILURE','UNQUERIED','SKIPPED_QUOTA'}:return 'SCAN_FAILED','EXPLICIT_FAILED_FIXTURE_ATTEMPT'
    if 'NO_FIXTURE_IN_PROVIDER_RESPONSE' in reasons:return 'MISSING_SLOT','EXPLICIT_COHORT_RESPONSE_ABSENCE'
    if 'BOOKMAKER_NOT_ACTIVE' in reasons:return 'NO_PRICE','BOOKMAKER_NOT_ACTIVE'
    return 'UNKNOWN_EVIDENCE','NO_EXHAUSTIVE_FIXTURE_LEVEL_EVIDENCE'

def save(path,v,jsonl=False):
    root=Path(__file__).resolve().parent
    if not path.resolve().is_relative_to(root):raise ValueError('RESEARCH_OUTPUT_ONLY')
    b=(''.join(enc(r)+'\n' for r in v) if jsonl else json.dumps(v,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=b:raise ValueError('IMMUTABLE_CONFLICT')
    else:
        with path.open('xb') as f:f.write(b)

def run(out):
    now=stamp(ASOF);sources={};versions=[]
    for n in [*SNAPS,AUDIT,LEDGER,DAILY,RAW]:
        sources[n],vv=collect(n,n in SNAPS or n==AUDIT);versions+=vv
    rec=defaultdict(list);observed=set();attempted=set();actual=[];keys=set();sn=defaultdict(list);au=defaultdict(list);de=defaultdict(list);co=defaultdict(set)
    def add(r,e,kind):
        fid=str(r.get('fixture_id') or '')
        if fid:rec[fid].append((r,e,kind))
        if kind=='snapshot':observed.add(fid)
        if kind in ('audit','cohort'):attempted.add(fid)
    for n in SNAPS:
        for x in sources[n]:
            r=x['row'];obs=stamp(r.get('observed_at'));t=stamp(r.get('scheduled_target_at'));fid=str(r.get('fixture_id'))
            if not obs or obs>now:continue
            add(r,x['evidence'],'snapshot');key=(fid,r.get('bookmaker'),obs,sha(r.get('ah')))
            if key in keys:continue
            keys.add(key);a=dict(fixture_id=fid,bookmaker=r.get('bookmaker'),observed_at=obs.isoformat(),target=t.isoformat() if t else None,valid_ah=valid(r),baseline=x['baseline'],evidence=x['evidence'])
            actual.append(a)
            if t and t<=obs<=t+timedelta(minutes=150) and valid(r):sn[fid,t].append(a)
    for x in sources[AUDIT]:
        r=x['row'];add(r,x['evidence'],'audit');t=stamp(r.get('scheduled_target_at'));obs=stamp(r.get('observed_at'))
        if t and obs and t<=obs<=min(now,t+timedelta(minutes=150)):au[str(r.get('fixture_id')),t].append(x)
    for x in sources[DAILY]:add(x['row'],x['evidence'],'discovery')
    ledger=[x['row'] for x in sources[LEDGER]]
    for x in sources[LEDGER]:
        r=x['row'];t=stamp(r.get('scheduled_target_at'))
        if not t:continue
        for f in r.get('daily_cohort_fixtures') or []:
            add(f,x['evidence'],'cohort');de[str(f['fixture_id']),t].append(f)
            if r.get('daily_cohort_policy')=='FIXED_1500_FIXTURE_COHORT_V1':co[r['football_day']].add(str(f['fixture_id']))
    # Retained raw responses are inventoried and decoded without converting fetch time to quote time.
    catalog=json.loads(Path('research/historical_backfill/reports/reviewed_catalog.json').read_text());raw_ah=[]
    for x in sources[RAW]:
        r=x['row'];payload=r['payload'];payload=payload if isinstance(payload,list) else payload.get('data',[])
        obs=stamp(r.get('observed_at'));tt={stamp(z.get('scheduled_target_at')) for z in ledger if stamp(z.get('request_completed_at') or z.get('actual_observed_at'))==obs}
        t=next(iter(tt)) if len(tt)==1 else None
        for f in payload:
            fid=str(f.get('fixtureId'));ko=stamp(f.get('startTime'))
            if r.get('endpoint')=='/fixtures':
                add(dict(fixture_id=fid,kickoff=f.get('startTime'),home=f.get('participant1Name'),away=f.get('participant2Name'),league=f.get('tournamentName'),discovered_at=r['observed_at']),x['evidence'],'discovery')
            if r.get('endpoint')!='/odds-by-tournaments' or not t or not obs or not ko or not t<=obs<ko or obs>now:continue
            b=f.get('bookmakerOdds',{}).get('pinnacle',{})
            if f.get('statusId')!=0 or b.get('bookmakerIsActive') is not True:continue
            for m in catalog:
                market=b.get('markets',{}).get(str(m['market_id']),{})
                if market.get('marketActive') is not True:continue
                qs={s:market.get('outcomes',{}).get(str(m[s+'_outcome_id']),{}).get('players',{}).get('0',{}) for s in ('home','away')}
                if not all(isinstance(q,dict) and q.get('active') is True and type(q.get('price')) in (int,float) and math.isfinite(q['price']) and q['price']>1 for q in qs.values()):continue
                a=dict(fixture_id=fid,bookmaker='pinnacle',observed_at=obs.isoformat(),target=t.isoformat(),market_id=m['market_id'],home_line=m['home_line'],quotes=qs,evidence=x['evidence'],line_selection='ALL_LINES_NO_MAINLINE_CLAIM')
                raw_ah.append(a)
                if not any(z['observed_at']==a['observed_at'] for z in sn[fid,t]):sn[fid,t].append(a)
    first=min(stamp(a['observed_at']) for a in actual);inventory=[];matrix=[];gaps=[]
    evidence_targets=defaultdict(set)
    for ff,t in set(sn)|set(au)|set(de):evidence_targets[ff].add(t)
    for fid,rr in sorted(rec.items()):
        kos=sorted({stamp(r.get('kickoff')) for r,e,k in rr if stamp(r.get('kickoff'))})
        if not kos or all(k<first-timedelta(days=1) for k in kos):continue
        ko=kos[-1];r=next((r for r,e,k in rr if r.get('home') and r.get('away')),rr[0][0])
        pairs={(str(r.get('home_participant_id')),str(r.get('away_participant_id'))) for r,e,k in rr if r.get('home_participant_id') and r.get('away_participant_id')};conflict=len(pairs)>1
        f=dict(provider_fixture_id=fid,canonical_identity='PROVIDER_NAMESPACE_ONLY_NO_FUZZY_JOIN',home=r.get('home'),away=r.get('away'),league=r.get('league'),kickoff_versions=[k.isoformat() for k in kos],original_kickoff_utc=kos[0].isoformat(),current_kickoff_utc=ko.isoformat(),kickoff_changed=len(kos)>1,identity_conflict=conflict,production_evidence=fid in observed|attempted,mapping_evidence=[e for r,e,k in rr[:3]],lifecycle='POSTPONED' if fid==LEVANTE else 'UNVERIFIED')
        if fid==LEVANTE:f.update(current_kickoff_utc='2026-10-21T18:00:00+00:00',settlement_blocked=True)
        inventory.append(f);days={r.get('football_day') for r,e,k in rr if isinstance(r.get('football_day'),str)}|{(k.astimezone(BKK)-timedelta(hours=6)).date().isoformat() for k in kos}
        ts={t for d in days if first.astimezone(BKK).date().isoformat()<=d<='2026-10-16' for t in targets(d)}|evidence_targets[fid]
        for t in sorted(ts):
            if t<first or t.astimezone(BKK).date().isoformat()>'2026-10-17':continue
            day=(t.astimezone(BKK)-timedelta(hours=6)).date().isoformat();pt,pv,pc=policy(t);sched=scheduled(t)
            direct=any(a['evidence']['path']==P+SNAPS[0] for a in sn[fid,t]) or bool(au[fid,t] or de[fid,t]);cohort=fid in co[day] and pv=='FIXED_1500'
            expected=False if sched is False else True if sched and (direct or cohort) else None
            if pv=='FIXED_1500' and co[day] and fid not in co[day]:expected=False
            if len(kos)>1:expected=None
            reasons=[a['row'].get('eligibility_reason') for a in au[fid,t]]+[a.get('reason') for a in de[fid,t]]
            state,reason=classify(expected,t,ko,now,bool(sn[fid,t]),reasons,conflict)
            if fid==LEVANTE and state not in ('COMPLETE','NOT_EXPECTED'):state,reason='POSTPONED','FT_SETTLEMENT_BLOCKED'
            row=dict(fixture_id=fid,home=f['home'],away=f['away'],league=f['league'],kickoff_utc=ko.isoformat(),slot_utc=t.isoformat(),slot_bangkok=t.astimezone(BKK).isoformat(),football_day=day,policy_version=pv,policy_commit=pc,policy_deployed_at=pt,expected=expected,status=state,reason=reason,actual_observation_count=len({a['observed_at'] for a in sn[fid,t]}),observed_evidence=[a['evidence'] for a in sn[fid,t]],attempt_evidence=[a['evidence'] for a in au[fid,t]],membership='EXACT_ATTEMPT_OR_DEPLOYED_COHORT' if direct or cohort else 'UNKNOWN_EXPECTED_MEMBERSHIP')
            matrix.append(row)
            if expected is True and state in ('MISSING_SLOT','SCAN_FAILED','NO_PRICE'):
                eligible=fid.startswith('id') and not conflict and len(kos)==1 and fid!=LEVANTE
                gaps.append(dict(**row,bookmaker='pinnacle',required_market='FULL_MATCH_AH',provider_fixture_id=fid if eligible else None,mapping_evidence=f['mapping_evidence'],recovery_eligible=eligible,exclusion_reason=None if eligible else 'IDENTITY_OR_LIFECYCLE_UNRESOLVED',deduplication_key=sha([fid,t.isoformat(),'pinnacle','AH']),scope='ALL_RETAINED_GIT_SOURCES_NOT_EXHAUSTIVE_EXTERNAL_STORES'))
    assert len(gaps)==len({g['deduplication_key'] for g in gaps})
    by_fixture=defaultdict(list)
    for r in matrix:by_fixture[r['fixture_id']].append(r)
    for f in inventory:
        mm=by_fixture[f['provider_fixture_id']]
        f['expected_slots_lower_bound']=[r['slot_utc'] for r in mm if r['expected'] is True and stamp(r['slot_utc'])<=now and stamp(r['slot_utc'])<stamp(r['kickoff_utc'])]
        f['status_counts']=dict(Counter(r['status'] for r in mm))
    known=[r for r in matrix if r['expected'] is True and stamp(r['slot_utc'])<=now and stamp(r['slot_utc'])<stamp(r['kickoff_utc'])]
    summary=dict(baseline_sha=BASE,start_sha=START,audit_asof=ASOF,earliest_verified_live_ah_at=first.isoformat(),inventory_provider_ids=len(inventory),production_evidence_provider_ids=sum(f['production_evidence'] for f in inventory),matrix_rows=len(matrix),expected_slots_lower_bound=len(known),expected_status_counts=dict(Counter(r['status'] for r in known)),all_status_counts=dict(Counter(r['status'] for r in matrix)),gap_manifest_rows=len(gaps),gap_status_counts=dict(Counter(r['status'] for r in gaps)),observed_evidence_records=len(actual),baseline_observed_records=sum(a['baseline'] for a in actual),historical_only_evidence_records=sum(not a['baseline'] for a in actual),raw_ah_ladder_records=len(raw_ah),new_api_requests=0,audit_complete=False,production_import_approved=False)
    for n,v in [('fixture_inventory',inventory),('expected_actual_matrix',matrix),('missing_slot_manifest',gaps),('observed_evidence',actual),('raw_ah_ladder',raw_ah),('source_versions',versions)]:save(out/(n+'.jsonl'),v,True)
    paths=git('ls-tree','-r','--name-only',BASE,'data/normalized','reports','.github/workflows').decode().splitlines()
    save(out/'source_inventory.json',dict(paths=paths,excluded_as_live_slot_proof=['oddspapi_history_ticks and shards: imported historical ticks','history.csv/multimarket_history.csv: backtest','five_dollar_snapshots: opening/latest only, no scan timestamps'],policy_timeline=POLICIES))
    save(out/'summary.json',summary);return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.output),indent=2))
