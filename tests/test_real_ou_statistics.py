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
    # Over 2.25 (2 goals) => HALF_LOSS: counted as loss for WR.
    r = real_ou_outcome(snapshot(line=2.25), 1, 1)
    assert r["ou_real_over_settlement"] == "HALF_LOSS"
    assert r["ou_real_over_profit_units"] == -.5
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
    assert under["roi_pct"] == -1.67


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

def test_paired_ou_uses_identical_cohort_and_complementary_percentages():
    rows = []
    for fid, line, over_price, under_price, score in [
        ("win_half", 2.75, 1.85, 1.95, (2, 1)),
        ("push", 3.0, 1.85, 1.95, (2, 1)),
        ("lose", 2.75, 1.85, 1.95, (1, 1)),
        ("other_under_bucket", 2.75, 1.85, 2.05, (2, 1)),
        ("win_half_2", 2.75, 1.85, 1.95, (2, 1)),
    ]:
        q = snapshot(fid, line, over_price, under_price)
        q.update(market_side="HOME_FAVORITE", ah_line=-.75,
                 ah_price_bucket="1.90-1.99",
                 ft_home_goals=score[0], ft_away_goals=score[1])
        rows.append({**q, **real_ou_outcome(q, *score)})
    out = aggregate_real_ou(rows)
    pairs = out["real_ou_paired_by_ah_line_price_ou_line_price_buckets"]
    primary = next(p for p in pairs if p["ou_line"] == "2.75"
                   and p["over_price_bucket"] == "1.80-1.89")
    # Under water varied between 1.95 and 2.05. All four fixtures must be
    # included in one Over-price cohort; Under quote is NOT an extra filter.
    assert primary["n"] == 4
    assert primary["over_win_n"] == 3
    assert primary["under_win_n"] == 1
    assert primary["push_n"] == 0
    assert primary["over_win_pct"] == 75
    assert primary["under_win_pct"] == 25
    assert primary["over_half_win"] == 3
    assert primary["under_half_loss"] == 3
    assert "under_price_bucket" not in primary
    push = next(p for p in pairs if p["ou_line"] == "3")
    assert push["n"] == 1 and push["push_n"] == 1
    assert push["over_win_n"] == push["under_win_n"] == 0
    assert push["over_win_pct"] == push["under_win_pct"] == 0
    assert push["push_pct"] == 100
    assert len(pairs) == 2
    assert out["real_ou_paired_price_grouping"].endswith("UNDER_ODDS_NOT_A_GROUPING_FILTER")
    assert all(p["over_win_n"] + p["under_win_n"] + p["push_n"] == p["n"]
               for p in pairs)


def test_end_to_end_paired_same_price_population(tmp_path):
    observations = [
        snapshot("a", line=2.75, op=1.85, up=1.95),
        snapshot("b", line=2.75, op=1.86, up=1.95),
        snapshot("c", line=2.75, op=1.85, up=2.05),
        snapshot("missing", line=2.75),
    ]
    observations[-1]["ou"] = {}
    results = [
        dict(fixture_id="a", ft_home_goals=2, ft_away_goals=1),
        dict(fixture_id="b", ft_home_goals=1, ft_away_goals=1),
        dict(fixture_id="c", ft_home_goals=2, ft_away_goals=1),
        dict(fixture_id="missing", ft_home_goals=1, ft_away_goals=1),
    ]
    for path, data in ((SNAPSHOTS, observations), (RESULTS, results)):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("".join(json.dumps(row) + "\n" for row in data))
    report = build(tmp_path)
    pairs = report["real_ou_paired_by_ah_line_price_ou_line_price_buckets"]
    assert sum(p["n"] for p in pairs) == 3
    assert len(pairs) == 1
    # These 3 rows share Over water 1.85/1.86 regardless of Under 1.95/2.05.
    assert pairs[0]["n"] == 3
    assert pairs[0]["over_win_n"] == 2
    assert pairs[0]["under_win_n"] == 1
    assert pairs[0]["over_price_bucket"] == "1.80-1.89"
    assert "under_price_bucket" not in pairs[0]


def test_global_over_cohort_ignores_all_ah_dimensions_and_under_odds():
    # Same real O/U line + Over water; fixtures have different AH directions,
    # lines, buckets, and also include an AH price outside the AH core range.
    definitions = [
        ("f1", "HOME_FAVORITE", -0.75, "1.90-1.99", 1.95, 2.75, 1.95, (2, 1)),
        ("f2", "AWAY_FAVORITE", -1.5, "1.80-1.89", 1.85, 2.05, 1.95, (1, 1)),
        ("f3", "HOME_FAVORITE", -0.25, "<1.80", 1.60, 2.15, 1.95, (2, 1)),
    ]
    rows=[]
    for fid, market, ahline, ah_bucket, ah_price, under_price, over_price, score in definitions:
        snap=snapshot(fid=fid, line=2.5, op=over_price, up=under_price)
        snap["ah"]["selected_side_line"]=ahline
        snap["ah"]["selected_side_price"]=ah_price
        snap.update(market_side=market, ah_line=ahline,
                    ah_price_bucket=ah_bucket, ah_core_price=1.8 <= ah_price <= 2.2,
                    ft_home_goals=score[0], ft_away_goals=score[1])
        rows.append({**snap, **real_ou_outcome(snap, *score)})
    report=aggregate_real_ou(rows)
    independent=report["real_ou_paired_by_line_over_price_bucket"]
    assert len(independent)==1
    group=independent[0]
    assert group["ou_line"]=="2.5"
    assert group["over_price_bucket"]=="1.90-1.99"
    assert group["n"]==3
    assert group["over_win_n"]==2 and group["under_win_n"]==1 and group["push_n"]==0
    assert group["over_win_pct"]==66.67
    assert group["under_win_pct"]==33.33
    assert not any(k.startswith("ah_") or k=="market_side" for k in group)
    assert len(report["real_ou_paired_by_ah_line_price_ou_line_price_buckets"])==3
    assert report["real_ou_independent_grouping"].endswith("NO_AH_CONDITION")


def test_global_over_grouping_has_separate_actual_lines_and_over_price_ranges():
    cases=[("a",2.5,1.93, (2,1)),("b",2.5,1.98,(1,1)),
           ("c",2.75,1.92,(2,1)),("d",2.5,2.04,(2,1))]
    rows=[]
    for fid,line,op,score in cases:
        snap=snapshot(fid=fid,line=line,op=op,up=1.98)
        snap.update(market_side="AWAY_FAVORITE",ah_line=-1,
                    ah_price_bucket=">2.20",
                    ft_home_goals=score[0],ft_away_goals=score[1])
        rows.append({**snap,**real_ou_outcome(snap,*score)})
    groups=aggregate_real_ou(rows)["real_ou_paired_by_line_over_price_bucket"]
    lookup={(g["ou_line"],g["over_price_bucket"]):g for g in groups}
    assert lookup[("2.5","1.90-1.99")]["n"]==2
    assert lookup[("2.5","1.90-1.99")]["over_win_pct"]==50
    assert lookup[("2.75","1.90-1.99")]["n"]==1
    assert lookup[("2.5","2.00-2.09")]["n"]==1
