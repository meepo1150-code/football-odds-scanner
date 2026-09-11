from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_PATH = Path('data/normalized/europe_discovery_snapshots.jsonl')
TARGET_PATH = Path('reports/europe_discovery_tournaments.json')
REPORT_PATH = Path('reports/europe_discovery_summary.json')


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _load_jsonl(path: Path):
    rows = []
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


def summarize(rows, targets=None):
    targets = targets or []
    expected = {(str(x.get('country') or ''), str(x.get('tournament_name') or '')) for x in targets if isinstance(x, dict)}
    by_league = defaultdict(lambda: {'observations': 0, 'fixtures': set(), 'candidate_like_observations': 0, 'candidate_like_hits': 0})
    pattern_hits = Counter()
    observed_days = set()
    fixtures = set()

    for row in rows:
        league = str(row.get('league') or row.get('tournament_name') or 'UNKNOWN')
        country = str(row.get('country') or '')
        key = (country, league)
        fixture_id = str(row.get('fixture_id') or '')
        observed_at = str(row.get('observed_at') or '')
        if observed_at:
            observed_days.add(observed_at[:10])
        if fixture_id:
            fixtures.add(fixture_id)
            by_league[key]['fixtures'].add(fixture_id)
        by_league[key]['observations'] += 1
        matches = [str(x) for x in (row.get('candidate_like_matches') or [])]
        if matches:
            by_league[key]['candidate_like_observations'] += 1
            by_league[key]['candidate_like_hits'] += len(matches)
            pattern_hits.update(matches)

    leagues = []
    all_keys = sorted(expected | set(by_league))
    for country, league in all_keys:
        stats = by_league[(country, league)]
        leagues.append({
            'country': country,
            'league': league,
            'observations': stats['observations'],
            'unique_fixtures': len(stats['fixtures']),
            'candidate_like_observations': stats['candidate_like_observations'],
            'candidate_like_hits': stats['candidate_like_hits'],
            'coverage_status': 'OBSERVED' if stats['observations'] else 'NO_STRICT_OBSERVATION_YET',
        })

    return {
        'schema_version': '1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'classification': 'EUROPE_DISCOVERY_ONLY',
        'production_promotion_allowed': False,
        'validation_gate_effect': 'NONE',
        'interpretation': 'Descriptive accumulation only. Candidate-like frequency is not evidence of edge, profitability, or promotion eligibility.',
        'observation_days': len(observed_days),
        'strict_observations': len(rows),
        'unique_fixtures': len(fixtures),
        'target_leagues': len(expected),
        'leagues_with_strict_observations': sum(1 for x in leagues if x['observations'] > 0),
        'candidate_like_observations': sum(1 for row in rows if row.get('candidate_like_matches')),
        'candidate_like_hits': sum(len(row.get('candidate_like_matches') or []) for row in rows),
        'pattern_hits': dict(sorted(pattern_hits.items())),
        'league_coverage': leagues,
    }


def run():
    target_doc = _load_json(TARGET_PATH) or {}
    targets = target_doc.get('tournaments', []) if isinstance(target_doc, dict) else []
    report = summarize(_load_jsonl(SNAPSHOT_PATH), targets)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
