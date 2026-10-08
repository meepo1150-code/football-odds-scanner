from pathlib import Path
import yaml


def test_all_workflow_yaml_parses_and_cron_has_five_fields():
    for path in Path('.github/workflows').glob('*.yml'):
        data=yaml.safe_load(path.read_text())
        assert isinstance(data,dict),path
        trigger=data.get('on',data.get(True,{}))
        if isinstance(trigger,dict):
            for row in trigger.get('schedule',[]):
                assert len(row['cron'].split())==5,path


def test_recovered_results_trigger_dashboard_and_refresh_queue_after_merge():
    pages = yaml.safe_load(Path('.github/workflows/pages.yml').read_text())
    guard = yaml.safe_load(Path('.github/workflows/api-football-shadow.yml').read_text())
    trigger = pages.get('on', pages.get(True, {}))
    assert guard['name'] in trigger['workflow_run']['workflows']
    assert 'completed' in trigger['workflow_run']['types']
    steps = guard['jobs']['shadow']['steps']
    persist = next(step['run'] for step in steps
                   if step.get('name') == 'Persist result data and rebuilt statistics')
    assert persist.index('odds_scanner.result_artifact_merge') < persist.index('odds_scanner.pinnwire_result_join')
    assert persist.index('odds_scanner.pinnwire_result_join') < persist.index('odds_scanner.web_result_recovery')
    assert persist.index('odds_scanner.web_result_recovery') < persist.index('git add')
