"""Validate staged identities and evidence without network calls or activation."""
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
EXPECTED={'JPN-0003':20,'KOR-0003':14,'CHN-0001':16,'CHN-0002':16,'IDN-0001':18,
          'MYS-0001':12,'VNM-0001':14,'SAU-0002':18,'ARE-0001':14,'QAT-0001':12,
          'USA-0002':25,'CAN-0001':8,'ARG-0002':36,'CHL-0001':16,'COL-0001':20,
          'URY-0001':16,'ECU-0001':16,'PRY-0001':12,'PER-0001':18,'BOL-0001':16}
DOMAINS={'JPN':'www.jleague.jp','KOR':'www.kfa.or.kr','CHN':'api.cfl-china.cn',
         'IDN':'www.ligaindonesiabaru.com','MYS':'www.malaysianfootballleague.com',
         'VNM':'vpf.vn','SAU':'www.saff.com.sa','ARE':'uaeproleague.ae','QAT':'www.qsl.qa',
         'USA':'www.rhodeislandfc.com','CAN':'www.cplsoccer.com','ARG':'www.afa.com.ar',
         'CHL':'www.campeonatochileno.cl','COL':'www.dimayor.com.co','URY':'www.auf.org.uy',
         'ECU':'ligapro.ec','PRY':'www.apf.org.py','PER':'liga1.pe','BOL':'fbf.com.bo'}


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',s).casefold()
                   if c.isalnum() and not unicodedata.combining(c))


