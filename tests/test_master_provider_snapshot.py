from datetime import datetime, timezone
from odds_scanner.master_provider_snapshot import collect


def test_quota_blocks_all_metered_calls():
    calls = []
    def get(path, key, *args, **kwargs):
        calls.append(path)
        return {}
    report = collect('secret', get=get)
    assert calls == ['/account']
    assert report['metered_requests_attempted'] == 0
    assert report['status'] == 'BLOCKED_QUOTA_RESERVE'


def test_snapshot_is_bounded_and_never_exposes_transport_secret(monkeypatch):
    calls = []
    monkeypatch.setattr('odds_scanner.master_provider_snapshot.summarize_account', lambda _: dict(status='QUOTA_AVAILABLE', request_remaining=146, soccer_sport_id_10_allowed=True))
    def get(path, key, *args, **kwargs):
        calls.append(path)
        if path == '/account': return {}
        if path == '/tournaments': return []
        raise RuntimeError('apiKey=secret')
    report = collect('secret', get=get)
    assert calls == ['/account', '/tournaments', '/participants']
    assert report['metered_requests_attempted'] == 2
    assert report['status'] == 'BLOCKED_PROVIDER_RESPONSE'
    assert 'secret' not in str(report)


def test_successful_snapshot_has_exact_ids_without_claiming_complete_rosters(monkeypatch, tmp_path):
    monkeypatch.setattr('odds_scanner.master_provider_snapshot.summarize_account', lambda _: dict(status='QUOTA_AVAILABLE', request_remaining=146, soccer_sport_id_10_allowed=True))
    root = tmp_path / 'data/master'
    (root / 'research').mkdir(parents=True)
    (root / 'uefa_clubs_canonical.csv').write_text('canonical_name\nArsenal\n')
    (root / 'research/club_assignments.csv').write_text('source_name\nChelsea\n')
    calls = []
    def get(path, key, params=None, **kwargs):
        calls.append(path)
        return {'/account': {}, '/tournaments': [{'tournamentId': 17, 'tournamentName': 'Premier League', 'categoryName': 'England'}], '/participants': {'3': 'Arsenal', '4': 'Chelsea', '5': 'Other'}, '/fixtures': [{'fixtureId': 'exact-id', 'tournamentId': 17, 'participant1Id': 3, 'participant2Id': 4, 'secretField': 'omit'}]}[path]
    report = collect('secret', get=get, root=tmp_path, now=datetime(2026, 10, 9, tzinfo=timezone.utc))
    assert report['metered_requests_attempted'] == 3
    assert len(calls) == 4
    assert report['participants'] == {'3': 'Arsenal', '4': 'Chelsea'}
    assert report['fixtures'][0]['fixtureId'] == 'exact-id'
    assert 'secretField' not in report['fixtures'][0]
    assert report['fixture_window']['complete_rosters'] is False
    assert report['production_enabled'] is False
