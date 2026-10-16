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
    """Result recovery must remain active without requiring retired scanner jobs."""
    pages = yaml.safe_load(Path('.github/workflows/pages.yml').read_text())
    trigger = pages.get('on', pages.get(True, {}))
    assert 'workflow_run' in trigger
    assert 'completed' in trigger['workflow_run']['types']
    for name in ('research-v2-free-result-backfill.yml', 'research-v2-result-backfill.yml'):
        workflow = yaml.safe_load(Path('.github/workflows', name).read_text())
        assert workflow['jobs'], name
        assert any(
            'result' in str(step.get('run', '')).lower()
            for job in workflow['jobs'].values()
            for step in job.get('steps', [])
        ), name


def test_dashboard_publication_survives_frequent_report_updates():
    pages = yaml.safe_load(Path('.github/workflows/pages.yml').read_text())
    assert pages['concurrency'] == {'group': 'pages', 'cancel-in-progress': False}
    checkout = next(step for step in pages['jobs']['deploy']['steps']
                    if str(step.get('uses', '')).startswith('actions/checkout@'))
    assert checkout['with']['ref'] == 'main'
