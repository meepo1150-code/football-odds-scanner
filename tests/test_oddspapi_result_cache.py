import json
from odds_scanner.oddspapi_result_cache import merge_normalized_results, merge_results


def test_merge_results_caches_only_explicit_finished_scores(tmp_path):
    path=tmp_path/"results.jsonl"
    fixtures=[
        {"fixtureId":"1","statusId":2,"participant1Score":2,"participant2Score":1},
        {"fixtureId":"2","statusId":2},
        {"fixtureId":"3","statusId":0,"participant1Score":1,"participant2Score":0},
    ]
    assert merge_results(path,fixtures)==1
    rows=[json.loads(x) for x in path.read_text().splitlines()]
    assert len(rows)==1 and rows[0]["fixture_id"]=="1"
    assert merge_results(path,fixtures)==0


def test_merge_normalized_results_accepts_only_explicit_integer_ft_scores(tmp_path):
    path=tmp_path/"results.jsonl"
    results=[
        {"fixture_id":"1","ft_home_goals":2,"ft_away_goals":1,"result_source":"exact"},
        {"fixture_id":"2","ft_home_goals":-1,"ft_away_goals":1,"result_source":"bad"},
        {"fixture_id":"3","ft_home_goals":2.0,"ft_away_goals":1,"result_source":"bad_type"},
    ]
    assert merge_normalized_results(path,results)==1
    rows=[json.loads(x) for x in path.read_text().splitlines()]
    assert rows==[{"fixture_id":"1","ft_home_goals":2,"ft_away_goals":1,"result_source":"exact"}]
