from odds_scanner.hierarchical_backtest import build_hierarchical_report
from odds_scanner.joint_audit import build_joint_audit


def _row(season: str, hg: int, ag: int, ah_line=-0.5, ah_price=1.95, over=1.95, under=1.95):
    return {
        "season": season,
        "favorite_side": "H",
        "favorite_fair_probability": 0.60,
        "favorite_ah_line": ah_line,
        "favorite_ah_price": ah_price,
        "ou_line": 2.5,
        "over_price": over,
        "under_price": under,
        "home_goals": hg,
        "away_goals": ag,
    }


def test_hierarchical_backtest_creates_coarse_and_deep_families():
    rows=[]
    for season in ("2021","2122","2223","2324","2425","2526"):
        rows.extend([_row(season, 2, 1) for _ in range(12)])
        rows.extend([_row(season, 1, 0) for _ in range(12)])
    rep=build_hierarchical_report(rows,test_seasons={"2324","2425","2526"},min_n=10)
    families={b["family"] for b in rep["buckets"]}
    assert "AH_LINE" in families
    assert "AH_OU" in families
    assert "AH_OU_PRICE" in families
    assert "AH_OU_PRICE_1X2" in families


def test_joint_audit_pairs_train_and_test_without_forcing_robust_status():
    rows=[]
    for season in ("2021","2122","2223","2324","2425","2526"):
        rows.extend([_row(season, 2, 1) for _ in range(25)])
    rep=build_hierarchical_report(rows,test_seasons={"2324","2425","2526"},min_n=10)
    audit=build_joint_audit(rep,min_train_n=30,min_test_n=30,fdr_alpha=0.10)
    assert audit["paired_tests"] > 0
    assert all("q_bh" in p for p in audit["patterns"])
    assert all(p["status"] in {"REJECT","WATCHLIST","ROBUST_RESEARCH_CANDIDATE"} for p in audit["patterns"])
