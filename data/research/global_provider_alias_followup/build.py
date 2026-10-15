"""Offline official alias corroboration. Never writes production provider mappings."""
import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
EVIDENCE_SHA256 = '835a0deb489d4e917346d6888a870e60bee9240fa7829ba2b7755c7e14ba9c2b'
spec = importlib.util.spec_from_file_location('provider_identity_review', REPO/'data/research/global_provider_identity_review/review.py')
reviewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reviewer)


def check_source(source, host):
    assert urlparse(source['source_url']).hostname == host, 'Official source namespace required'
    assert len(source['raw_sha256']) == 64 and all(c in '0123456789abcdef' for c in source['raw_sha256'])
    assert datetime.fromisoformat(source['observed_at']).tzinfo is not None


def aliases(evidence_path=ROOT/'evidence.json'):
    payload = evidence_path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == EVIDENCE_SHA256, 'Official evidence hash mismatch'
    evidence = json.loads(payload)
    base = reviewer.review()
    by_name = {c['canonical_name']:c['club_id'] for c in base['clubs'] if c['country_id']=='PRY'}
    found = set(); output = []
    apf = evidence['apf']
    check_source(apf, 'www.apf.org.py')
    for team in apf['records']:
        canonical = team['nickname']
        assert canonical in by_name and canonical not in found
        found.add(canonical)
        # The same official team UUID binds all three labels, not fuzzy matching.
        for name in sorted({team['name'], team['shortName'], canonical}):
            output.append(dict(competition_id='PRY-0001', club_id=by_name[canonical], alias=name,
                official_entity_id=team['id'], source_url=apf['source_url']))
    assert found == set(by_name) and len(found)==12
    for row in evidence['auf']:
        check_source(row['table_source'], 'www.auf.org.uy')
        check_source(row['profile_source'], 'www.auf.org.uy')
        assert row['canonical_name'] in row['table_link']['texts']
        assert row['table_link']['href'] == urlparse(row['profile_source']['source_url']).path
        assert 'femenino' not in row['profile_heading'].casefold()
        assert row['alias'] in row['profile_alias_excerpt']
        output.append(dict(competition_id=row['competition_id'], club_id=row['club_id'],
            alias=row['alias'], official_entity_id=row['table_link']['href'],
            source_url=row['profile_source']['source_url']))
    return output


def build(evidence_path=ROOT/'evidence.json', snapshot=None):
    proven = aliases(evidence_path)
    baseline = reviewer.review(snapshot=snapshot)
    result = reviewer.review(snapshot=snapshot, official_aliases=proven)
    result['official_alias_evidence_sha256'] = EVIDENCE_SHA256
    result['official_aliases'] = proven
    result['baseline_counts'] = baseline['counts']
    result['identity_delta'] = {
        key:result['counts'][key]-baseline['counts'][key]
        for key in ('verified_cached_competition_identities','verified_cached_participant_identities')}
    assert all(n>=0 for n in result['identity_delta'].values())
    verified = {c['club_id'] for c in result['clubs'] if c['provider_id']}
    members = {}
    for phase in ('phase1','phase2'):
        for row in reviewer.rows(REPO/f'data/research/global_master_{phase}/verified_memberships.csv'):
            members.setdefault(row['competition_id'],set()).add(row['club_id'])
    for row in reviewer.rows(REPO/'data/research/thailand_membership_completion/verified_memberships.csv'):
        members.setdefault(row['competition_id'],set()).add(row['club_id'])
    result['remaining_work'] = [dict(competition_id=c['competition_id'],
        cached_identity_status=c['status'],
        unresolved_club_ids=sorted(members[c['competition_id']]-verified),
        provider_season_stage_verified=False, live_odds_coverage_verified=False,
        activation_allowed=False) for c in result['competitions']]
    return result


if __name__=='__main__':
    import sys
    result = build()
    path = ROOT/'review.json'
    if '--write' in sys.argv:
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    else:
        assert json.loads(path.read_text())==result, 'Committed review differs from evidence rebuild'
    print(json.dumps(dict(counts=result['counts'],identity_delta=result['identity_delta']),indent=2))
