from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

MOVEMENT_PATH = Path('reports/europe_discovery_movement.json')
REPORT_PATH = Path('reports/europe_discovery_pattern_research.json')


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _bucket_direction(delta):
    try:
        value = float(delta)
    except (TypeError, ValueError):
        return 'UNKNOWN'
    if abs(value) < 1e-9:
        return 'FLAT'
    return 'UP' if value > 0 else 'DOWN'


def summarize(movement_report: dict) -> dict:
    rows = movement_report.get('movement_rows') or []
    if not isinstance(rows, list):
        rows = []

    by_candidate: dict[str, dict] = {}
    candidate_rows: dict[str, list[dict]] = defaultdict(list)
    all_buckets = Counter()

    for row in rows:
        if not isinstance(row, dict):
            continue
        ah = row.get('ah') or {}
        ou = row.get('ou') or {}
        all_buckets[f"AH_{_bucket_direction(ah.get('line_delta'))}"] += 1
        all_buckets[f"OU_{_bucket_direction(ou.get('line_delta'))}"] += 1

        candidate_ids = set()
        for key in ('candidate_like_open', 'candidate_like_latest', 'candidate_like_persisted', 'candidate_like_appeared', 'candidate_like_disappeared'):
            values = row.get(key) or []
            if isinstance(values, list):
                candidate_ids.update(str(v) for v in values if v is not None)
        for candidate_id in candidate_ids:
            candidate_rows[candidate_id].append(row)

    for candidate_id, items in sorted(candidate_rows.items()):
        ah_dirs = Counter()
        ou_dirs = Counter()
        persistence = Counter()
        side_changes = 0
        leagues = set()
        for row in items:
            ah_dirs[_bucket_direction((row.get('ah') or {}).get('line_delta'))] += 1
            ou_dirs[_bucket_direction((row.get('ou') or {}).get('line_delta'))] += 1
            if row.get('favorite_side_changed'):
                side_changes += 1
            if row.get('league'):
                leagues.add(str(row.get('league')))
            if candidate_id in (row.get('candidate_like_persisted') or []):
                persistence['PERSISTED'] += 1
            if candidate_id in (row.get('candidate_like_appeared') or []):
                persistence['APPEARED'] += 1
            if candidate_id in (row.get('candidate_like_disappeared') or []):
                persistence['DISAPPEARED'] += 1

        n = len(items)
        by_candidate[candidate_id] = {
            'fixtures_with_movement': n,
            'leagues_observed': len(leagues),
            'favorite_side_changes': side_changes,
            'ah_direction_counts': dict(ah_dirs),
            'ou_direction_counts': dict(ou_dirs),
            'candidate_state_counts': dict(persistence),
            'ah_nonflat_share': 0 if n == 0 else round((ah_dirs['UP'] + ah_dirs['DOWN']) / n, 4),
            'ou_nonflat_share': 0 if n == 0 else round((ou_dirs['UP'] + ou_dirs['DOWN']) / n, 4),
        }

    repeated = len(rows)
    status = 'WAITING_FOR_REPEATED_OBSERVATIONS' if repeated == 0 else 'DESCRIPTIVE_ONLY'
    return {
        'schema_version': '1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'classification': 'EUROPE_DISCOVERY_ONLY',
        'status': status,
        'production_promotion_allowed': False,
        'validation_gate_effect': 'NONE',
        'profitability_inference_allowed': False,
        'edge_inference_allowed': False,
        'minimum_sample_gate': 'NONE_DESCRIPTIVE_ONLY',
        'movement_source_semantics': movement_report.get('source_semantics') or 'FIRST_VS_LATEST_STRICT_DAILY_DISCOVERY_OBSERVATION',
        'fixtures_with_repeated_observations': repeated,
        'candidate_patterns_observed': len(by_candidate),
        'overall_direction_counts': dict(all_buckets),
        'candidate_movement_profiles': by_candidate,
        'interpretation': 'Descriptive segmentation only. Direction frequency may be used to decide what to pre-register for later testing, but it is not evidence of profitability, predictive edge, CLV, or production eligibility. First/latest discovery snapshots are not guaranteed bookmaker opening/closing prices.',
    }


def run(root: Path = Path('.')) -> dict:
    report = summarize(_load_json(root / MOVEMENT_PATH))
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
