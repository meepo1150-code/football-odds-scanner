import json
from odds_scanner.result_artifact_merge import merge
from odds_scanner.oddspapi_result_cache import RESULTS_PATH


def save(root, rows):
    p=root/RESULTS_PATH;p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def result(fid, h=1, a=0):
    return dict(fixture_id=fid, ft_home_goals=h, ft_away_goals=a)


def test_stale_overnight_results_preserve_concurrent_results(tmp_path):
    main, stage=tmp_path/'main',tmp_path/'stage'
    save(main,[result('old'),result('concurrent')])
    save(stage,[result('old'),result('overnight')])
    merge(stage, main)
    assert {json.loads(l)['fixture_id'] for l in (main/RESULTS_PATH).read_text().splitlines()} == {'old','concurrent','overnight'}


def test_conflicting_concurrent_ft_is_quarantined_not_overwritten(tmp_path):
    main, stage=tmp_path/'main',tmp_path/'stage'
    save(main,[result('same',1,0)])
    save(stage,[result('same',2,0)])
    merge(stage, main)
    assert (main/RESULTS_PATH).read_text()==''
    conflicts=(main/RESULTS_PATH.with_suffix('.conflicts.jsonl')).read_text()
    assert 'CONFLICTING_EXACT_RESULT_SCORES' in conflicts
