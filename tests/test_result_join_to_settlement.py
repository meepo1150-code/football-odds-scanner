from odds_scanner.oddspapi_result_join import join_rows
from odds_scanner.settled_history import settle_row


def test_exact_join_then_quarter_line_settlement():
    ticks = [{
        "fixture_id": "f1",
        "asian_handicap": [{
            "line": -0.75,
            "home": {"opening_price": 1.9, "opening_at": "2026-01-01T10:00:00Z", "closing_price": 1.9, "closing_at": "2026-01-01T10:00:00Z"},
            "away": {"opening_price": 2.0, "opening_at": "2026-01-01T10:00:00Z", "closing_price": 2.0, "closing_at": "2026-01-01T10:00:00Z"},
        }],
        "over_under": [{
            "line": 2.75,
            "over": {"opening_price": 2.0, "opening_at": "2026-01-01T10:00:00Z", "closing_price": 2.0, "closing_at": "2026-01-01T10:00:00Z"},
            "under": {"opening_price": 1.9, "opening_at": "2026-01-01T10:00:00Z", "closing_price": 1.9, "closing_at": "2026-01-01T10:00:00Z"},
        }],
    }]
    results = [{"fixture_id": "f1", "ft_home_goals": 2, "ft_away_goals": 1, "result_source": "explicit"}]
    joined, report = join_rows(ticks, results)
    assert report["join_rate"] == 1.0 and report["promotion_allowed"] is False

    settled = settle_row(joined[0])
    assert settled
    assert all(obs["promotion_eligible"] is False for obs in settled)

    by = {(obs["market_type"], obs["selection"], obs["snapshot_stage"]): obs for obs in settled}
    assert by[("AH", "H", "OPENING")]["settlement"] == "HALF_WIN"
    assert by[("AH", "A", "OPENING")]["selected_side_line"] == 0.75
    assert by[("OU", "O", "OPENING")]["settlement"] == "HALF_WIN"
    assert by[("OU", "U", "OPENING")]["settlement"] == "HALF_LOSS"
