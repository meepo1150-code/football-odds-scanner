"""Offline boundary tests: canonical master IDs do not replace provider fixture IDs."""
import csv
from pathlib import Path
from odds_scanner.oddspapi_result_join import join_rows, normalize_result
from odds_scanner.oddspapi_tournament_universe import classify, tier_hint

ROOT = Path(__file__).resolve().parents[1] / 'data/master'

def rows(name):
    with (ROOT / name).open(newline='') as handle:
        return list(csv.DictReader(handle))

def test_scanner_england_tier_hints_agree_with_scoped_competitions():
    catalog = {r['competition_id']: r for r in rows('uefa_domestic_league_catalog.csv')}
    for level, name in enumerate(['Premier League', 'Championship', 'League One', 'League Two'], 1):
        assert int(catalog[f'ENG-{level:04d}']['league_level']) == tier_hint(name, 'England')

def test_master_enriched_fixture_preserves_exact_historical_join():
    clubs = {r['club_id'] for r in rows('uefa_clubs_canonical.csv')}
    assert {'ENG-ARS', 'ENG-CHE'} <= clubs
    fixture = dict(fixture_id='provider-history-17', home_club_id='ENG-ARS', away_club_id='ENG-CHE', league='Premier League')
    result = normalize_result(dict(fixtureId='provider-history-17', statusId=2, homeScore=1, awayScore=0))
    joined, report = join_rows([fixture], [result])
    assert report['joined_fixtures'] == 1
    assert joined[0]['fixture_id'] == fixture['fixture_id']
    assert joined[0]['home_club_id'] == 'ENG-ARS'
    assert not joined[0]['promotion_eligible']
    assert join_rows([{**fixture, 'fixture_id': 'different-provider-id'}], [result])[0] == []

def test_cup_competitions_remain_separate_from_domestic_memberships():
    cups = rows('cup_competition_registry_2026.csv')
    cup_ids = {r['competition_id'] for r in cups}
    assert len(cup_ids) == 11
    assert not cup_ids & {r['competition_id'] for r in rows('memberships.csv')}
    for cup in cups:
        expected = 'EUROPEAN_CUP' if cup['competition_type'] == 'UEFA_CLUB_COMPETITION' else 'DOMESTIC_CUP'
        assert classify(cup['competition_name'], cup['country_id']) == expected

def test_provider_mappings_are_backed_by_exact_saved_catalog_records():
    import json
    import hashlib
    audit = json.loads((ROOT / 'research/provider_mapping_audit_2026_10_09.json').read_text())
    source = ROOT.parents[1] / audit['source_path']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == audit['source_sha256']
    candidates = {str(r['tournament_id']): r for r in json.loads(source.read_text())['candidates']}
    evidence = {r['internal_id']: r for r in audit['mappings']}
    actual = rows('provider_mappings.csv')
    assert len(actual) == 45
    for mapping in actual:
        candidate = candidates[mapping['provider_id']]
        proof = evidence[mapping['internal_id']]
        assert candidate['provider_verified']
        assert proof['provider_id'] == mapping['provider_id']
        assert proof['provider_name'] == candidate['tournament_name']
        assert proof['provider_country'] == candidate['country']
        assert mapping['verification_status'] == 'VERIFIED_PROVIDER_SNAPSHOT'
    scope = {r['competition_id'] for r in rows('uefa_league_coverage_2026.csv')} | {r['competition_id'] for r in rows('cup_competition_registry_2026.csv')}
    assert set(evidence) | set(audit['unmapped_competition_ids']) == scope
    assert not set(evidence) & set(audit['unmapped_competition_ids'])


def test_offline_enrichment_preserves_provider_and_dashboard_payload():
    from odds_scanner.master_mapping import load_mappings, enrich_fixture
    row = dict(fixture_id='history-17', tournament_id=17, home='Arsenal', away='Chelsea', one_x_two={'home': 1.8})
    enriched = enrich_fixture(row, provider='oddspapi', mappings=load_mappings())
    assert enriched == {**row, 'canonical_competition_id': 'ENG-0001'}
    assert 'home_club_id' not in enriched
    assert enrich_fixture(row, provider='different-provider', mappings=load_mappings()) == row
    assert enrich_fixture({**row, 'tournament_id': 'unknown'}, provider='oddspapi', mappings=load_mappings()) == {**row, 'tournament_id': 'unknown'}
    assert row == {k: enriched[k] for k in row}


def test_enrichment_rejects_conflicting_identity_and_duplicate_maps(tmp_path):
    import pytest
    from odds_scanner.master_mapping import load_mappings, enrich_fixture
    with pytest.raises(ValueError, match='Conflicting'):
        enrich_fixture({'tournament_id': 17, 'canonical_competition_id': 'ENG-0002'}, provider='oddspapi', mappings=load_mappings())
    path = tmp_path / 'maps.csv'
    path.write_text('entity_type,internal_id,provider,provider_id,verification_status\ncompetition,ENG-0001,oddspapi,17,VERIFIED_PROVIDER_SNAPSHOT\ncompetition,ENG-0002,oddspapi,17,VERIFIED_PROVIDER_SNAPSHOT\n')
    with pytest.raises(ValueError, match='Duplicate'):
        load_mappings(path)

def test_user_excluded_leagues_are_filtered_by_exact_identity_only():
    from odds_scanner.research_population import exclusion_reason
    import json
    policy = json.loads((ROOT.parents[1] / 'config/league_selection_v1.json').read_text())
    for cid in policy['user_excluded_competition_ids']:
        assert exclusion_reason({'canonical_competition_id': cid}) == 'USER_REVIEWED_COMPETITION_OUT_OF_SCOPE'
    assert exclusion_reason({'competition_id': 'POL-0001'}) is None
    assert exclusion_reason({'competition_id': '123', 'home_club_id': 'AND-AND'}) is None
