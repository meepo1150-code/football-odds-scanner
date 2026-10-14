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
const sourceRows=[{fixture_id:'a',home:'H',away:'A',kickoff:'K',league:'L',provider:'pinnwire'},{fixture_id:'b',home:'H',away:'A',kickoff:'K',league:'L2',provider:'propline'}];
const bridges=[{canonical_fixture_id:'a',members:sourceRows}];
const fm=fixtureIdentityMap(sourceRows,bridges);
assert.equal(fm.get('b'),'a');
assert.equal(fixtureIdentityMap([...sourceRows,{...sourceRows[1],home:'Different'}],bridges).size,0);
assert.equal(exactResults(projectFixtureRows([{fixture_id:'a',ft_home_goals:1,ft_away_goals:0},{fixture_id:'b',ft_home_goals:0,ft_away_goals:0}],fm)).size,0);
assert.equal(exactResults(projectFixtureRows([{fixture_id:'a',ft_home_goals:1,ft_away_goals:0}],fm),projectFixtureRows([{fixture_id:'b'}],fm)).size,0);

assert.equal(activeTimelineGroups([['old',[]],['new',[]]],['old'],new Map).length,1);
assert.equal(activeTimelineGroups([['old',[]]],['old'],new Map([['old',{}]])).length,1);
assert.equal(exactResults([{fixture_id:'x',ft_home_goals:1,ft_away_goals:0}],null).size,0);
assert.equal(exactResults([{fixture_id:'x',ft_home_goals:1,ft_away_goals:0}],[{}]).size,0);
assert.equal(exactResults([{fixture_id:'x',ft_home_goals:true,ft_away_goals:0}]).size,0);
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


