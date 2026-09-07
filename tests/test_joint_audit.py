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


def test_hierarchical_backtest_creates_coarse_and_deep_families_without_double_counting_ah():
    rows=[]
    for season in ("2021","2122","2223","2324","2425","2526"):
        rows.extend([_row(season, 2, 1) for _ in range(12)])
        rows.extend([_row(season, 1, 0) for _ in range(12)])
    rep=build_hierarchical_report(rows,test_seasons={"2324","2425","2526"},min_n=10)
    families={b["family"] for b in rep["buckets"]}
    assert {"AH_LINE","AH_OU","AH_OU_PRICE","AH_OU_PRICE_1X2"}.issubset(families)
    train_ah=next(b for b in rep["buckets"] if b["family"]=="AH_LINE" and b["split"]=="train")
    test_ah=next(b for b in rep["buckets"] if b["family"]=="AH_LINE" and b["split"]=="test")
    assert train_ah["n"] == 72
    assert test_ah["n"] == 72
    assert train_ah["ou_roi"] is None


def test_joint_audit_pairs_train_and_test_without_forcing_robust_status():
    rows=[]
    for season in ("2021","2122","2223","2324","2425","2526"):
        rows.extend([_row(season, 2, 1) for _ in range(25)])
    rep=build_hierarchical_report(rows,test_seasons={"2324","2425","2526"},min_n=10)
    audit=build_joint_audit(rep,min_train_n=30,min_test_n=30,fdr_alpha=0.10)
    assert audit["paired_tests"] > 0
    assert all("q_bh" in p for p in audit["patterns"])
    assert all(p["status"] in {"REJECT","WATCHLIST","ROBUST_RESEARCH_CANDIDATE"} for p in audit["patterns"])
    assert all(not (p["family"]=="AH_LINE" and p["market"]=="OU") for p in audit["patterns"])
