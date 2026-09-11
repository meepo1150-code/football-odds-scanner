from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

MOVEMENT_PATH = Path('reports/europe_discovery_movement.json')
REPORT_PATH = Path('reports/europe_discovery_movement_research.json')


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _ids(row: dict, key: str) -> set[str]:
    raw = row.get(key) or []
    return {str(x) for x in raw if x is not None}


def _inc(counter: Counter, value) -> None:
    counter[str(value if value is not None else 'UNKNOWN')] += 1


def summarize(movement_report: dict) -> dict:
    rows = movement_report.get('movement_rows') or []
    by_candidate: dict[str, dict] = defaultdict(lambda: {
        'fixtures': set(),
        'first_observed_hits': 0,
        'latest_observed_hits': 0,
        'persisted': 0,
        'appeared': 0,
        'disappeared': 0,
        'favorite_side_changed': 0,
        'ah_line_buckets': Counter(),
        'ou_line_buckets': Counter(),
        'leagues': Counter(),
    })

    for row in rows:
        first_ids = _ids(row, 'candidate_like_open')
        latest_ids = _ids(row, 'candidate_like_latest')
        persisted = _ids(row, 'candidate_like_persisted')
        appeared = _ids(row, 'candidate_like_appeared')
        disappeared = _ids(row, 'candidate_like_disappeared')
        touched = first_ids | latest_ids
        fixture_id = str(row.get('fixture_id') or '')
        league_key = f"{row.get('country') or ''} · {row.get('league') or '—'}"
        ah_bucket = (row.get('ah') or {}).get('line_bucket')
        ou_bucket = (row.get('ou') or {}).get('line_bucket')

        for cid in touched:
            x = by_candidate[cid]
            if fixture_id:
                x['fixtures'].add(fixture_id)
            if cid in first_ids:
                x['first_observed_hits'] += 1
            if cid in latest_ids:
                x['latest_observed_hits'] += 1
            if cid in persisted:
                x['persisted'] += 1
            if cid in appeared:
                x['appeared'] += 1
            if cid in disappeared:
                x['disappeared'] += 1
            if row.get('favorite_side_changed'):
                x['favorite_side_changed'] += 1
            _inc(x['ah_line_buckets'], ah_bucket)
            _inc(x['ou_line_buckets'], ou_bucket)
            x['leagues'][league_key] += 1

    candidate_rows = []
    for cid, x in sorted(by_candidate.items()):
        touched = len(x['fixtures'])
        persistence_base = x['persisted'] + x['disappeared']
        persistence_rate = None if persistence_base == 0 else round(x['persisted'] / persistence_base, 4)
        candidate_rows.append({
            'candidate_id': cid,
            'repeated_fixtures_touched': touched,
            'first_observed_hits': x['first_observed_hits'],
            'latest_observed_hits': x['latest_observed_hits'],
            'persisted': x['persisted'],
            'appeared': x['appeared'],
            'disappeared': x['disappeared'],
            'persistence_rate_among_first_observed_hits': persistence_rate,
            'favorite_side_changed': x['favorite_side_changed'],
            'ah_line_buckets': dict(sorted(x['ah_line_buckets'].items())),
            'ou_line_buckets': dict(sorted(x['ou_line_buckets'].items())),
            'league_counts': dict(x['leagues'].most_common()),
        })

    overall_ah = Counter()
    overall_ou = Counter()
    for row in rows:
        _inc(overall_ah, (row.get('ah') or {}).get('line_bucket'))
        _inc(overall_ou, (row.get('ou') or {}).get('line_bucket'))

    return {
        'schema_version': '1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'classification': 'EUROPE_DISCOVERY_ONLY',
        'production_promotion_allowed': False,
        'validation_gate_effect': 'NONE',
        'outcome_or_roi_used': False,
        'source_semantics': movement_report.get('source_semantics') or 'FIRST_VS_LATEST_STRICT_DAILY_DISCOVERY_OBSERVATION',
        'repeated_fixtures': len(rows),
        'candidate_patterns_observed': len(candidate_rows),
        'overall_ah_line_buckets': dict(sorted(overall_ah.items())),
        'overall_ou_line_buckets': dict(sorted(overall_ou.items())),
        'candidate_pattern_movement': candidate_rows,
        'interpretation': 'Descriptive persistence and movement-frequency research only. No match outcomes, ROI, CLV, or profit claims are used. Candidate-like persistence does not validate an edge and cannot promote a pattern.',
    }


def run(root: Path = Path('.')) -> dict:
    report = summarize(_load(root / MOVEMENT_PATH))
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