def test_required_quarantine_fetch_does_not_become_empty_list():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    html=Path('apps/dashboard/index.html').read_text()
    script=html.split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks="""
const assert=require('assert');
(async()=>{
 global.fetch=async()=>({ok:false});
 assert.equal(await jl('ledger',true),null);
 global.fetch=async()=>({ok:true,text:async()=>'{bad json'});
 assert.equal(await jl('ledger',true),null);
 global.fetch=async()=>({ok:true,text:async()=>''});
 assert.deepEqual(await jl('ledger',true),[]);
})().catch(e=>{console.error(e);process.exit(1)});
"""
    result=subprocess.run([node,'-e',script+checks],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert "conflicts.jsonl',true)" in html
    assert "if(!validConflictLedger(resultConflicts))" in html


def test_result_status_boundaries_do_not_claim_live_or_finished():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    html=Path('apps/dashboard/index.html').read_text()
    script=html.split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks=r"""
const assert=require('assert');
const s={kickoff:'2026-10-01T12:00:00Z'},ko=Date.parse(s.kickoff);
assert.equal(fixtureResultState(s,null,ko-1).code,'SCHEDULED');
assert.equal(fixtureResultState(s,null,ko).code,'AWAITING_RESULT');
assert.equal(fixtureResultState(s,null,ko+10800000-1).code,'AWAITING_RESULT');
assert.equal(fixtureResultState(s,null,ko+10800000).code,'OVERDUE_RESULT');
assert.equal(fixtureResultState({kickoff:'2026-10-01T12:00:00'},null,ko).code,'UNKNOWN_KICKOFF');
assert.equal(fixtureResultState({kickoff:'bad'},null,ko).code,'UNKNOWN_KICKOFF');
assert.equal(fixtureResultState(s,{ft_home_goals:0,ft_away_goals:0},ko).label,'FT 0 - 0');
assert.equal(fixtureResultState(s,{ft_home_goals:0,ft_away_goals:0},ko,true).code,'CONFLICT');
assert.equal(priceResultFromFT(null,s),'');
assert.equal(observationLabel({provider:'pinnwire'},null),'ข้อมูลวิจัย · mainline ยังไม่ยืนยัน');
assert.equal(observationLabel({provider:'other'},null),'ยังไม่มีผลประเมินราคา');
"""
    r=subprocess.run([node,'-e',script+checks],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert 'fixtureResultState(' in html and 'OVERDUE_RESULT' in html and 'SCHEDULED' in html
    assert "'UNCLASSIFIED'" not in html


def test_shared_scope_receipt_matches_backend_real_offline_data(tmp_path):
    from odds_scanner.dashboard_scope import build
    from odds_scanner.research_v2_pattern_stats import _rows, SNAPSHOTS
    from odds_scanner.research_v2_integrity import trusted_snapshot
    from odds_scanner.research_population import in_scope
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    rows=_rows(SNAPSHOTS)
    target=tmp_path/SNAPSHOTS;target.parent.mkdir(parents=True);target.write_text(SNAPSHOTS.read_text())
    receipt=build(tmp_path)
    expected=sorted((str(r['fixture_id']),str(r['observed_at'])) for r in rows if trusted_snapshot(r) and in_scope(r))
    script=Path('apps/dashboard/index.html').read_text().split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks='scopeReceipt='+json.dumps(receipt)+';const rows='+json.dumps(rows)+';const got=rows.filter(r=>trustedSnapshot(r)&&inScope(r)).map(r=>[String(r.fixture_id),String(r.observed_at)]).sort();require("assert").deepEqual(got,'+json.dumps(expected)+');'
    check=tmp_path/'check.js';check.write_text(script+checks)
    result=subprocess.run([node,str(check)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_ou_table_uses_frequency_and_priced_returns_without_ah_columns():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=Path('apps/dashboard/index.html').read_text().split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks='''
const assert=require('assert');
const rendered=ouTable([{market_side:'HOME_FAVORITE',ah_line:-.75,ah_price_bucket:'1.90-1.99',n:10,over_2_5_n:6,under_2_5_n:4,over_2_5_pct:60,under_2_5_pct:40,ou25_priced_n:3,over_2_5_roi_pct:23.5,under_2_5_roi_pct:-30,sample_label:'VERY_LOW'}]);
assert(!rendered.includes('undefined'));
assert(!rendered.includes('FW / HW'));
assert(rendered.includes('O/U priced N')&&rendered.includes('6/10')&&rendered.includes('23.5%'));
const ah=statsTable([{settled_n:1,full_win:0,half_win:1,push:0,half_loss:0,full_loss:0}]);
assert(ah.includes('FW / HW / P / HL / FL')&&ah.includes('0/1/0/0/0'));
'''
    result=subprocess.run([node,'-e',script+checks],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_archive_quote_is_not_presented_as_current_scope_statistics():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=Path('apps/dashboard/index.html').read_text().split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks='''
const assert=require('assert');
scopeReceipt={excluded_fixture_reasons:{cancelled:'USER_REVIEWED_COMPETITION_OUT_OF_SCOPE'},untrusted_observations:[]};
const quote={fixture_id:'cancelled',provider:'pinnwire',favorite_side:'H',ah:{selected_side_line:-.75,selected_side_price:1.95}};
assert(wrBox(quote,{}).includes('out of scope'));
assert.equal(providerLabel({source_semantics:'CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED'}),'oddspapi');
'''
    result=subprocess.run([node,'-e',script+checks],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_mobile_round_labels_and_complementary_ou_split():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=Path('apps/dashboard/index.html').read_text().split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks='''
const assert=require('assert');
assert.equal(scanLabel({scheduled_target_at:'2026-10-13T08:00:00Z'},0),'Scan 15:00');
assert.equal(scanLabel({scheduled_target_at:'2026-10-13T11:00:00Z'},1),'Scan 18:00');
assert.equal(scanLabel({scheduled_target_at:null},2),'r3');
const split=ouSplitBar({n:8,over_2_5_pct:25,under_2_5_pct:75});
assert(split.includes('25.0%')&&split.includes('75.0%'));
assert(split.includes('width:25%')&&split.includes('width:75%'));
assert(split.includes('N=8')&&split.includes('ou-segment under'));
assert(!split.includes('NaN'));
assert(ouSplitBar({n:0}).includes('ไม่มีข้อมูล')||ouSplitBar({n:0}).includes('ยังไม่มี'));
const timeline=miniTimeline([{scheduled_target_at:'2026-10-13T08:00:00Z',observed_at:'2026-10-13T08:03:00Z',ah:{selected_side_line:-.25,selected_side_price:2.13}},{scheduled_target_at:'2026-10-13T11:00:00Z',observed_at:'2026-10-13T11:03:00Z',ah:{selected_side_line:-.25,selected_side_price:2.15}}]);
assert(timeline.includes('Scan 15:00')&&timeline.includes('Scan 18:00'));
'''
    result=subprocess.run([node,'-e',script+checks],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_round_header_price_specific_ah_sample_n():
    html=Path('apps/dashboard/index.html').read_text()
    assert 'class="round-price-top"' in html
    assert 'AH ${esc(s.ah?.selected_side_line)}' in html
    assert 'signalStats(s,st).ah?.settled_n' in html
    assert 'class="round-ah-n"' in html
    assert 'N=${Number(signalStats(s,st).ah?.settled_n)>0' in html
    assert '.round-price-top{display:flex' in html


def test_ah_sample_n_badge_color_tiers():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    html=Path('apps/dashboard/index.html').read_text()
    assert 'ahSampleTier(signalStats(s,st).ah?.settled_n)' in html
    assert '.round-ah-n.n-low' in html and '.round-ah-n.n-large' in html
    script=html.split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks='''
const assert=require('assert');
for(const [n,tier] of [[null,'n-unknown'],[0,'n-unknown'],[8,'n-low'],[14,'n-low'],[15,'n-limited'],[29,'n-limited'],[30,'n-good'],[59,'n-good'],[60,'n-large'],[100,'n-large']])assert.equal(ahSampleTier(n),tier);
'''
    result=subprocess.run([node,'-e',script+checks],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
