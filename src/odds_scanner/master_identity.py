"""Strict spelling normalization for scoped provider identity evidence, never results."""
import re
import unicodedata

# Club legal designators only; reserve/age/geographic/numeric qualifiers remain.
DESIGNATORS = frozenset({'fc', 'cf', 'fk', 'nk', 'sk', 'sc', 'ac', 'afc', 'pfc', 'hfk', 'hnk', 'gnk', 'kf', 'fkc', 'ofk'})


def club_spelling(value, *, designators=False):
    text = ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))
    tokens = re.findall(r'[a-z0-9]+', text)
    if designators:
        while tokens and tokens[0] in DESIGNATORS:
            tokens.pop(0)
        while tokens and tokens[-1] in DESIGNATORS:
            tokens.pop()
    return ''.join(tokens)
