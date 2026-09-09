from odds_scanner.oddspapi_v5_score_probe import inspect_fixture_payload


def test_inspect_fixture_payload_counts_explicit_ft_scores_and_provider_keys():
    payload = [
        {
            "fixtureId": "f1",
            "statusId": 2,
            "tournamentId": 17,
            "participant1Name": "Home",
            "participant2Name": "Away",
            "scores": {"result": {"participant1Score": 2, "participant2Score": 1}, "period1": {"participant1Score": 1, "participant2Score": 0}},
            "externalProviders": {"betradarId": 123, "flashscoreId": "abc"},
        },
        {
            "fixtureId": "f2",
            "statusId": 1,
            "tournamentId": 17,
            "scores": {"result": {"participant1Score": 0, "participant2Score": 0}},
        },
        {
            "fixtureId": "other",
            "statusId": 2,
            "tournamentId": 999,
            "scores": {"result": {"participant1Score": 3, "participant2Score": 0}},
        },
    ]
    report = inspect_fixture_payload(payload)
    assert report["fixture_rows"] == 3
    assert report["finished_big5_rows"] == 1
    assert report["explicit_ft_result_rows"] == 1
    assert report["score_top_level_key_counts"] == {"period1": 1, "result": 1}
    assert report["external_provider_key_counts"] == {"betradarId": 1, "flashscoreId": 1}
    assert report["samples"][0]["normalized_result"]["ft_home_goals"] == 2
