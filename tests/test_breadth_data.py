from odds_scanner.breadth_data import normalize_big5_csv


def test_normalize_big5_csv_maps_away_favourite_handicap_perspective():
    csv_text = "\n".join([
        "Division,MatchDate,HomeTeam,AwayTeam,FTHome,FTAway,OddHome,OddDraw,OddAway,Over25,Under25,HandiSize,HandiHome,HandiAway",
        "E0,2024-09-01,Home,Away,0,2,4.00,3.50,1.90,1.95,1.90,0.50,1.90,1.95",
    ])
    rows = normalize_big5_csv(csv_text.encode())
    assert len(rows) == 1
    row = rows[0]
    assert row["season"] == "2425"
    assert row["favorite_side"] == "A"
    assert row["favorite_ah_line"] == -0.5
    assert row["favorite_ah_price"] == 1.95


def test_normalize_big5_csv_filters_non_big5_and_outside_window():
    csv_text = "\n".join([
        "Division,MatchDate,HomeTeam,AwayTeam,FTHome,FTAway,OddHome,OddDraw,OddAway,Over25,Under25,HandiSize,HandiHome,HandiAway",
        "N1,2024-09-01,A,B,1,0,1.90,3.50,4.00,1.95,1.90,-0.50,1.95,1.90",
        "E0,2018-09-01,C,D,1,0,1.90,3.50,4.00,1.95,1.90,-0.50,1.95,1.90",
    ])
    assert normalize_big5_csv(csv_text.encode()) == []


def test_normalize_big5_csv_rejects_non_quarter_handicap_line():
    csv_text = "\n".join([
        "Division,MatchDate,HomeTeam,AwayTeam,FTHome,FTAway,OddHome,OddDraw,OddAway,Over25,Under25,HandiSize,HandiHome,HandiAway",
        "E0,2024-09-01,A,B,3,0,1.30,5.00,10.00,1.70,2.10,-2.30,1.95,1.90",
    ])
    assert normalize_big5_csv(csv_text.encode()) == []
