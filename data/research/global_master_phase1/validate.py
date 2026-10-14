"""Offline staging audit. Does not write, rebuild, or activate production data."""
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
ALLOWED_COMPETITIONS = {'JPN-0001', 'JPN-0002', 'KOR-0001', 'KOR-0002',
                        'AUS-0001', 'USA-0001', 'BRA-0001', 'BRA-0002',
                        'ARG-0001', 'MEX-0001', 'SAU-0001'}


def spelling(name):
    return ''.join(c for c in unicodedata.normalize('NFKD', name).casefold()
                   if c.isalnum() and not unicodedata.combining(c))


def audit(root=ROOT, repo=REPO):
    errors = []
    def check(ok, label):
        if not ok:
            errors.append(label)
    def rows(name, base=root):
        with (base / name).open(encoding='utf-8', newline='') as handle:
            data = list(csv.DictReader(handle))
        check(all(all(v is not None and v != '' for v in r.values()) for r in data),
              'Missing required field: ' + name)
        return data
    def unique(data, keys, label):
        counts = Counter(tuple(r[k] for k in keys) for r in data)
        check(all(n == 1 for n in counts.values()), 'Duplicate ' + label)
    baseline = json.loads((root / 'baseline.json').read_text())
    # Every tracked baseline record and production file is byte-preserved.
    for path, digest in baseline['hashes'].items():
        p = repo / path
        check(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == digest,
              'Baseline changed: ' + path)
    countries = rows('countries.csv')
    comps = rows('competitions.csv')
    clubs = rows('clubs_canonical.csv')
    members = rows('verified_memberships.csv')
    projection = rows('memberships.csv')
    assignments = rows('club_assignments.csv')
    coverage = rows('league_coverage.csv')
    seasons = rows('seasons.csv')
    evidence = json.loads((root / 'evidence/rosters.json').read_text())
    candidates = json.loads((root / 'evidence/provider_candidates.json').read_text())
    aliases = json.loads((root / 'evidence/aliases.json').read_text())
    changes = json.loads((root / 'evidence/change_review.json').read_text())
    old_countries = {r['country_id']:r for r in rows('data/master/countries.csv', repo)}
    old_comps = {r['competition_id']:r for r in rows('data/master/competitions.csv', repo)}
    old_clubs = {r['club_id']:r for r in rows('data/master/uefa_clubs_canonical.csv', repo)}
    legacy = {r['team_id']:r for r in rows('data/master/teams.csv', repo)}
    unique(countries, ['country_id'], 'country ID')
    unique(comps, ['competition_id'], 'competition ID')
    unique(clubs, ['club_id'], 'club ID')
    unique(members, ['season','competition_id','club_id'], 'membership')
    unique(members, ['season','club_id'], 'domestic season membership')
    unique(assignments, ['association_id','source_name'], 'assignment')
    unique(evidence, ['competition_id'], 'roster evidence')
    unique(candidates, ['provider','provider_id'], 'provider candidate')
    cm = {r['competition_id']:r for r in comps}
    cl = {r['club_id']:r for r in clubs}
    em = {r['competition_id']:r for r in evidence}
    country_ids = {r['country_id'] for r in countries} | set(old_countries)
    check(set(cm) == ALLOWED_COMPETITIONS == set(em), 'Eleven-league scope mismatch')
    unique(seasons, ['competition_id','season'], 'season')
    check({s['competition_id'] for s in seasons}==set(cm), 'Season coverage mismatch')
    for s in seasons:
        r=em.get(s['competition_id'],{})
        check(all(s[k]==r.get(k) for k in ['season','source_url','checked_at','verification_status']),
              'Season evidence mismatch')
        check(s['temporal_state']==('NEXT_ANNOUNCED' if s['competition_id']=='AUS-0001' else 'CURRENT'),
              'Wrong season temporal state')
        stages={'ARG-0001':'Apertura|Clausura','MEX-0001':'Apertura'}
        check(s['verified_stages']==stages.get(s['competition_id'],'League'), 'Unverified season stage')
    for c in countries:
        check(bool(re.fullmatch('[A-Z]{3}', c['country_id'])), 'Invalid country ID')
        if c['country_id'] in old_countries:
            check(c == old_countries[c['country_id']], 'Existing country changed')
        else:
            check(c['status'] == 'REVIEW', 'New country activated')
    for c in comps:
        cid=c['competition_id']
        check(bool(re.fullmatch('[A-Z]{3}-[0-9]{4}',cid)), 'Invalid competition ID')
        check(cid.startswith(c['country_id']+'-') and c['country_id'] in country_ids,
              'Invalid competition country reference')
        check(c['status'] == 'REVIEW', 'Staging competition activated')
        if cid in old_comps:
            check(c == old_comps[cid], 'Competition collision or existing record change')
    name_ids = {}
    for c in [*old_clubs.values(), *clubs]:
        key=(c['country_id'],spelling(c['canonical_name']))
        name_ids.setdefault(key,set()).add(c['canonical_club_id'])
    check(all(len(ids)==1 for ids in name_ids.values()), 'Duplicate normalized club identity')
    unique(aliases, ['club_id','alias'], 'club alias')
    for a in aliases:
        club=cl.get(a['club_id'],{})
        check(bool(club) and bool(a['alias']) and a['source_url'].startswith('https://')
              and a['verification_status']=='VERIFIED_OFFICIAL' and bool(a['basis'])
              and a['checked_at']=='2026-10-14', 'Unverified alias evidence')
        key=(club.get('country_id'),spelling(a['alias']))
        name_ids.setdefault(key,set()).add(a['club_id'])
    check(all(len(ids)==1 for ids in name_ids.values()), 'Ambiguous club alias')
    check(set(changes['leagues'])==ALLOWED_COMPETITIONS and changes['checked_at']=='2026-10-14',
          'Change review scope mismatch')
    check(all(r.get('findings') and r.get('sources') for r in changes['leagues'].values()),
          'Missing change review evidence')
    for c in clubs:
        cid=c['club_id']
        check(bool(re.fullmatch('[A-Z]{3}-[A-Z]{3}',cid)), 'Invalid club ID')
        check(cid.startswith(c['country_id']+'-') and c['country_id'] in country_ids,
              'Invalid club country reference')
        check(c['canonical_club_id']==cid, 'Invalid canonical redirect')
        if cid in old_clubs:
            check(c == old_clubs[cid], 'Club collision or existing record change')
        if cid in legacy:
            check(c['canonical_name']==legacy[cid]['canonical_name'], 'Legacy club ID collision')
    ledger={(a['association_id'],a['source_name']):a['club_id'] for a in assignments}
    for m in members:
        cid=m['competition_id']; club=cl.get(m['club_id'],{})
        check(cid in cm and m['club_id'] in cl, 'Invalid membership foreign key')
        r=em.get(cid,{})
        check(m['country_id']==cm.get(cid,{}).get('country_id'), 'Invalid membership association')
        check(m['competition_name']==cm.get(cid,{}).get('competition_name'), 'Membership competition label mismatch')
        check(m['source_name']==club.get('canonical_name'), 'Membership club identity mismatch')
        check(ledger.get((club.get('country_id'),m['source_name']))==m['club_id'], 'ID ledger mismatch')
        for k in ['season','division','source_url','verification_status','checked_at']:
            check(str(m[k])==str(r.get(k)), 'Membership evidence mismatch: '+k)
        check(m['verification_status']=='VERIFIED_OFFICIAL', 'Unverified accepted membership')
    check(Counter((m['season'],m['competition_id'],m['club_id']) for m in members)==
          Counter((m['season'],m['competition_id'],m['team_id']) for m in projection),
          'Membership projection mismatch')
    check({m['club_id'] for m in members}==set(cl), 'Orphan club')
    unique(coverage,['competition_id'],'coverage row')
    check({c['competition_id'] for c in coverage}==set(cm),'Coverage scope mismatch')
    matrix=[]
    for r in evidence:
        cid=r['competition_id'];actual=[m for m in members if m['competition_id']==cid]
        names=[m['source_name'] for m in actual]
        check(Counter(names)==Counter(r['names']), 'Official roster mismatch: '+cid)
        check(len(set(r['names']))==len(r['names'])==r['expected_teams'], 'Expected roster count mismatch: '+cid)
        check(r['verification_status']=='VERIFIED_OFFICIAL' and bool(r['season_basis']), 'Unverified roster: '+cid)
        check(r['source_url'].startswith('https://') and r['checked_at']=='2026-10-14', 'Invalid source metadata')
        cv=next((c for c in coverage if c['competition_id']==cid),{})
        check(all(str(cv.get(k))==str(r[k]) for k in ['season','country_id','division','competition_name','expected_teams','source_url','verification_status','checked_at']), 'Coverage metadata mismatch: '+cid)
        missing=len(set(r['names'])-set(names)); duplicates=len(names)-len(set(names))
        check(cv.get('recorded_teams')==str(len(names)) and cv.get('missing_teams')==str(missing)
              and cv.get('duplicate_teams')==str(duplicates) and cv.get('evidence_coverage')=='100%'
              and cv.get('database_status')=='STAGING_ONLY','Coverage count/status mismatch: '+cid)
        matrix.append(dict(competition_id=cid,season=r['season'],expected=r['expected_teams'],verified=len(names),missing=missing,duplicates=duplicates))
    # Cross-border club namespace is separate from the host association.
    check({m['club_id'] for m in members if m['competition_id']=='AUS-0001' and m['club_id'].startswith('NZL-')}=={'NZL-AUC','NZL-WEL'},'NZ cross-border membership mismatch')
    check({m['club_id'] for m in members if m['competition_id']=='USA-0001' and m['club_id'].startswith('CAN-')}=={'CAN-MON','CAN-TOR','CAN-VAN'},'Canada cross-border membership mismatch')
    raw_path=repo/'reports/master_provider_snapshot.json'
    raw=json.loads(raw_path.read_text());catalog={str(t['tournamentId']):t for t in raw['tournaments']}
    check({c['competition_id'] for c in candidates}==set(cm),'Provider candidate coverage mismatch')
    production_mappings=rows('data/master/provider_mappings.csv',repo)
    for c in candidates:
        check(c['source_sha256']==hashlib.sha256(raw_path.read_bytes()).hexdigest(), 'Provider evidence hash mismatch')
        t=catalog.get(c['provider_id'],{})
        check(t.get('tournamentName')==c['provider_name'] and t.get('categoryName')==c['provider_country'], 'Unproven provider ID')
        check(c['verification_status']=='REVIEW' and c['activation_allowed'] is False
              and c['production_mapping_present'] is False,'Candidate activated')
        check(not any(m['internal_id']==c['competition_id'] for m in production_mappings),'Candidate leaked into production mapping')
    return dict(status='PASS' if not errors else 'FAIL', errors=errors,
                baseline_sha=baseline['main_sha'],new_countries=len(baseline['new_country_ids']),
                reused_countries=len(baseline['reused_country_ids']),competitions=len(comps),
                clubs=len(clubs),memberships=len(members),reused_clubs=baseline['reused_clubs'],
                provider_candidates=len(candidates),production_mappings_added=0,
                matrix=matrix,limitations=['Offline audit checks reviewed factual extracts, not live re-fetches or legal entity registration.',
                    'Current roster verification does not certify every historical promotion/relegation decision.',
                    'A-League 2026-27 is the next announced season, not an active season on the research date.',
                    'No live provider team mapping or odds availability has been certified.'])


if __name__=='__main__':
    result=audit()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(bool(result['errors']))
