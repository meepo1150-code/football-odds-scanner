"""Evidence-backed retirement of unresolved fixtures; raw observations never deleted."""
from .research_population import in_scope, exclusion_reason, POLICY
import hashlib
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from .research_v2_integrity import trusted_snapshot

STATE=Path('data/normalized/result_recovery_attempts.json')
RETIRED=Path('data/normalized/research_v2_retired_fixtures.jsonl')
SNAP=Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
RESULTS=Path('data/normalized/oddspapi_finished_results.jsonl')

# User-authorized triage of the existing backlog, not a future collection ban.
LOW_TIER_REVIEW_CUTOFF='2026-10-02T07:21:00+00:00'
LOW_TIER_LEAGUES={
    'Germany - Regionalliga North': ('REGIONAL_TIER_4', 'https://www.nordfv.de/spielbetrieb/ligen/herren-regionalliga-nord/'),
    'Slovenia - 3. SNL': ('REGIONAL_TIER_3', 'https://www.nzs.si/klubi/moski/3-slovenska-nogometna-liga-vzhod/vsebine?type=news'),
    'India - Bangalore Super Division': ('STATE_OR_CITY_LEAGUE', 'https://www.the-aiff.com/'),
    'India - Mizoram Premier League': ('STATE_LEAGUE', 'https://theawayend.co/mizoram-premier-league/'),
    'Israel - Liga Alef': ('REGIONAL_TIER_3', 'https://en.wikipedia.org/wiki/Liga_Alef'),
}



def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def utc(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except ValueError:return None


def state(root):
    return json.loads((root/STATE).read_text()) if (root/STATE).exists() else {'rounds':{},'fixtures':{}}


def save(root,data):
    p=root/STATE;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,separators=(',',':'),sort_keys=True)+'\n')


def retired_ids(root):
    return {str(r['fixture_id']) for r in rows(root/RETIRED)}


def fingerprint(round_,kickoff):
    when=utc(round_['recorded_at']);ko=utc(kickoff)
    if not when or not ko:return None
    days=[(ko+timedelta(days=d)).date().isoformat() for d in (-1,0,1)]
    proof=round_['days']
    if any(day not in proof for day in days):return None
    return (round_['provider'],*(proof[day] for day in days))


def record(root,provider,report,snapshots=None,results=None,proof_commit=None,recorded_at=None,legacy_direct=False):
    """Only successful covered days count; identical cache evidence counts once."""
    when=utc(report.get('generated_at') or recorded_at)
    if not when:return
    days={}
    if legacy_direct:
        failed={x.get('day') for x in report.get('request_failures',[])}
        days={d:'git:'+proof_commit for d in report.get('days_requested',[]) if d not in failed}
    else:
        for e in report.get('fetch_evidence',[]):
            fetched=utc(e.get('fetched_at'))
            if e.get('source') in ('NETWORK','CACHE') and fetched and fetched<=when:
                days[e['day']]=fetched.isoformat()
    if not days:return
    data=state(root)
    round_={'provider':provider,'recorded_at':when.isoformat(),'days':days,'proof_commit':proof_commit,'report_path':f'reports/{provider}_result_backfill.json'}
    rid=hashlib.sha256(json.dumps(round_,sort_keys=True).encode()).hexdigest()[:16]
    data['rounds'][rid]=round_
    known={str(r.get('fixture_id')) for r in (results if results is not None else rows(root/RESULTS))}
    snapshots=snapshots if snapshots is not None else rows(root/SNAP)
    for s in snapshots:
        fid=str(s.get('fixture_id') or '');ko=utc(s.get('kickoff'));observed=utc(s.get('observed_at'))
        if not fid or fid in known or not (trusted_snapshot(s) and in_scope(s)) or not ko or not observed or observed>when or when-ko<timedelta(hours=3):continue
        fp=fingerprint(round_,s.get('kickoff'))
        if not fp:continue
        # Cached source evidence predating maturity is not a recovery attempt.
        if not legacy_direct and any(utc(v)<ko+timedelta(hours=3) for v in fp[1:]):continue
        attempts=data['fixtures'].setdefault(fid,[])
        if any(fingerprint(data['rounds'][old],s['kickoff'])==fp for old in attempts):continue
        attempts.append(rid)
    save(root,data)


def merge(staged,root):
    old=state(root);new=state(staged);old['rounds'].update(new['rounds'])
    for fid,ids in new['fixtures'].items():old['fixtures'][fid]=list(dict.fromkeys(old['fixtures'].get(fid,[])+ids))
    save(root,old)


