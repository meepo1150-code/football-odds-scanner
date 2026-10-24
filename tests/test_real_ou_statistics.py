"""Real O/U, per-line and per-price rules; never infer a 2.5 quote."""
import json

from odds_scanner.real_ou_statistics import _quote, real_ou_outcome, aggregate_real_ou
from odds_scanner.research_v2_pattern_stats import build, SNAPSHOTS, RESULTS


def snapshot(fid="x", line=2.75, op=1.85, up=1.95, when="2026-09-29T10:00:00Z"):
    return {
        "fixture_id": fid, "football_day": "2026-09-29",
        "provider": "oddspapi", "bookmaker": "pinnacle",
        "source_semantics": "CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED",
        "observed_at": when, "kickoff": "2026-09-29T12:00:00Z",
        "favorite_side": "H", "home": "H", "away": "A",
        "ah": {"home_line": -0.75, "away_line": 0.75, "home_price": 1.90,
               "away_price": 2, "selected_side_line": -0.75,
               "selected_side_price": 1.90},
        "ou": {"line": line, "over_price": op, "under_price": up},
    }


def test_explicit_user_examples_lose_push_half_win():
    # Over 2.25 (2 goals) => lose the full stake.
    r = real_ou_outcome(snapshot(line=2.25), 1, 1)
    assert r["ou_real_over_settlement"] == "FULL_LOSS"
    assert r["ou_real_over_profit_units"] == -1
    # Over 3.00 (3 goals) => a refunded stake, not a win.
    r = real_ou_outcome(snapshot(line=3.0), 2, 1)
    assert r["ou_real_over_settlement"] == "PUSH"
    assert r["ou_real_over_profit_units"] == 0
    # Over 2.75 (3 goals) => half-win, counts positively in WR but ROI half.
    r = real_ou_outcome(snapshot(line=2.75), 2, 1)
    assert r["ou_real_over_settlement"] == "HALF_WIN"
    assert abs(r["ou_real_over_profit_units"] - .425) < 1e-9
    assert r["ou_real_under_settlement"] == "HALF_LOSS"
    assert r["ou_real_under_profit_units"] == -.5


def test_missing_ou_is_note_only_not_2point5():
    s = snapshot()
    s.pop("ou")
    r = real_ou_outcome(s, 2, 1)
    assert r["ou_real_quote_status"] == "MISSING_OU"
    assert r["ou_real_line"] is None
    assert r["ou_real_over_settlement"] is None


def test_no_fabricated_or_nonprematch_odds():
    for bad in [None, 0, 1, float("nan"), float("inf")]:
        s = snapshot()
        s["ou"]["over_price"] = bad
        assert _quote(s)[0] is None
    for field, bad in [("observed_at", "2026-09-29T12:00:00Z"),
                       ("bookmaker", None), ("source_semantics", None)]:
        s = snapshot()
        s[field] = bad
        assert _quote(s)[0] is None
    s = snapshot()
    s["mainline_verified"] = False
    s["source_semantics"] = "PINNWIRE_PREMATCH_FULL_SNAPSHOT"
    q, reason = _quote(s)
    assert q is not None and not q["mainline_verified"]
    assert reason == "PAIRED_QUOTE_MAINLINE_UNVERIFIED"


def test_group_real_ou_by_each_side_and_own_price_bucket():
    rows = []
    for i, (g1, g2) in enumerate(((2, 1), (1, 1), (2, 1))):
        s = snapshot(fid=str(i), line=2.75)
        s.update(market_side="HOME_FAVORITE", ah_line=-.75, ah_price_bucket="1.90-1.99",
                 ft_home_goals=g1, ft_away_goals=g2)
        rows.append({**s, **real_ou_outcome(s, g1, g2)})
    summary = aggregate_real_ou(rows)
    over = next(x for x in summary["real_ou_by_ah_line_price_ou_line_price"]
                if x["selection"] == "OVER")
    under = next(x for x in summary["real_ou_by_ah_line_price_ou_line_price"]
                 if x["selection"] == "UNDER")
    assert over["n"] == 3 and over["half_win"] == 2 and over["full_loss"] == 1
    assert over["price_win_pct"] == 66.67
    assert over["roi_pct"] == -5.0
    assert under["half_loss"] == 2 and under["full_win"] == 1
    assert under["price_win_pct"] == 33.33
    assert under["roi_pct"] == 0


def test_end_to_end_uses_latest_per_fixture_and_no_ou_not_in_denominator(tmp_path):
    snapshots = [
        snapshot("one", line=2.25, when="2026-09-29T09:00:00Z"),
        snapshot("one", line=2.75, when="2026-09-29T10:00:00Z"),
        snapshot("two", line=3.0),
        snapshot("no_ou"),
    ]
    snapshots[-1].pop("ou")
    results = [
        {"fixture_id": "one", "ft_home_goals": 2, "ft_away_goals": 1},
        {"fixture_id": "two", "ft_home_goals": 2, "ft_away_goals": 1},
        {"fixture_id": "no_ou", "ft_home_goals": 1, "ft_away_goals": 1},
    ]
    for path, rows in ((SNAPSHOTS, snapshots), (RESULTS, results)):
        output = tmp_path / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("".join(json.dumps(row) + "\n" for row in rows))
    d = build(tmp_path)
    assert d["settled_fixtures"] == 3
    assert d["real_ou_settled_fixtures_with_paired_quote"] == 2
    selections = d["real_ou_by_ah_line_price_ou_line_price"]
    assert sum(x["n"] for x in selections if x["selection"] == "OVER") == 2
    over_two75 = next(x for x in selections
                      if x["selection"] == "OVER" and x["ou_line"] == "2.75")
    assert over_two75["half_win"] == 1 and over_two75["price_win_pct"] == 100
    over_three = next(x for x in selections
                      if x["selection"] == "OVER" and x["ou_line"] == "3")
    assert over_three["push"] == 1 and over_three["price_win_pct"] == 0
    assert d["real_ou_quote_status_counts"]["MISSING_OU"] == 1
