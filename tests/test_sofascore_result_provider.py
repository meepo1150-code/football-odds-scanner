from io import BytesIO
from pathlib import Path

from odds_scanner.sofascore_result_provider import backfill_results, normalize_sofascore_result
from odds_scanner.oddspapi_fixture_refs import REFS_PATH
from odds_scanner.oddspapi_result_cache import RESULTS_PATH


def test_normalize_sofascore_result_requires_finished_exact_id_and_normaltime():
    payload = {
        "event": {
            "id": 123,
            "status": {"type": "finished"},
            "homeScore": {"current": 3, "normaltime": 2},
            "awayScore": {"current": 2, "normaltime": 1},
        }
    }
    out = normalize_sofascore_result(payload, fixture_id="f1", sofascore_id=123)
    assert out["ft_home_goals"] == 2
    assert out["ft_away_goals"] == 1
    assert out["result_source"] == "SOFASCORE_EXACT_EXTERNAL_ID_NORMALTIME"
    assert normalize_sofascore_result(payload, fixture_id="f1", sofascore_id=999) is None

    payload["event"]["status"]["type"] = "inprogress"
    assert normalize_sofascore_result(payload, fixture_id="f1", sofascore_id=123) is None


def test_normalize_rejects_current_only_score():
    payload = {
        "event": {
            "id": 123,
            "status": {"type": "finished"},
            "homeScore": {"current": 2},
            "awayScore": {"current": 1},
        }
    }
    assert normalize_sofascore_result(payload, fixture_id="f1", sofascore_id=123) is None


class _Response:
    def __init__(self, body: bytes):
        self._body = body
    def read(self):
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def test_backfill_uses_exact_refs_and_merges_cache(tmp_path: Path):
    refs = tmp_path / REFS_PATH
    refs.parent.mkdir(parents=True, exist_ok=True)
    refs.write_text('{"fixture_id":"f1","sofascore_id":123}\n', encoding="utf-8")

    def opener(request, timeout=15):
        body = b'{"event":{"id":123,"status":{"type":"finished"},"homeScore":{"normaltime":2},"awayScore":{"normaltime":1}}}'
        return _Response(body)

    report = backfill_results(tmp_path, max_results=10, opener=opener, sleep_fn=lambda _: None)
    assert report["results_added"] == 1
    cached = (tmp_path / RESULTS_PATH).read_text(encoding="utf-8")
    assert '"fixture_id":"f1"' in cached
    assert '"ft_home_goals":2' in cached
