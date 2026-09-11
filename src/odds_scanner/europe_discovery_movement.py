from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_PATH = Path('data/normalized/europe_discovery_snapshots.jsonl')
REPORT_PATH = Path('reports/europe_discovery_movement.json')


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except FileNotFoundError:
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _quarter_delta(delta: float | None) -> str | None:
    if delta is None:
        return None
    q = round(delta * 4) / 4
    if abs(q - delta) > 1e-9:
        return 'NON_QUARTER_DELTA'
    if abs(q) < 1e-9:
        return 'FLAT'
    if abs(q) >= 0.5:
        return 'UP_.50_PLUS' if q > 0 else 'DOWN_.50_PLUS'
    return 'UP_.25' if q > 0 else 'DOWN_.25'


def _candidate_ids(row: dict) -> set[str]:
    raw = row.get('candidate_like_matches') or []
    return {str(x) for x in raw if x is not None}


def summarize(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        fixture_id = row.get('fixture_id')
        observed_at = row.get('observed_at')
        if fixture_id is None or not observed_at:
            continue
        grouped[str(fixture_id)].append(row)

    movements: list[dict] = []
    for fixture_id, fixture_rows in grouped.items():
        fixture_rows.sort(key=lambda r: str(r.get('observed_at') or ''))
        if len(fixture_rows) < 2:
            continue
        first, latest = fixture_rows[0], fixture_rows[-1]
        first_ah = first.get('ah') or {}
        last_ah = latest.get('ah') or {}
        first_ou = first.get('ou') or {}
        last_ou = latest.get('ou') or {}

        ah_line_open = _num(first_ah.get('selected_side_line'))
        ah_line_close = _num(last_ah.get('selected_side_line'))
        ah_price_open = _num(first_ah.get('selected_side_price'))
        ah_price_close = _num(last_ah.get('selected_side_price'))
        ou_line_open = _num(first_ou.get('line'))
        ou_line_close = _num(last_ou.get('line'))
        over_open = _num(first_ou.get('over_price'))
        over_close = _num(last_ou.get('over_price'))
        under_open = _num(first_ou.get('under_price'))
        under_close = _num(last_ou.get('under_price'))

        ah_line_delta = None if ah_line_open is None or ah_line_close is None else round(ah_line_close - ah_line_open, 4)
        ou_line_delta = None if ou_line_open is None or ou_line_close is None else round(ou_line_close - ou_line_open, 4)
        movement = {
            'fixture_id': fixture_id,
            'country': latest.get('country') or first.get('country'),
            'league': latest.get('league') or first.get('league'),
            'home': latest.get('home') or first.get('home'),
            'away': latest.get('away') or first.get('away'),
            'kickoff': latest.get('kickoff') or first.get('kickoff'),
            'observations': len(fixture_rows),
            'first_observed_at': first.get('observed_at'),
            'latest_observed_at': latest.get('observed_at'),
            'favorite_side_open': first.get('favorite_side'),
            'favorite_side_latest': latest.get('favorite_side'),
            'favorite_side_changed': first.get('favorite_side') != latest.get('favorite_side'),
            'ah': {
                'opening_line': ah_line_open,
                'latest_line': ah_line_close,
                'line_delta': ah_line_delta,
                'line_bucket': _quarter_delta(ah_line_delta),
                'opening_price': ah_price_open,
                'latest_price': ah_price_close,
                'price_delta': None if ah_price_open is None or ah_price_close is None else round(ah_price_close - ah_price_open, 4),
            },
            'ou': {
                'opening_line': ou_line_open,
                'latest_line': ou_line_close,
                'line_delta': ou_line_delta,
                'line_bucket': _quarter_delta(ou_line_delta),
                'opening_over_price': over_open,
                'latest_over_price': over_close,
                'over_price_delta': None if over_open is None or over_close is None else round(over_close - over_open, 4),
                'opening_under_price': under_open,
                'latest_under_price': under_close,
                'under_price_delta': None if under_open is None or under_close is None else round(under_close - under_open, 4),
            },
            'candidate_like_open': sorted(_candidate_ids(first)),
            'candidate_like_latest': sorted(_candidate_ids(latest)),
            'candidate_like_persisted': sorted(_candidate_ids(first) & _candidate_ids(latest)),
            'candidate_like_appeared': sorted(_candidate_ids(latest) - _candidate_ids(first)),
            'candidate_like_disappeared': sorted(_candidate_ids(first) - _candidate_ids(latest)),
        }
        movements.append(movement)

    movements.sort(key=lambda x: (str(x.get('latest_observed_at') or ''), str(x.get('fixture_id'))), reverse=True)
    return {
        'schema_version': '1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'classification': 'EUROPE_DISCOVERY_ONLY',
        'production_promotion_allowed': False,
        'validation_gate_effect': 'NONE',
        'source_semantics': 'FIRST_VS_LATEST_STRICT_DAILY_DISCOVERY_OBSERVATION',
        'fixtures_seen': len(grouped),
        'fixtures_with_repeated_observations': len(movements),
        'movement_rows': movements,
        'interpretation': 'Descriptive movement evidence only. First observed discovery snapshot is not guaranteed to be bookmaker opening price; latest snapshot is not guaranteed to be closing price. Do not treat this report as CLV, edge, or promotion evidence.',
    }


def run(root: Path = Path('.')) -> dict:
    report = summarize(_load_jsonl(root / SNAPSHOT_PATH))
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
