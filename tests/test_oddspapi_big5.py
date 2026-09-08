from odds_scanner.oddspapi_big5 import select_big5_tournaments


def test_select_big5_tournaments_is_country_and_name_exact():
    rows = [
        {"tournamentId": 1, "categoryName": "England", "tournamentName": "Premier League", "tournamentSlug": "premier-league"},
        {"tournamentId": 2, "categoryName": "England", "tournamentName": "Championship", "tournamentSlug": "championship"},
        {"tournamentId": 3, "categoryName": "Germany", "tournamentName": "Bundesliga", "tournamentSlug": "bundesliga"},
        {"tournamentId": 4, "categoryName": "Italy", "tournamentName": "Serie A", "tournamentSlug": "serie-a"},
        {"tournamentId": 5, "categoryName": "Spain", "tournamentName": "LaLiga", "tournamentSlug": "laliga"},
        {"tournamentId": 6, "categoryName": "France", "tournamentName": "Ligue 1", "tournamentSlug": "ligue-1"},
        {"tournamentId": 7, "categoryName": "Brazil", "tournamentName": "Serie A", "tournamentSlug": "serie-a"},
    ]
    selected = select_big5_tournaments(rows)
    assert {x["tournamentId"] for x in selected} == {1, 3, 4, 5, 6}
    assert len(selected) == 5


def test_select_big5_tournaments_does_not_guess_missing_top_division():
    rows = [{"tournamentId": 2, "categoryName": "England", "tournamentName": "Championship", "tournamentSlug": "championship"}]
    assert select_big5_tournaments(rows) == []