def review(root=Path('.'),now=None):
    now=now or datetime.now(timezone.utc)
    for provider in ('fotmob','espn'):
        p=root/'reports'/f'{provider}_result_backfill.json'
        if p.exists():record(root,provider,json.loads(p.read_text()))
    data=state(root);known={str(r.get('fixture_id')) for r in rows(root/RESULTS)}
    blocked={str(r.get('fixture_id')) for r in rows((root/RESULTS).with_suffix('.conflicts.jsonl'))}
    snapshots={};identities={}
    for s in rows(root/SNAP):
        if not (trusted_snapshot(s) and in_scope(s)):continue
        fid=str(s.get('fixture_id'));snapshots[fid]=s
        identities.setdefault(fid,set()).add(tuple(s.get(k) for k in ('home','away','kickoff','league')))
    retired=[];pending=[]
    for fid,s in snapshots.items():
        ko=utc(s.get('kickoff'))
        if fid in known or not ko or now-ko<timedelta(hours=3):continue
        unique={}
        for rid in sorted(data['fixtures'].get(fid,[]),key=lambda rid:data['rounds'][rid]['recorded_at']):
            fp=fingerprint(data['rounds'][rid],s['kickoff'])
            if fp:unique.setdefault(fp,rid)
        ids=list(unique.values());data['fixtures'][fid]=ids
        proofs=[data['rounds'][r] for r in ids];times=[utc(r['recorded_at']) for r in proofs];providers={r['provider'] for r in proofs}
        low_tier=LOW_TIER_LEAGUES.get(s.get('league'))
        scope_excluded=bool(low_tier and ko<=utc(LOW_TIER_REVIEW_CUTOFF)
                            and s.get('home') and s.get('away') and fid not in blocked
                            and len(ids)>=4 and len(providers)>=2 and len(identities[fid])==1)
        eligible=scope_excluded or (fid not in blocked and len(ids)>=4 and len(providers)>=2 and now-ko>=timedelta(hours=72)
                  and max(times)-min(times)>=timedelta(hours=24) and len(identities[fid])==1)
        item={'fixture_id':fid,'home':s.get('home'),'away':s.get('away'),'league':s.get('league'),'kickoff':s.get('kickoff'),'attempt_count':len(ids),'round_ids':ids,'sources':sorted(providers),'reviewed_at':now.isoformat()}
        if eligible:
            item.update(status='RETIRED_UNRESOLVED',reason=('MISSING_TEAM_IDENTITY_AFTER_EXHAUSTED_RECOVERY' if not s.get('home') or not s.get('away') else 'NO_VERIFIED_90_MINUTE_RESULT_AFTER_4_PLUS_DISTINCT_ROUNDS_AND_2_SOURCES'),raw_preserved=True)
            if scope_excluded:
                item.update(reason='LOW_TIER_SCOPE_EXCLUSION_AFTER_EXHAUSTED_RECOVERY',
                            scope_policy='EXISTING_BACKLOG_2026_10_02',
                            league_classification=low_tier[0], classification_source=low_tier[1],
                            scope_cutoff=LOW_TIER_REVIEW_CUTOFF)
            retired.append(item)
        else:
            unmet=[]
            if fid in blocked:unmet.append('RESULT_CONFLICT')
            if len(ids)<4:unmet.append('MINIMUM_DISTINCT_ROUNDS')
            if len(providers)<2:unmet.append('MINIMUM_SOURCES')
            if now-ko<timedelta(hours=72):unmet.append('MINIMUM_AGE_72H')
            if not times or max(times)-min(times)<timedelta(hours=24):unmet.append('MINIMUM_ATTEMPT_SPAN_24H')
            if len(identities[fid])!=1:unmet.append('INCONSISTENT_IDENTITY')
            item.update(unmet_gates=unmet,age_eligible_at=(ko+timedelta(hours=72)).isoformat())
            item.update(status='ACTIVE_UNRESOLVED',reason='RESULT_CONFLICT_REQUIRES_REVIEW' if fid in blocked else 'MISSING_IDENTITY' if not s.get('home') or not s.get('away') else 'RETIREMENT_EVIDENCE_OR_AGE_GATE_NOT_MET')
            pending.append(item)
    save(root,data)
    p=root/RETIRED;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in retired))
    report={'generated_at':now.isoformat(),'matured_unresolved_total':len(retired)+len(pending),'retired_from_active_queue':len(retired),'active_matured_unresolved':len(pending),'raw_deleted':0,'settled_results_deleted':0,'low_tier_scope_exclusions':sum(r['reason']=='LOW_TIER_SCOPE_EXCLUSION_AFTER_EXHAUSTED_RECOVERY' for r in retired),'low_tier_scope_cutoff':LOW_TIER_REVIEW_CUTOFF,'minimum_distinct_rounds':4,'minimum_sources':2,'minimum_age_hours':72,'minimum_attempt_span_hours':24,'pending':pending}
    p=root/'reports/result_recovery_review.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    print(json.dumps({k:v for k,v in review().items() if k!='pending'}))
