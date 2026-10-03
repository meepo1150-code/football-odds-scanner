"""User-selected population scope; exclusion is NOT a data-integrity failure."""
import re

POLICY = 'REVIEWED_RESEARCH_SCOPE_V2'
EXCLUDED_LEAGUES = {
    'egypt - 2nd division b',
    'argentina - liga pro reserves',
}
WOMEN = re.compile(r"\b(?:women(?:s|'s)?|female|ladies|girls|femenin[ao]|feminine|frauen|damallsvenskan|nwsl)\b", re.I)
YOUTH = re.compile(r'\b(?:u\s*[- ]?\s*(?:1[0-9]|2[0-3])|under\s*[- ]?\s*(?:1[0-9]|2[0-3])|youth|junior|juniors|primavera)\b', re.I)


def exclusion_reason(row):
    # Never infer age/gender from a club's fame or country. Provider labels
    # and explicit team suffixes are the evidence; reserves alone are retained.
    values = [row.get(k) for k in ('league', 'league_name', 'competition', 'sport', 'home', 'away', 'gender', 'age_group')]
    text = ' '.join(str(v).replace('_', ' ') for v in values if v is not None)
    if WOMEN.search(text):
        return 'WOMEN_OUT_OF_SCOPE'
    if YOUTH.search(text):
        return 'YOUTH_OUT_OF_SCOPE'
    if any(str(row.get(k) or '').strip().casefold() in EXCLUDED_LEAGUES
           for k in ('league', 'league_name', 'competition', 'sport')):
        return 'REVIEWED_LEAGUE_OUT_OF_SCOPE'
    return None


def in_scope(row):
    return exclusion_reason(row) is None
