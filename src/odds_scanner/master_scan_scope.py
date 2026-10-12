"""Strict forward allowlist; legacy exclusion semantics stay separate for archives."""
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
    return [r for r in rows if exclusion_reason(r, provider=provider) is None
            and scan_scope_reason(r,provider=provider) is None]


@lru_cache(maxsize=1)
def approved_competitions():
    root=PATH.parents[1]
    with (root/'competitions.csv').open() as f:
        active={r['competition_id']:r for r in csv.DictReader(f) if r['status']=='VERIFIED_OFFICIAL'}
    with (root/'cup_competition_registry_2026.csv').open() as f:
        active.update({r['competition_id']:r for r in csv.DictReader(f)
            if r['season_status']=='VERIFIED_OFFICIAL'
            and r['competition_type'] in {'DOMESTIC_CUP','UEFA_CLUB_COMPETITION'}})
    with (root/'countries.csv').open() as f:
        countries={r['country_id']:r['country_name'] for r in csv.DictReader(f)}
    return {cid:{**r,'country_name':countries[r['country_id']]} for cid,r in active.items()}


@lru_cache(maxsize=1)
def forward_mappings():
    from .master_mapping import load_mappings
    active=approved_competitions()
    return {(p,pid):cid for (p,kind,pid),cid in load_mappings().items()
            if kind=='competition' and cid in active}


def provider_has_verified_scope(provider):
    return any(p==provider for p,_ in forward_mappings())


@lru_cache(maxsize=1)
def observed_provider_countries():
    # Accepted aliases are literal reviewed provider categories, not guessed countries.
    catalog=json.loads((PATH.parents[3]/'reports/master_provider_snapshot.json').read_text())
    return {('oddspapi',str(r['tournamentId'])):str(r.get('categoryName') or '').casefold()
            for r in catalog.get('tournaments',[])}


def scan_scope_reason(row, *, provider):
    tid=row.get('tournament_id',row.get('tournamentId',row.get('provider_competition_id')))
    if tid is None:return 'MASTER_PROVIDER_COMPETITION_ID_MISSING'
    cid=forward_mappings().get((provider,str(tid)))
    if cid is None:return 'MASTER_PROVIDER_COMPETITION_UNMAPPED'
    if row.get('canonical_competition_id') not in (None,cid):return 'MASTER_CANONICAL_ID_CONFLICT'
    c=approved_competitions()[cid];country=row.get('country',row.get('categoryName'))
    if isinstance(country,dict):country=country.get('name')
    accepted_countries={c['country_id'].casefold(),c['country_name'].casefold(),
                        observed_provider_countries().get((provider,str(tid)))}
    if provider=='oddspapi':
        audit=json.loads((PATH.parents[1]/'research/provider_mapping_audit_2026_10_09.json').read_text())
        accepted_countries.update(str(r.get('provider_country','')).casefold() for r in audit.get('mappings',[]) if str(r.get('provider_id'))==str(tid) and r.get('internal_id')==cid)
    # The existing reviewed Czech resolver explicitly records both country labels.
    if c['country_id']=='CZE':accepted_countries.update({'czech republic','czechia'})
    if country and str(country).casefold() not in accepted_countries:
        return 'MASTER_COUNTRY_CONFLICT'
    return None
