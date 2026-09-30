"""Run actual browser JavaScript pure functions with Node (no DOM simulation)."""
import json
import shutil
import subprocess
from pathlib import Path
import pytest


def test_dashboard_data_guards():
    node=shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    html=Path('apps/dashboard/index.html').read_text()
    script=html.split('<script>',1)[1].split('</script>',1)[0]
    script=script.rsplit('load();',1)[0]
    checks='''
const assert=require('assert');
assert.equal(n(null),'—');
assert.equal(exactResults([{fixture_id:'blocked',ft_home_goals:2,ft_away_goals:1}],[{fixture_id:'blocked'}]).size,0);
assert.equal(ahSettlement(1,0,-1.5,'H'),'FULL_LOSS');
assert.equal(ahSettlement(1,0,null,'H'),null);
assert.equal(ahSettlement(1,0,-.6,'H'),null);
assert.equal(exactResults([{fixture_id:'a',ft_home_goals:1,ft_away_goals:0},{fixture_id:'a',ft_home_goals:0,ft_away_goals:0}]).size,0);
assert.equal(exactResults([{fixture_id:'a',ft_home_goals:null,ft_away_goals:0}]).size,0);
assert.equal(exactResults([{fixture_id:'a',ft_home_goals:1,ft_away_goals:0}]).size,1);
assert.equal(trustedSnapshot({provider:'propline',mainline_verified:true,source_semantics:'PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE',ah:{selected_side_price:1.9}}),false);
assert.equal(sortedRows([{favorite_price_win_pct:null},{favorite_price_win_pct:40}],'ah')[0].favorite_price_win_pct,40);
'''
    result=subprocess.run([node,'-e',script+checks],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
