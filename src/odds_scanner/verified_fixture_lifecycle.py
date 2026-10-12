"""Exact identity lifecycle receipts; never converts a postponement to an FT."""
from urllib.parse import urlparse
from .research_v2_pattern_stats import _rows
from .research_v2_slots import stamp

PATH = 'data/research/verified_fixture_lifecycle.jsonl'


def verified_statuses(root, snapshots):
    identities = {}
    for s in snapshots:
        identities.setdefault(str(s.get('fixture_id')), set()).add(
            (s.get('home'),s.get('away'),s.get('league'),stamp(s.get('kickoff'))))
    accepted = {}; conflicts = set()
    for row in _rows(root/PATH):
        fid=str(row.get('fixture_id'));source=row.get('source') or {}
        if not isinstance(source,dict):continue
        assertion=source.get('assertion') or {}
        if not isinstance(assertion,dict):continue
        status=row.get('status')
        identity=(row.get('home'),row.get('away'),row.get('league'),stamp(row.get('kickoff')))
        if (status not in {'POSTPONED','CANCELLED','ABANDONED'}
            or source.get('tier')!='A_OFFICIAL'
            or assertion.get('verification_method')!='MANUAL_WEB_REVIEW'
            or not source.get('source_title')
            or not urlparse(str(source.get('url'))).scheme=='https'
            or not urlparse(str(source.get('url'))).hostname
            or stamp(row.get('retrieved_at')) is None
            or None in identity or identities.get(fid)!={identity}
            or assertion.get('status')!=status
            or tuple(assertion.get(k) for k in ('home','away','league'))!=identity[:3]
            or stamp(assertion.get('original_kickoff'))!=identity[3]):
            continue
        if fid in accepted and accepted[fid]['status']!=status:conflicts.add(fid)
        accepted[fid]=row
    return {fid:r for fid,r in accepted.items() if fid not in conflicts}