def audit(root=ROOT, repo=REPO):
    errors=[]
    def check(ok,msg):
        if not ok:errors.append(msg)
    def js(name):return json.loads((root/name).read_text())
    def rows(path):
        with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
    def table(name):
        data=rows(root/name)
        check(all(all(v is not None and v!='' for v in r.values()) for r in data),'Missing field: '+name)
        return data
    def unique(data,keys,label):
        check(len({tuple(r[k] for k in keys) for r in data})==len(data),'Duplicate '+label)
    base=js('baseline.json')
    for path,digest in base['continuous_hashes'].items():
        p=repo/path
        check(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,'Baseline changed: '+path)
    old_comps=rows(repo/'data/master/competitions.csv')+rows(repo/'data/research/global_master_phase1/competitions.csv')
    old_clubs=rows(repo/'data/master/uefa_clubs_canonical.csv')+rows(repo/'data/research/global_master_phase1/clubs_canonical.csv')
    old_countries=rows(repo/'data/master/countries.csv')+rows(repo/'data/research/global_master_phase1/countries.csv')
    comps=table('competitions.csv');clubs=table('clubs_canonical.csv');countries=table('countries.csv')
    members=table('verified_memberships.csv');proj=table('memberships.csv');seasons=table('seasons.csv');assign=table('club_assignments.csv')
    rosters=js('evidence/rosters.json');ledger=js('evidence/identity_ledger.json')
    aliases=js('evidence/aliases.json');special=js('evidence/special_identities.json')
    candidates=js('evidence/provider_candidates.json');participants=js('evidence/participant_candidates.json')
    changes=js('evidence/change_review.json');associations=js('evidence/associations.json')
    cm={r['competition_id']:r for r in comps};cl={c['club_id']:c for c in clubs};em={r['competition_id']:r for r in rosters}
    for data,keys,label in [(comps,['competition_id'],'competition'),(clubs,['club_id'],'club ID'),(countries,['country_id'],'country'),(members,['season','competition_id','club_id'],'membership'),(members,['season','club_id'],'domestic club membership'),(seasons,['competition_id','season'],'season'),(rosters,['competition_id'],'roster'),(ledger,['club_id'],'ledger'),(aliases,['competition_id','alias','club_id'],'alias')]:unique(data,keys,label)
    check(set(cm)==set(em)==set(EXPECTED),'Twenty-league scope mismatch')
    check(not(set(cm)&{c['competition_id'] for c in old_comps}),'Existing competition duplicated')
    check(not(set(cl)&{c['club_id'] for c in old_clubs}),'Existing club ID overwritten')
    check([r for r in old_comps if r['status']=='EXCLUDED_USER']==base['excluded_user'],'EXCLUDED_USER changed')
    check(not(set(cm)&{c['competition_id'] for c in base['excluded_user']}),'EXCLUDED_USER reintroduced')
    country_ids={c['country_id'] for c in countries}|{c['country_id'] for c in old_countries}
    check(all(c['country_id'] in country_ids and re.fullmatch('[A-Z]{3}-[0-9]{4}',c['competition_id']) and c['competition_id'].startswith(c['country_id']+'-') and c['status']=='REVIEW' for c in comps),'Invalid or activated competition')
    for c in countries:
        old=next((x for x in old_countries if x['country_id']==c['country_id']),None)
        check(c==old if old else c['status']=='REVIEW','Country changed or activated')
    unique(old_clubs+clubs,['country_id','canonical_name'],'club name')
    keys=Counter((c['country_id'],norm(c['canonical_name'])) for c in old_clubs+clubs if c['season_membership_status']!='RESERVED_DUPLICATE_ALIAS')
    check(all(n==1 for n in keys.values()),'Duplicate normalized identity')
    check(all(re.fullmatch('[A-Z]{3}-[A-Z]{3}',c['club_id']) and c['club_id'].startswith(c['country_id']+'-') and c['canonical_club_id']==c['club_id'] and c['country_id'] in country_ids for c in clubs),'Club namespace or redirect invalid')
    lm={c['club_id']:c for c in ledger}
    check(set(lm)==set(cl),'Identity ledger coverage mismatch')
    for c in clubs:
        check(all(c[k]==lm.get(c['club_id'],{}).get(k) for k in ['club_id','country_id','canonical_name']),'Identity ledger changed')
    check(Counter((m['season'],m['competition_id'],m['club_id']) for m in members)==Counter((m['season'],m['competition_id'],m['team_id']) for m in proj),'Membership projection mismatch')
    check({m['club_id'] for m in members}==set(cl),'Orphan club')
    check({(c['country_id'],c['canonical_name'],c['club_id']) for c in ledger}=={(c['association_id'],c['source_name'],c['club_id']) for c in assign},'Assignment ledger mismatch')
    check({c['competition_id'] for c in changes}==set(EXPECTED) and len(changes)==20,'Change review coverage incomplete')
    for change in changes:
        r=em.get(change['competition_id'],{})
        check(change['expected_current_members']==r.get('names') and change['sources']==[r.get('source_url')]+r.get('supplementary_sources',[]) and change['legal_promotion_relegation_history']=='PARTIAL_NOT_EXHAUSTIVELY_CERTIFIED','Change review conflicts with evidence')
        check(not(set(change['excluded_from_current_membership'])&set(r.get('names',[]))),'Withdrawn club reintroduced')
    check({c['country_id'] for c in associations}=={c['country_id'] for c in comps} and len(associations)==19,'Association coverage incomplete')
    for association in associations:
        check(set(association['competition_ids'])=={c['competition_id'] for c in comps if c['country_id']==association['country_id']} and association['association_name'] and association['roster_authority_urls'],'Association competition mismatch')
    matrix=[]
    for r in rosters:
        cid=r['competition_id'];actual=[m for m in members if m['competition_id']==cid]
        check(r['expected_teams']==EXPECTED.get(cid)==len(r['names'])==len(set(r['names'])),'Independent expected count mismatch: '+cid)
        check(Counter(m['source_name'] for m in actual)==Counter(r['names']),'Official roster mismatch: '+cid)
        check(r['roster_facts_sha256']==hashlib.sha256(json.dumps(r['names'],ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),'Roster factual extract altered')
        check(len(r['clubs'])==len(r['names']) and {c['club_id'] for c in r['clubs']}=={m['club_id'] for m in actual},'Evidence identity coverage mismatch')
        check(all(c==lm.get(c['club_id']) for c in r['clubs']),'Evidence identity ledger mismatch')
        check(r['verification_status']=='VERIFIED_OFFICIAL' and r['checked_at']=='2026-10-15' and r['format'] and r['season_basis'] and r['source_type'].startswith('OFFICIAL_') and urlparse(r['source_url']).hostname==DOMAINS.get(r['country_id']),'Official evidence missing or wrong domain')
        check(r['activation_allowed'] is False,'Evidence activation prohibited')
        check(r['history_review_status']=='CURRENT_ROSTER_VERIFIED_HISTORY_PARTIAL','Unsupported legal history claim')
        check(r['season']==('2026-27' if r['country_id'] in {'JPN','IDN','MYS','VNM','SAU','ARE','QAT'} else '2026'),'Wrong current season')
        if r['country_id']=='CHN':
            check(all(x['competition_code']==('CSL' if cid=='CHN-0001' else 'CL1') and x['tournament_calendar_name']=='2026' for x in r['source_club_records']),'Chinese season binding mismatch')
            check([x['official_name'] for x in r['source_club_records']]==r['names'],'Chinese official identity mismatch')
        for m in actual:
            check(m['club_id'] in cl and m['competition_id'] in cm,'Membership foreign key invalid')
            check(m['country_id']==r['country_id'] and m['competition_name']==r['competition_name'],'Membership host mismatch')
            check(all(str(m[k])==str(r[k]) for k in ['season','division','source_url','checked_at','verification_status']),'Membership evidence mismatch')
            check(m['source_name']==lm.get(m['club_id'],{}).get('source_name'),'Source identity mismatch')
        matrix.append(dict(competition_id=cid,name=r['competition_name'],season=r['season'],clubs=len(actual),expected=EXPECTED.get(cid),missing=len(set(r['names'])-{m['source_name'] for m in actual})))
    check(len(seasons)==20 and {s['competition_id'] for s in seasons}==set(cm),'Season coverage incomplete')
    for s in seasons:
        r=em.get(s['competition_id'],{})
        check(all(s[k]==r.get(k) for k in ['season','verified_stages','source_url','verification_status','checked_at']) and s['temporal_state']=='CURRENT','Season evidence or stage mismatch')
    # Scoped alias labels cannot silently identify another club in the same competition.
    alias_ids={(c['competition_id'],norm(c['canonical_name'])):{c['club_id']} for c in ledger}
    for a in aliases:
        check(a['club_id'] in cl and lm.get(a['club_id'],{}).get('competition_id')==a['competition_id'] and a['verification_status']=='VERIFIED_OFFICIAL' and a['source_url'].startswith('https://') and a['basis'],'Invalid alias evidence')
        alias_ids.setdefault((a['competition_id'],norm(a['alias'])),set()).add(a['club_id'])
    check(all(len(v)==1 for v in alias_ids.values()),'Alias ambiguity')
    cross=[c for c in ledger if c['country_id']!=c['competition_id'][:3]]
    check(len(cross)==1 and cross[0]['country_id']=='BRN' and cross[0]['source_name']=='DPMM FC' and cross[0]['competition_id']=='MYS-0001','Cross-border identity mismatch')
    reserves=[c for c in ledger if c['squad_type']=='RESERVE'];old_ids={c['club_id']:c for c in old_clubs}
    check(len(reserves)==1 and reserves[0]['parent_club_id'] in old_ids and old_ids[reserves[0]['parent_club_id']]['canonical_name']=='전북현대' and reserves[0]['canonical_name']=='전북현대 N팀' and reserves[0]['club_id']!=reserves[0]['parent_club_id'],'Reserve parent identity mismatch')
    check(len(special)==2 and {s['club_id'] for s in special}=={c['club_id'] for c in cross+reserves} and all(s.get('source_url','').startswith('https://') and s.get('reason') for s in special),'Special identity evidence missing')
    rawpath=repo/'reports/master_provider_snapshot.json';raw=json.loads(rawpath.read_text());digest=hashlib.sha256(rawpath.read_bytes()).hexdigest();cat={str(t['tournamentId']):t for t in raw['tournaments']}
    check({c['competition_id'] for c in candidates}==set(cm) and len(candidates)==20,'Provider competition coverage mismatch')
    for c in candidates:
        check(c['provider']=='oddspapi' and c['verification_status']=='REVIEW' and c['activation_allowed'] is False and c['source_sha256']==digest,'Provider namespace, hash or activation invalid')
        for p in c['candidates']:
            t=cat.get(p['provider_id'],{})
            check(t.get('tournamentName')==p['provider_name'] and t.get('categoryName')==p['provider_country'],'Unproven provider competition ID')
    check({p['club_id'] for p in participants}==set(cl) and len(participants)==len(cl),'Provider participant coverage mismatch')
    fixture_index={str(f['fixtureId']):f for f in raw['fixtures']}
    for p in participants:
        check(p['provider']=='oddspapi' and p['activation_allowed'] is False and p['source_sha256']==digest and p['verification_status'] in {'REVIEW','UNRESOLVED'},'Participant candidate activated or wrong namespace')
        for c in p['candidates']:check(raw['participants'].get(c['provider_id'])==c['provider_name'],'Unproven provider participant ID')
        allowed_ids={c['provider_id'] for binding in candidates if binding['competition_id']==p['competition_id'] for c in binding['candidates']}
        for f in p['cached_fixture_evidence']:
            observed=fixture_index.get(str(f['fixture_id']),{})
            check(str(observed.get('tournamentId'))==f['tournament_id'] and f['tournament_id'] in allowed_ids and observed.get('startTime')==f['start_time'] and any(str(observed.get('participant'+side+'Id'))==f['participant_id'] and observed.get('participant'+side+'Name')==f['participant_name'] for side in ['1','2']),'Unproven cached fixture identity')
    return dict(status='PASS' if not errors else 'FAIL',errors=errors,competitions=len(comps),clubs=len(clubs),memberships=len(members),new_clubs=len(clubs),provider_verified_competitions=0,provider_verified_participants=0,provider_catalog_candidate_competitions=len(candidates),provider_exact_label_candidate_clubs=sum(bool(p['candidates']) for p in participants),production_activation_allowed=False,matrix=matrix)


if __name__=='__main__':
    result=audit();print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(bool(result['errors']))
