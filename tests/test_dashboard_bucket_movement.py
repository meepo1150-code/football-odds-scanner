"""Regression tests for dashboard AH price-bucket and line movement statistics."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_bucket_movements_and_verified_transition_wr():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable")
    html = Path("apps/dashboard/index.html").read_text()
    script = html.split("<script>", 1)[1].split("</script>", 1)[0].rsplit("load();", 1)[0]
    checks = r"""
const assert = require('assert');
scopeReceipt={excluded_fixture_reasons:{},untrusted_observations:[]};
const make=(price,line,time,fixture='fx',provider='pinnwire')=>({
  fixture_id:fixture,source_fixture_id:fixture,provider,bookmaker:'pinnacle',
  source_semantics:'VERIFIED_MAINLINE',favorite_side:'H',
  observed_at:'2026-10-20T'+time+':00Z',kickoff:'2026-10-21T00:00:00Z',
  ah:{selected_side_price:price,selected_side_line:line}
});
const a=make(1.909,-.5,'08:00'),b=make(1.917,-.5,'11:00');
const c=make(1.925,-.5,'14:00'),d=make(1.877,-.5,'17:00');
assert.deepEqual(transitionKinds(a,b),[]);
assert.deepEqual(transitionKinds(b,c),[]);
assert.deepEqual(transitionKinds(c,d),['PRICE_CHANGE']);
assert.equal(movement(a,b),'');
assert.deepEqual(transitionKinds(c,make(1.925,-.75,'17:00')),['LINE_CHANGE']);
assert.deepEqual(transitionKinds(c,make(1.877,-.75,'17:00')),['PRICE_CHANGE','LINE_CHANGE']);
assert.deepEqual(transitionKinds(c,make(1.877,-.5,'17:00','fx','other')),[]);
assert.equal(miniTimeline([a,b,c,d]).match(/bucket-changed/g).length,1);
const rows=[a,b,c,d,make(1.93,-.5,'18:00'),make(1.88,-.5,'19:00')];
transitionStats=buildTransitionStats(rows,new Map([['fx',{ft_home_goals:2,ft_away_goals:0}]]));
const stat=transitionStats.get(transitionKey('PRICE_CHANGE',c,d));
assert.equal(stat.n,1); // repeat of same transition on one fixture is not a second match
assert.equal(stat.wins,1);
assert(movementStatBox(c,d).includes('WR 100.0%'));
assert(movementStatBox(c,d).includes('N=1'));
assert.equal(movementStatBox(a,b),'');
const pushFixture=[make(1.925,-1,'08:00','push'),make(1.877,-1,'11:00','push')];
const pushing=buildTransitionStats(pushFixture,new Map([['push',{ft_home_goals:1,ft_away_goals:0}]]));
const push=pushing.get(transitionKey('PRICE_CHANGE',pushFixture[0],pushFixture[1]));
assert.equal(push.n,1);assert.equal(push.wins,0);assert.equal(push.push,1);

"""
    result = subprocess.run([node, "-e", script + checks], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "สถิติย้อนหลังเท่านั้น ·" not in html
