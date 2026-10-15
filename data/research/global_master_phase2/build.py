"""Offline deterministic staging projection. Never writes production tables."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(root, name, fields, rows):
    with (root / name).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: tuple(str(r[k]) for k in fields)))


def build(root=ROOT, repo=REPO):
    rosters = json.loads((root/'evidence/rosters.json').read_text())
    ledger = json.loads((root/'evidence/identity_ledger.json').read_text())
    existing_countries = {r['country_id']:r for p in [repo/'data/master/countries.csv', repo/'data/research/global_master_phase1/countries.csv'] for r in read_csv(p)}
    names = {'CHN':'China','IDN':'Indonesia','MYS':'Malaysia','BRN':'Brunei Darussalam','VNM':'Vietnam','ARE':'United Arab Emirates','QAT':'Qatar','CHL':'Chile','COL':'Colombia','URY':'Uruguay','ECU':'Ecuador','PRY':'Paraguay','PER':'Peru','BOL':'Bolivia'}
    ids = {r['country_id'] for r in rosters} | {c['country_id'] for c in ledger}
    countries = [existing_countries.get(i, dict(country_id=i,country_name=names.get(i,i),status='REVIEW')) for i in sorted(ids)]
    comps=[];clubs=[];members=[];seasons=[]
    for r in rosters:
        comps.append(dict(competition_id=r['competition_id'], country_id=r['country_id'], competition_name=r['competition_name'],status='REVIEW'))
        seasons.append(dict(competition_id=r['competition_id'],season=r['season'],verified_stages=r['verified_stages'],temporal_state='CURRENT',verification_status='VERIFIED_OFFICIAL',source_url=r['source_url'],checked_at=r['checked_at']))
        for c in r['clubs']:
            clubs.append(dict(club_id=c['club_id'],country_id=c['country_id'],canonical_name=c['canonical_name'],season_membership_status='SOURCE_VERIFIED_CURRENT',canonical_club_id=c['club_id']))
            members.append(dict(season=r['season'],country_id=r['country_id'],division=r['division'],competition_id=r['competition_id'],competition_name=r['competition_name'],club_id=c['club_id'],source_name=c['source_name'],source_url=r['source_url'],verification_status='VERIFIED_OFFICIAL',checked_at=r['checked_at']))
    write_csv(root,'countries.csv',['country_id','country_name','status'],countries)
    write_csv(root,'competitions.csv',['competition_id','country_id','competition_name','status'],comps)
    write_csv(root,'clubs_canonical.csv',['club_id','country_id','canonical_name','season_membership_status','canonical_club_id'],clubs)
    write_csv(root,'verified_memberships.csv',['season','country_id','division','competition_id','competition_name','club_id','source_name','source_url','verification_status','checked_at'],members)
    write_csv(root,'memberships.csv',['season','competition_id','team_id'],[dict(season=m['season'],competition_id=m['competition_id'],team_id=m['club_id']) for m in members])
    write_csv(root,'club_assignments.csv',['association_id','source_name','club_id'],[dict(association_id=c['country_id'],source_name=c['canonical_name'],club_id=c['club_id']) for c in ledger])
    write_csv(root,'seasons.csv',['competition_id','season','verified_stages','temporal_state','verification_status','source_url','checked_at'],seasons)


if __name__ == '__main__':
    build()
