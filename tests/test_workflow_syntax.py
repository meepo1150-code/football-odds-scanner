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
