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

def test_no_unverified_provider_ids_are_fabricated():
    assert rows('provider_mappings.csv') == []
