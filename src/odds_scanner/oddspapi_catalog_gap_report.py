from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CATALOG_PATH = Path('data/normalized/oddspapi_market_catalog.json')
DISCOVERY_STATUS_PATH = Path('reports/europe_discovery_status.json')
REPORT_PATH = Path('reports/oddspapi_catalog_gap_report.json')
SPORT_ID = 10


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def classify_unknown_ids(catalog_rows: list[dict], unknown_counts: dict[str, int]) -> dict:
    raw = {str(r.get('marketId')): r for r in catalog_rows if isinstance(r, dict) and r.get('marketId') is not None}
    classes = Counter()
    samples: dict[str, list[dict]] = {}
    weighted = Counter()
    for market_id, count in unknown_counts.items():
        meta = raw.get(str(market_id))
        if meta is None:
            cls = 'ABSENT_FROM_RAW_CATALOG'
            sample = {'market_id': str(market_id), 'count': int(count)}
        elif meta.get('sportId') != SPORT_ID:
            cls = 'FILTERED_OTHER_SPORT'
            sample = {'market_id': str(market_id), 'count': int(count), 'sportId': meta.get('sportId'), 'marketName': meta.get('marketName'), 'period': meta.get('period'), 'playerProp': meta.get('playerProp')}
        elif meta.get('playerProp') is True:
            cls = 'FILTERED_PLAYER_PROP'
            sample = {'market_id': str(market_id), 'count': int(count), 'sportId': meta.get('sportId'), 'marketName': meta.get('marketName'), 'period': meta.get('period'), 'playerProp': meta.get('playerProp')}
        elif str(meta.get('period') or '').lower() != 'fulltime':
            cls = 'FILTERED_NON_FULLTIME'
            sample = {'market_id': str(market_id), 'count': int(count), 'sportId': meta.get('sportId'), 'marketName': meta.get('marketName'), 'period': meta.get('period'), 'playerProp': meta.get('playerProp')}
        else:
            cls = 'FULLTIME_SOCCER_NON_PLAYER_BUT_NOT_RECOGNIZED'
            sample = {'market_id': str(market_id), 'count': int(count), 'sportId': meta.get('sportId'), 'marketName': meta.get('marketName'), 'marketType': meta.get('marketType'), 'period': meta.get('period'), 'playerProp': meta.get('playerProp'), 'handicap': meta.get('handicap')}
        classes[cls] += 1
        weighted[cls] += int(count)
        samples.setdefault(cls, [])
        if len(samples[cls]) < 20:
            samples[cls].append(sample)
    return {
        'unknown_market_ids': len(unknown_counts),
        'classification_counts': dict(sorted(classes.items())),
        'fixture_weighted_occurrences': dict(sorted(weighted.items())),
        'samples': samples,
    }


def run(root: Path = Path('.')) -> dict:
    catalog = _load(root / CATALOG_PATH, [])
    status = _load(root / DISCOVERY_STATUS_PATH, {})
    unknown = status.get('unknown_active_market_ids') or {}
    report = {
        'schema_version': '1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'provider': 'oddspapi',
        'classification': 'DIAGNOSTIC_ONLY',
        'api_requests_used': 0,
        'strict_parser_rules_changed': False,
        **classify_unknown_ids(catalog if isinstance(catalog, list) else [], unknown if isinstance(unknown, dict) else {}),
        'interpretation': 'Zero-quota diagnostic only. This report explains why active market IDs are absent from the strict full-time soccer catalog view; it does not authorize fallback market selection.',
    }
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
