"""Bounded master identity research; never requests odds or enables production scans."""
import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .oddspapi_provider import _get
from .oddspapi_quota_health import summarize_account

OUT = Path('reports/master_provider_snapshot.json')
RESERVE = 50


def collect(key, *, get=_get, now=None, root=Path('.'), previous=None, window_end=None, targeted=False):
    now = now or datetime.now(timezone.utc)
    result = dict(schema_version='1.0', provider='oddspapi', generated_at=now.isoformat(), metered_requests_attempted=0, max_metered_requests=3, production_enabled=False)
    try:
        result['quota'] = summarize_account(get('/account', key))
        if result['quota'].get('status') != 'QUOTA_AVAILABLE' or result['quota'].get('request_remaining', 0) < RESERVE + 3:
            result['status'] = 'BLOCKED_QUOTA_RESERVE'
            return result
        if not result['quota'].get('soccer_sport_id_10_allowed'):
            result['status'] = 'BLOCKED_SPORT_ENTITLEMENT'
            return result
        params = dict(sportId=10, language='en')
        if previous is None:
            result['metered_requests_attempted'] += 1
            tournaments = get('/tournaments', key, params, timeout=45)
        else:
            tournaments = previous['tournaments']
            result['tournaments_reused_from'] = previous['generated_at']
        if not isinstance(tournaments, list):
            raise ValueError('Invalid tournament catalog shape')
        fields = ('tournamentId', 'tournamentName', 'tournamentSlug', 'categoryName', 'categorySlug', 'futureFixtures', 'upcomingFixtures', 'liveFixtures')
        result['tournaments'] = [{k: r[k] for k in fields if k in r} for r in tournaments]
        result['metered_requests_attempted'] += 1
        participants = get('/participants', key, params, timeout=45)
        if not isinstance(participants, dict):
            raise ValueError('Invalid participant catalog shape')
        result['participant_catalog_count'] = len(participants)
        end = window_end or (now + timedelta(days=9) if previous is None else now)
        start = now if previous is None else end - timedelta(days=9)
        if targeted:
            fixtures = []
            result['identity_targets'] = []
            for aliases in ({'Hegelmann Litauen', 'FC Hegelmann', 'Hegelmann', 'FC Hegelmann Litauen'},):
                selected = [(pid, name) for pid, name in participants.items() if name in aliases]
                if len(selected) != 1:
                    result['identity_targets'].append({'status': 'AMBIGUOUS_OR_ABSENT_PARTICIPANT', 'candidates': [{'participant_id': str(pid), 'provider_name': name} for pid, name in participants.items() if isinstance(name, str) and 'hegelmann' in name.casefold()]})
                    continue
                pid, name = selected[0]
                result['metered_requests_attempted'] += 1
                found = get('/fixtures', key, {**params, 'participantId': pid, 'from': '2026-01-01T00:00:00+00:00'}, timeout=45)
                if not isinstance(found, list):
                    raise ValueError('Invalid targeted fixtures shape')
                fixtures.extend(found)
                result['identity_targets'].append({'participant_id': str(pid), 'provider_name': name, 'fixtures_returned': len(found)})
        else:
            result['metered_requests_attempted'] += 1
            fixtures = get('/fixtures', key, {**params, 'from': start.isoformat(), 'to': end.isoformat(), 'limit': 1000}, timeout=45)
        if not isinstance(fixtures, list):
            raise ValueError('Invalid fixtures shape')
        fields = ('fixtureId', 'tournamentId', 'tournamentName', 'seasonId', 'startTime', 'statusId', 'participant1Id', 'participant1Name', 'participant2Id', 'participant2Name')
        combined = {r['fixtureId']: r for r in (previous or {}).get('fixtures', [])}
        combined.update({r['fixtureId']: {k: r[k] for k in fields if k in r} for r in fixtures})
        result['fixtures'] = list(combined.values())
        result['fixture_window'] = {'from': start.isoformat(), 'to': end.isoformat(), 'limit_requested': 1000, 'returned_count': len(fixtures), 'complete_rosters': False}
        names = set()
        for filename, field in [('uefa_clubs_canonical.csv', 'canonical_name'), ('research/club_assignments.csv', 'source_name')]:
            with (root / 'data/master' / filename).open() as handle:
                names.update(r[field].casefold().strip() for r in csv.DictReader(handle))
        ids = {str(r[k]) for r in result['fixtures'] for k in ('participant1Id', 'participant2Id') if k in r}
        # Retain identity candidates only; names do not authorize a club mapping.
        result['participants'] = {str(k): v for k, v in participants.items() if str(k) in ids or isinstance(v, str) and v.casefold().strip() in names}
        result['participant_selection'] = 'FIXTURE_ID_OR_EXACT_MASTER_NAME_CANDIDATE_ONLY_NOT_VERIFIED_MAPPING'
        result['status'] = 'SNAPSHOT_AVAILABLE_REQUIRES_IDENTITY_REVIEW'
    except Exception as exc:
        # Never log URL/repr/body: transports may embed apiKey in exception text.
        result['status'] = 'BLOCKED_PROVIDER_RESPONSE'
        result['error_type'] = type(exc).__name__
        result['http_status'] = getattr(exc, 'code', None)
    return result


def main():
    key = os.environ.get('ODDSPAPI_KEY')
    if not key:
        raise SystemExit('Provider key is not configured')
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--lookback', action='store_true')
    parser.add_argument('--window-end', type=datetime.fromisoformat)
    parser.add_argument('--targeted', action='store_true')
    args = parser.parse_args()
    previous = json.loads(OUT.read_text()) if args.lookback else None
    report = collect(key, previous=previous, window_end=args.window_end, targeted=args.targeted)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'metered_requests_attempted', 'generated_at')}))


if __name__ == '__main__':
    main()
