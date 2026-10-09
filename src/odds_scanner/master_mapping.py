"""Offline, opt-in master enrichment. Provider fixture identities remain untouched."""
import csv
from pathlib import Path

DEFAULT_MAPPING_PATH = Path(__file__).resolve().parents[2] / 'data/master/provider_mappings.csv'
ACCEPTED = frozenset({'VERIFIED_PROVIDER_SNAPSHOT', 'VERIFIED_OFFICIAL'})


def load_mappings(path=DEFAULT_MAPPING_PATH):
    """Fail closed on ambiguous provider identities; never resolve by display name."""
    result = {}
    with Path(path).open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if row['verification_status'] not in ACCEPTED:
                continue
            key = (row['provider'], row['entity_type'], row['provider_id'])
            if key in result:
                raise ValueError('Duplicate provider identity: ' + str(key))
            result[key] = row['internal_id']
    return result


def enrich_fixture(row, *, provider, mappings):
    """Return an enriched copy without changing API/dashboard/historical fields.

    Missing IDs stay unresolved. Club names, league labels and season membership
    are never used as substitute provider identifiers. This does not enable scans.
    """
    enriched = dict(row)
    for source, entity, target in (
        ('tournament_id', 'competition', 'canonical_competition_id'),
        ('home_participant_id', 'club', 'home_club_id'),
        ('away_participant_id', 'club', 'away_club_id'),
    ):
        value = row.get(source)
        if value is None:
            continue
        canonical = mappings.get((provider, entity, str(value)))
        if canonical is None:
            continue
        if target in row and row[target] != canonical:
            raise ValueError('Conflicting canonical identity: ' + target)
        enriched[target] = canonical
    return enriched
