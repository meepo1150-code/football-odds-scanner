"""Deterministic staging review; official bilingual club identities only."""
import hashlib
import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs,urlparse

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
EVIDENCE_SHA256='4fa2146740383dea81f609c5affe8334b1c6a2f4cebad4f2f8cfb13ccb8147f2'
MATCHDAY_SHA256='27199f76565e8eb03384c7fdf069e098cfe2dc3e68dea98e1143c32552eb67d0'
spec=importlib.util.spec_from_file_location('previous_alias_followup',REPO/'data/research/global_provider_alias_followup/build.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
reviewer=previous.reviewer


def aliases(path=ROOT/'korean_official_aliases.json'):
    payload=path.read_bytes()
    assert hashlib.sha256(payload).hexdigest()==EVIDENCE_SHA256,'Official bilingual evidence hash mismatch'
    raw=json.loads(payload);out=[];seen=set()
    memberships={m['club_id']:m['competition_id'] for m in reviewer.rows(REPO/'data/research/global_master_phase1/verified_memberships.csv')}
    clubs={c['club_id']:c['canonical_name'] for c in reviewer.rows(REPO/'data/research/global_master_phase1/clubs_canonical.csv')}
    for row in raw['records']:
        club=row['club_id'];cid=row['competition_id'];code=row['official_team_id']
        assert club not in seen and memberships[club]==cid and clubs[club]==row['canonical_name']
        assert cid in ('KOR-0001','KOR-0002')
        seen.add(club);labels=set()
        assert {s['language'] for s in row['sources']}=={'en','ko'}
        for source in row['sources']:
            previous.check_source(source,'www.kleague.com')
            assert parse_qs(urlparse(source['source_url']).query)['teamId']==[code]
            labels.update((source['profile_name'],source['profile_short_name']))
        assert labels==set(row['aliases'])
        # FC and Football Club are the same generic legal designator. Remove
        # only this exact terminal phrase copied from the official profile;
        # retain city, squad, sponsor and numerical identity qualifiers.
        labels.update(label[:-len(' Football Club')].rstrip() for label in list(labels)
                      if label.casefold().endswith(' football club'))
        for label in sorted(labels):
            out.append(dict(club_id=club,competition_id=cid,alias=label,source_url=row['sources'][0]['source_url'],official_entity_id=code))
    assert len(seen)==29
    return out


def matchday_aliases(path=ROOT/'matchday_official_aliases.json'):
    payload=path.read_bytes()
    assert hashlib.sha256(payload).hexdigest()==MATCHDAY_SHA256,'Official matchday evidence hash mismatch'
    records=json.loads(payload);out=[]
    baseline=previous.reviewer.review()
    clubs={c['club_id']:c for c in baseline['clubs']}
    hosts={'SAU-KHA':'saudipedia.com','SAU-NAS':'saudipedia.com',
           'SAU-AHL':'en.alahlifc.sa','SAU-HAZ':'www.spl.com.sa',
           'THA-AAL':'competition.tl.prod.c0d1um.io'}
    assert {r['club_id'] for r in records}==set(hosts)
    for record in records:
        club=record['club_id']
        previous.check_source(record['source'],hosts[club])
        assert record['canonical_name']==clubs[club]['canonical_name']
        official=record['official_alias'];alias=record['alias']
        assert alias==official or official==alias+' Football Club'
        if club=='THA-AAL':
            current=next(r for r in reviewer.json_file(REPO/'data/research/thailand_membership_completion/identity_ledger.json') if r['club_id']==club)
            assert record['official_club_id']==current['official_club_id']==47
            assert record['current_tournament_team_id']==current['official_tournament_team_id']
        out.append(dict(club_id=club,competition_id=record['competition_id'],alias=alias,source_url=record['source']['source_url']))
    return out


def build(path=ROOT/'korean_official_aliases.json'):
    proven=previous.aliases()+aliases(path)+matchday_aliases()
    result=reviewer.review(official_aliases=proven)
    result['official_aliases']=proven
    result['source_hashes']['data/research/global_expansion_readiness/korean_official_aliases.json']=EVIDENCE_SHA256
    result['source_hashes']['data/research/global_expansion_readiness/matchday_official_aliases.json']=MATCHDAY_SHA256
    baseline=previous.build()
    result['baseline_counts']=baseline['counts']
    result['identity_delta']={k:result['counts'][k]-baseline['counts'][k] for k in ('verified_cached_competition_identities','verified_cached_participant_identities')}
    for kind,key in [('competitions','competition_id'),('clubs','club_id')]:
        after={r[key]:r['provider_id'] for r in result[kind]}
        assert all(not r['provider_id'] or after[r[key]]==r['provider_id'] for r in baseline[kind])
    return result


if __name__=='__main__':
    import sys
    result=build();path=ROOT/'identity_review.json'
    if '--write' in sys.argv:path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    else:assert json.loads(path.read_text())==result,'Committed identity report differs from rebuild'
    print(json.dumps(dict(counts=result['counts'],delta=result['identity_delta']),indent=2))
