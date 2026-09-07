from pathlib import Path
import odds_scanner.football_data as fd


def test_mirror_fallback_maps_processed_schema(tmp_path, monkeypatch):
    csv = (
        "season_code,season,date,home_team,away_team,ftr,bet365_1x2_home,bet365_1x2_draw,bet365_1x2_away,bet365_1x2_home_close,bet365_1x2_draw_close,bet365_1x2_away_close\n"
        + "2324.0,2023-24,2023-08-11,Burnley,Man City,A,8.0,5.0,1.33,9.0,5.5,1.30\n" * 300
    ).encode()
    monkeypatch.setattr(fd, "fetch_bytes", lambda *a, **k: csv)
    paths = fd._download_history_mirror(tmp_path, ["2324"], "E0")
    rows = fd.decode_csv(paths[0].read_bytes())
    assert len(rows) == 300
    assert rows[0]["B365H"] == "8.0"
    assert rows[0]["B365CH"] == "9.0"
    assert (tmp_path / "provenance.json").exists()


def test_canonical_season_code_from_label():
    assert fd._canonical_season_code({"season_code": "", "season": "2016-17"}) == "1617"
    assert fd._canonical_season_code({"season_code": "1617.0", "season": "2016-17"}) == "1617"
