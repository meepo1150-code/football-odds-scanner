from pathlib import Path

from odds_scanner import independent_league_confirmation as ind


def test_independent_universe_is_disjoint_from_big5():
    assert set(ind.INDEPENDENT_LEAGUES).isdisjoint({
        "Premier League", "Bundesliga", "Serie A", "LaLiga", "Ligue 1"
    })
    assert len(ind.INDEPENDENT_LEAGUES) == 5


def test_run_restores_base_leagues_and_never_promotes_production(tmp_path, monkeypatch):
    original = dict(ind.base.LEAGUES)

    def fake_load(_mirror_root):
        assert ind.base.LEAGUES == ind.INDEPENDENT_LEAGUES
        return [], {"mirror_commit": "frozen"}

    def fake_validate(rows):
        assert rows == []
        return ({
            "train_positive_patterns_entering_validation": 0,
            "promoted_patterns": 0,
        }, {
            "pattern_count": 0,
            "patterns": [],
        })

    monkeypatch.setattr(ind.base, "load_mirror", fake_load)
    monkeypatch.setattr(ind.base, "validate", fake_validate)
    result = ind.run(tmp_path, Path("mirror"))

    assert ind.base.LEAGUES == original
    assert result["promoted_candidates"] == 0
    report = (tmp_path / ind.REPORT_PATH).read_text(encoding="utf-8")
    assert '"production_promotion_allowed_by_this_run": false' in report
    assert (tmp_path / ind.CANDIDATE_REGISTRY_PATH).exists()
