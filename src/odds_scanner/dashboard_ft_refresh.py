"""Refresh offline FT reports for publication without touching scan transport."""
from pathlib import Path
import json

from .research_v2_pattern_stats import build, _rows, OUTCOMES, REPORT, MISSING_LEDGER


def refresh(root=Path('.')):
    previous = {str(r['fixture_id']): (r.get('ft_home_goals'), r.get('ft_away_goals'))
                for r in _rows(root / OUTCOMES)}
    stats = build(root)
    current_rows = _rows(root / OUTCOMES)
    current = {str(r['fixture_id']): (r.get('ft_home_goals'), r.get('ft_away_goals'))
               for r in current_rows}
    if any(current.get(fid) != score for fid, score in previous.items()):
        raise ValueError('BLOCKED FT publication: retained FT removed or score changed')
    # An empty canonical cache is already protected by build(); do not invent
    # a new population from absent input. Preserve the previously published set.
    from .research_v2_pattern_stats import SNAPSHOTS
    if not _rows(root / SNAPSHOTS):
        return stats
    ledger = json.loads((root / MISSING_LEDGER).read_text())
    pending = {str(r['fixture_id']) for r in ledger['fixtures']}
    denominator = len(current) + len(pending)
    if (len(current_rows) != len(current) or pending & current.keys()
            or ledger['missing_ft_count'] != len(pending)
            or stats['settled_fixtures'] != len(current)
            or stats['raw_unresolved_ft_fixtures'] != len(pending)
            or stats['ft_completeness_denominator'] != denominator):
        raise ValueError('BLOCKED FT publication: statistics/outcomes/pending population disagree')
    return stats


if __name__ == '__main__':
    report = refresh()
    print(json.dumps({k: report.get(k) for k in (
        'settled_fixtures', 'raw_unresolved_ft_fixtures',
        'ft_completeness_denominator', 'ft_completeness_pct')}))
