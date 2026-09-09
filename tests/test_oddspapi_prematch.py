from odds_scanner.oddspapi_prematch import opening_closing, extract_fixture


def test_opening_closing_excludes_kickoff_and_inplay_ticks():
    series=[
        {"created_at":"2026-01-01T10:00:00Z","price":2.0,"active":True},
        {"created_at":"2026-01-01T11:59:59Z","price":1.9,"active":True},
        {"created_at":"2026-01-01T12:00:00Z","price":1.8,"active":True},
        {"created_at":"2026-01-01T12:01:00Z","price":1.7,"active":True},
    ]
    out=opening_closing(series,"2026-01-01T12:00:00Z")
    assert out["opening_price"]==2.0
    assert out["closing_price"]==1.9
    assert out["prematch_tick_count"]==2


def test_extract_fixture_keeps_exact_line_and_two_sides():
    t1={"created_at":"2026-01-01T10:00:00Z","price":1.95,"active":True}
    t2={"created_at":"2026-01-01T11:59:00Z","price":2.05,"active":True}
    row={"fixture_id":"1","league":"L","kickoff":"2026-01-01T12:00:00Z","home":"A","away":"B","bookmaker":"bet365",
         "one_x_two":{"home":[t1],"draw":[t1],"away":[t1]},
         "asian_handicap":[{"line":-0.75,"home":[t1,t2],"away":[t1,t2]}],
         "over_under":[{"line":2.75,"over":[t1,t2],"under":[t1,t2]}]}
    out=extract_fixture(row)
    assert out["asian_handicap"][0]["line"]==-0.75
    assert out["over_under"][0]["line"]==2.75
    assert out["asian_handicap"][0]["home"]["closing_price"]==2.05
    assert out["snapshot_semantics"]=="STRICT_PREMATCH_CREATED_AT_LT_KICKOFF"
    assert out["promotion_eligible"] is False
