from odds_scanner import propline_provider as p


def test_decimal_conversion_supports_american_and_decimal():
    assert p._dec(330) == 4.3
    assert round(p._dec(-112), 6) == round(1 + 100/112, 6)
    assert p._dec(1.95) == 1.95


def test_fetch_chooses_balanced_mainline_not_high_price_alternate(monkeypatch):
    monkeypatch.setattr(p, "active_soccer_sports", lambda key: ("soccer_test",))
    event={"id":"1","commence_time":"2026-09-29T18:00:00Z","home_team":"A","away_team":"B","bookmakers":[{"key":"pinnacle","last_update":"2026-09-29T14:00:00Z","markets":[
      {"key":"spreads","outcomes":[{"name":"A","point":-1.5,"price":330},{"name":"B","point":1.5,"price":-450}]},
      {"key":"spreads","outcomes":[{"name":"A","point":-0.5,"price":-105},{"name":"B","point":0.5,"price":-105}]}
    ]}]}
    monkeypatch.setattr(p, "_get", lambda path,key,params=None: [event])
    rows,errors=p.fetch("x")
    assert not errors and len(rows)==1
    assert rows[0]["ah_home_line"] == -0.5
    assert 1.80 <= rows[0]["ah_home_odds"] <= 2.20
    assert 1.80 <= rows[0]["ah_away_odds"] <= 2.20


def test_fetch_rejects_event_when_only_alternate_spread_exists(monkeypatch):
    monkeypatch.setattr(p, "active_soccer_sports", lambda key: ("soccer_test",))
    event={"id":"1","commence_time":"2026-09-29T18:00:00Z","home_team":"A","away_team":"B","bookmakers":[{"key":"pinnacle","markets":[
      {"key":"spreads","outcomes":[{"name":"A","point":-1.5,"price":330},{"name":"B","point":1.5,"price":-450}]}
    ]}]}
    monkeypatch.setattr(p, "_get", lambda path,key,params=None: [event])
    rows,errors=p.fetch("x")
    assert rows == [] and errors == []
