import pytest
from odds_scanner.oddspapi_prematch import extract_fixture
from odds_scanner.settled_history import settle_row


def _raw(line=-0.75, ou_line=2.75):
    return {
        "fixture_id": "x", "league": "E0", "kickoff": "2026-01-02T15:00:00Z",
        "home": "A", "away": "B", "bookmaker": "Bet365",
        "asian_handicap": [{
            "line": line,
            "home": [
                {"created_at": "2026-01-02T10:00:00Z", "price": 1.90},
                {"created_at": "2026-01-02T14:59:00Z", "price": 2.00},
                {"created_at": "2026-01-02T15:00:00Z", "price": 9.99},
            ],
            "away": [
                {"created_at": "2026-01-02T10:00:00Z", "price": 2.00},
                {"created_at": "2026-01-02T14:58:00Z", "price": 1.90},
            ],
        }],
        "over_under": [{
            "line": ou_line,
            "over": [
                {"created_at": "2026-01-02T10:01:00Z", "price": 2.00},
                {"created_at": "2026-01-02T14:57:00Z", "price": 1.95},
            ],
            "under": [
                {"created_at": "2026-01-02T10:01:00Z", "price": 1.90},
                {"created_at": "2026-01-02T14:57:00Z", "price": 1.95},
            ],
        }],
    }


def _joined(**kwargs):
    row = extract_fixture(_raw(**kwargs))
    row.update({"ft_home_goals": 2, "ft_away_goals": 1, "result_source": "explicit", "result_join_status": "JOINED"})
    return row


def test_nested_shape_emits_both_sides_and_both_stages():
    out = settle_row(_joined())
    assert len(out) == 8
    by = {(r["market_type"], r["selection"], r["snapshot_stage"]): r for r in out}

    h_open = by[("AH", "H", "OPENING")]
    assert h_open["line"] == -0.75 and h_open["selected_side_line"] == -0.75
    assert h_open["settlement"] == "HALF_WIN" and h_open["profit_units"] == 0.45
    assert h_open["quote_at"] == "2026-01-02T10:00:00Z"
    assert h_open["opposite_side_price"] == 2.0

    a_open = by[("AH", "A", "OPENING")]
    assert a_open["selected_side_line"] == 0.75
    assert a_open["settlement"] == "HALF_LOSS"

    h_close = by[("AH", "H", "CLOSING_PREMATCH")]
    assert h_close["price"] == 2.0
    assert h_close["quote_at"] == "2026-01-02T14:59:00Z"
    assert h_close["price"] != 9.99  # kickoff tick must never enter prematch settlement

    assert by[("OU", "O", "OPENING")]["settlement"] == "HALF_WIN"
    assert by[("OU", "U", "OPENING")]["settlement"] == "HALF_LOSS"
    assert all(r["promotion_eligible"] is False for r in out)
    assert all(r["source_semantics"] == "STRICT_PREMATCH_CREATED_AT_LT_KICKOFF" for r in out)


def test_missing_opposite_side_does_not_create_unpaired_observation():
    row = _joined()
    row["asian_handicap"][0].pop("away")
    out = settle_row(row)
    assert not any(r["market_type"] == "AH" for r in out)
    assert len(out) == 4


def test_non_quarter_lines_are_not_rounded_or_settled():
    out = settle_row(_joined(line=-0.70, ou_line=2.73))
    assert out == []
