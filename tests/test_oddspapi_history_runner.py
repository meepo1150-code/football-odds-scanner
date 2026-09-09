from datetime import datetime, timezone
from io import BytesIO
from urllib.error import HTTPError

import pytest
import odds_scanner.oddspapi_history_runner as runner


def test_discover_finished_big5_uses_minimal_fixture_contract_and_harvests_exact_refs(monkeypatch):
    calls=[]; cached=[]; refs=[]
    def fake_get(path,key,params=None):
        calls.append((path,params))
        return [
            {"fixtureId":"ok","statusId":2,"tournamentId":17,"startTime":"2026-01-03T15:00:00Z","participant1Name":"A","participant2Name":"B","participant1Score":2,"participant2Score":1,"externalProviders":{"sofascoreId":101}},
            {"fixtureId":"live","statusId":1,"tournamentId":17,"participant1Score":1,"participant2Score":0,"externalProviders":{"sofascoreId":102}},
            {"fixtureId":"noodds","statusId":2,"tournamentId":17,"startTime":"2026-01-04T15:00:00Z","participant1Name":"C","participant2Name":"D","externalProviders":{"sofascoreId":103}},
            {"fixtureId":"other","statusId":2,"tournamentId":999,"participant1Score":3,"participant2Score":0,"externalProviders":{"sofascoreId":104}},
        ]
    def fake_merge(path,fixtures): cached.extend(fixtures); return 1
    def fake_refs(path,fixtures): refs.extend(fixtures); return 2
    monkeypatch.setattr(runner,"provider_get",fake_get)
    monkeypatch.setattr(runner,"merge_results",fake_merge)
    monkeypatch.setattr(runner,"merge_fixture_refs",fake_refs)
    rows=runner.discover_finished_big5_window("test",datetime(2026,1,1,tzinfo=timezone.utc),datetime(2026,1,10,tzinfo=timezone.utc))
    assert [r["fixtureId"] for r in rows]==["ok","noodds"]
    assert [f["fixtureId"] for f in cached]==["ok","noodds"]
    assert [f["fixtureId"] for f in refs]==["ok","noodds"]
    assert len(calls)==1
    path,params=calls[0]
    assert path=="/fixtures" and params["sportId"]==10 and params["limit"]==300
    assert "statusId" not in params and "hasOdds" not in params and "bookmakers" not in params


def _http_error(code):
    return HTTPError("https://api.oddspapi.io/v4/test",code,"test",{},BytesIO(b""))

def test_historical_404_becomes_empty_history(monkeypatch):
    monkeypatch.setattr(runner,"provider_get",lambda *a,**k: (_ for _ in ()).throw(_http_error(404)))
    assert runner._history_aware_get("/historical-odds","test",{"fixtureId":"x"})=={"bookmakers":{}}

def test_non404_and_nonhistorical_errors_still_propagate(monkeypatch):
    monkeypatch.setattr(runner,"provider_get",lambda *a,**k: (_ for _ in ()).throw(_http_error(429)))
    with pytest.raises(HTTPError) as exc: runner._history_aware_get("/historical-odds","test",{"fixtureId":"x"})
    assert exc.value.code==429
    monkeypatch.setattr(runner,"provider_get",lambda *a,**k: (_ for _ in ()).throw(_http_error(404)))
    with pytest.raises(HTTPError): runner._history_aware_get("/fixtures","test",{})
