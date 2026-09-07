from odds_scanner.three_way_audit import build_three_way_audit


def _row(season: str, division: str, hg: int = 2, ag: int = 0) -> dict:
    return {
        "season": season,
        "division": division,
        "favorite_side": "H",
        "favorite_fair_probability": 0.62,
        "favorite_ah_line": -0.5,
        "favorite_ah_price": 1.95,
        "ou_line": 2.5,
        "over_price": 1.95,
        "under_price": 1.95,
        "home_goals": hg,
        "away_goals": ag,
    }


def test_three_way_audit_uses_frozen_split_and_cross_league_gate():
    rows = []
    for league in ("E0", "D1", "I1"):
        for season in ("1920", "2021", "2122"):
            rows.extend(_row(season, league) for _ in range(20))
        for season in ("2223", "2324"):
            rows.extend(_row(season, league) for _ in range(20))
        rows.extend(_row("2425", league) for _ in range(20))

    audit = build_three_way_audit(
        rows,
        min_train_n=60,
        min_validation_n=40,
        min_holdout_n=30,
        fdr_alpha=0.10,
    )
    assert audit["split"]["holdout"] == ["2425"]
    assert audit["tested_patterns"] > 0
    ah = next(p for p in audit["patterns"] if p["family"] == "AH_LINE" and p["market"] == "AH")
    assert ah["train_roi"] > 0
    assert ah["validation_roi"] > 0
    assert ah["holdout_roi"] > 0
    assert ah["cross_league_holdout"]["eligible_leagues"] == 3
    assert ah["cross_league_holdout"]["stable"] is True


def test_three_way_audit_rejects_pattern_that_flips_on_holdout():
    rows = []
    for season in ("1920", "2021", "2122"):
        rows.extend(_row(season, "E0", 2, 0) for _ in range(30))
    for season in ("2223", "2324"):
        rows.extend(_row(season, "E0", 2, 0) for _ in range(30))
    rows.extend(_row("2425", "E0", 0, 2) for _ in range(50))

    audit = build_three_way_audit(
        rows,
        min_train_n=60,
        min_validation_n=40,
        min_holdout_n=30,
    )
    ah = next(p for p in audit["patterns"] if p["family"] == "AH_LINE" and p["market"] == "AH")
    assert ah["holdout_roi"] < 0
    assert ah["status"] == "REJECT"
