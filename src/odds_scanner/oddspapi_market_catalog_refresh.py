from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .oddspapi_provider import ENV_KEY, SPORT_ID, _get
from .oddspapi_quota_health import summarize_account

CATALOG_PATH = Path('data/normalized/oddspapi_market_catalog.json')
REPORT_PATH = Path('reports/oddspapi_market_catalog_refresh.json')
CORE_QUOTA_RESERVE = 30


def _rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        raw = payload.get('data') or payload.get('markets') or []
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]
    return []


def summarize_catalog(rows: list[dict]) -> dict:
    soccer = [r for r in rows if r.get('sportId') == SPORT_ID]
    fulltime = [r for r in soccer if str(r.get('period') or '').lower() == 'fulltime' and r.get('playerProp') is not True]
    ah = [r for r in fulltime if 'asian handicap' in str(r.get('marketName') or '').lower()]
    ou = [r for r in fulltime if 'over under' in str(r.get('marketName') or '').lower() or str(r.get('marketType') or '').lower() == 'totals']
    one_x_two = [r for r in fulltime if str(r.get('marketType') or '').lower() == '1x2']
    ids = {str(r.get('marketId')) for r in fulltime if r.get('marketId') is not None}
    return {
        'soccer_markets': len(soccer),
        'fulltime_non_player_markets': len(fulltime),
        'unique_fulltime_market_ids': len(ids),
        'asian_handicap_markets': len(ah),
        'over_under_markets': len(ou),
        'one_x_two_markets': len(one_x_two),
        'valid_for_strict_parser': bool(ah and ou and one_x_two),
    }


def run(root: Path = Path('.')) -> dict:
    now = datetime.now(timezone.utc)
    report = {
        'schema_version': '1.0',
        'generated_at': now.isoformat(),
        'provider': 'oddspapi',
        'purpose': 'ONE_TIME_OR_MANUAL_MARKET_CATALOG_REFRESH',
        'core_quota_reserve': CORE_QUOTA_RESERVE,
    }
    key = os.getenv(ENV_KEY, '').strip()
    if not key:
        report['status'] = 'API_KEY_NOT_CONFIGURED'
    else:
        try:
            quota = summarize_account(_get('/account', key))
        except Exception as exc:
            report.update(status='SKIPPED_QUOTA_HEALTH_UNAVAILABLE', errors=[f'{type(exc).__name__}: {exc}'])
        else:
            remaining = quota.get('request_remaining')
            report['quota_remaining_before'] = remaining
            try:
                allowed = quota.get('status') == 'QUOTA_AVAILABLE' and int(remaining) > CORE_QUOTA_RESERVE
            except (TypeError, ValueError):
                allowed = False
            if not allowed:
                report['status'] = 'SKIPPED_TO_PROTECT_CORE_QUOTA'
            else:
                try:
                    rows = _rows(_get('/markets', key, {'sportId': SPORT_ID, 'language': 'en'}))
                except Exception as exc:
                    report.update(status='MARKET_CATALOG_REQUEST_FAILED', requests_used=1, errors=[f'{type(exc).__name__}: {exc}'])
                else:
                    summary = summarize_catalog(rows)
                    report.update(summary, requests_used=1)
                    if not summary['valid_for_strict_parser']:
                        report['status'] = 'REFRESH_REJECTED_INVALID_CATALOG'
                    else:
                        path = root / CATALOG_PATH
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(json.dumps(rows, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
                        report['status'] = 'CATALOG_REFRESHED'
    out = root / REPORT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
