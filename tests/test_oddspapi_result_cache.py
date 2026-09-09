import json
from odds_scanner.oddspapi_result_cache import merge_results


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
