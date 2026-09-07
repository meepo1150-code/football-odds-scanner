import odds_scanner.football_data as fd


def test_mirror_fallback_joins_results_and_maps_odds(tmp_path, monkeypatch):
    odds_header = "match_id,season,date,home_team,away_team,bet365_1x2_home,bet365_1x2_draw,bet365_1x2_away,bet365_1x2_home_close,bet365_1x2_draw_close,bet365_1x2_away_close\n"
    result_header = "match_id,season,season_code,date,home_team,away_team,fthg,ftag,ftr\n"
    odds_rows = []
    result_rows = []
    for i in range(300):
        mid = f"2324-home{i}-away{i}"
        odds_rows.append(f"{mid},2023-24,2023-08-11,Home{i},Away{i},8.0,5.0,1.33,9.0,5.5,1.30\n")
        result_rows.append(f"{mid},2023-24,2324,2023-08-11,Home{i},Away{i},0,1,A\n")
    payloads = {
        fd.MIRROR_ODDS_URL: (odds_header + ''.join(odds_rows)).encode(),
        fd.MIRROR_RESULTS_URL: (result_header + ''.join(result_rows)).encode(),
    }
    monkeypatch.setattr(fd, "fetch_bytes", lambda url, *a, **k: payloads[url])
    paths = fd._download_history_mirror(tmp_path, ["2324"], "E0")
    rows = fd.decode_csv(paths[0].read_bytes())
    assert len(rows) == 300
    assert rows[0]["FTR"] == "A"
    assert rows[0]["B365H"] == "8.0"
    assert rows[0]["B365CH"] == "9.0"
    assert (tmp_path / "provenance.json").exists()


def test_canonical_season_code_variants():
    assert fd._canonical_season_code({"season_code": "", "season": "2016-17"}) == "1617"
    assert fd._canonical_season_code({"season_code": "1617.0", "season": "2016-17"}) == "1617"
    assert fd._canonical_season_code({"match_id": "1617-arsenal-chelsea"}) == "1617"
