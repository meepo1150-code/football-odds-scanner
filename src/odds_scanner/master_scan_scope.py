"""Reviewed exclusions before new scans; never deletes archived observations.

Provider IDs are namespaced. Unmapped competitions are not silently removed;
only the six explicitly cancelled divisions are excluded.
"""
import csv
import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / 'data/master/research/user_excluded_provider_bindings_2026_10_11.json'
REASON = 'USER_REVIEWED_COMPETITION_OUT_OF_SCOPE'
COUNTRY_CODES = {'AND': 'Andorra', 'AZE': 'Azerbaijan', 'BLR': 'Belarus', 'POL': 'Poland', 'RUS': 'Russia'}


@lru_cache(maxsize=1)
def bindings():
    with (PATH.parents[1] / 'competitions.csv').open() as handle:
        canonical = {r['competition_id']: r for r in csv.DictReader(handle)}
    return tuple({**r, 'canonical_name': canonical[r['competition_id']]['competition_name']} for r in json.loads(PATH.read_text()))


def excluded_competition_reason(row, *, provider=None):
    provider = provider or row.get('provider')
    source = str(row.get('source', ''))
    semantics = str(row.get('source_semantics', ''))
    if not provider and (source.startswith('oddspapi:') or semantics.startswith('CURRENT_ODDSPAPI_')):
        provider = 'oddspapi'
    tid = row.get('tournament_id', row.get('tournamentId'))
    country = row.get('country', row.get('categoryName', row.get('country_id')))
    if isinstance(country, str):
        country = COUNTRY_CODES.get(country, country)
    league = row.get('league', row.get('tournament_name', row.get('tournamentName', row.get('sport', ''))))
    if isinstance(league, dict):
        country = country or league.get('country')
        league = league.get('name', '')
    # Country-qualified labels supply country explicitly, never inferred from teams.
    if not country and isinstance(league, str) and ' - ' in league:
        country, league = league.split(' - ', 1)
    for binding in bindings():
        if provider == binding['provider'] and tid is not None and str(tid) == binding['provider_id']:
            return REASON
        if str(country).casefold() == binding['provider_country'].casefold() and str(league).strip().casefold() in {binding['provider_name'].casefold(), binding['canonical_name'].casefold()}:
            return REASON
    return None


def filter_scan_targets(rows, *, provider='oddspapi'):
    from .research_population import exclusion_reason
    return [r for r in rows if exclusion_reason(r, provider=provider) is None]
