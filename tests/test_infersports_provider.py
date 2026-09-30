import json
from pathlib import Path

import odds_scanner.infersports_provider as provider
from odds_scanner.infersports_provider import _two_sided


def test_two_sided_asian_handicap_prices():
    assert _two_sided({"market_type": "asian_handicap", "prices": {"home": 1.91, "away": 1.95}})
    assert not _two_sided({"market_type": "asian_handicap", "prices": {"home": 1.91}})


def test_two_sided_totals_prices():
    assert _two_sided({"market_type": "totals", "prices": {"over": 1.88, "under": 2.02}})
    assert not _two_sided({"market_type": "totals", "prices": {"over": 1.88, "under": 1.0}})


def test_three_way_requires_all_prices():
    assert _two_sided({"market_type": "1x2", "prices": {"home": 2.1, "draw": 3.2, "away": 3.4}})
    assert not _two_sided({"market_type": "1x2", "prices": {"home": 2.1, "away": 3.4}})


def test_event_list_without_ids_is_not_healthy_odds(monkeypatch):
    monkeypatch.setattr(provider,'list_scheduled_football',lambda **kw:[{'name':'unknown'}])
    out=provider.probe()
    assert out['status']=='NO_USABLE_MARKETS'
    assert out['events_probed']==0 and out['missing_event_ids']==1
    assert out['execution_candidate'] is False


def test_write_health_records_provider_failure_instead_of_raising(tmp_path: Path, monkeypatch):
    def boom(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(provider, "probe", boom)
    out = provider.write_health(tmp_path)
    assert out["status"] == "UNAVAILABLE"
    assert out["execution_candidate"] is False
    persisted = json.loads((tmp_path / "reports/infersports_health.json").read_text())
    assert persisted["status"] == "UNAVAILABLE"


def test_live_id_shape_and_no_unverified_execution_promotion(monkeypatch):
    from datetime import datetime,timedelta,timezone
    future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    monkeypatch.setattr(provider,'list_scheduled_football',lambda **kw:[{'id':'real-id','scheduled_at':future}])
    ids=[]
    def odds(event_id):
        ids.append(event_id)
        return {'stale':False,'odds':[{'market_type':'asian_handicap','prices':{'home':1.9,'away':1.9}},{'market_type':'totals','prices':{'over':1.9,'under':1.9}}]}
    monkeypatch.setattr(provider,'event_odds',odds)
    result=provider.probe()
    assert ids==['real-id'] and result['status']=='MARKETS_OBSERVED'
    assert result['execution_candidate'] is False
    assert result['capability']=='HEALTH_ONLY'


def test_provider_scheduled_label_cannot_override_past_kickoff(monkeypatch):
    monkeypatch.setattr(provider,'list_scheduled_football',lambda **kw:[{'id':'old','scheduled_at':'2020-01-01T00:00:00Z','status':'scheduled'}])
    monkeypatch.setattr(provider,'event_odds',lambda _: (_ for _ in ()).throw(AssertionError('must not fetch')))
    result=provider.probe()
    assert result['excluded_nonfuture_events']==1 and result['events_probed']==0
