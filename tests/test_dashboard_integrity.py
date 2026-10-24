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
const rawFT=[{fixture_id:'alias',ft_home_goals:0,ft_away_goals:0},{fixture_id:'clean',ft_home_goals:1,ft_away_goals:0}];
const safe=identitySafeResults(rawFT,[],new Map([['alias','canonical']]),['canonical']);
assert.equal(safe.size,1);assert(safe.has('clean'));
assert.equal(priceResultFromFT(safe.get('canonical'),{favorite_side:'H',ah:{selected_side_line:-.5}}),'');
assert.equal(identitySafeResults(rawFT,[],new Map,null).size,0);
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


def test_ou_table_uses_actual_ou_quote_prices_and_split_settlement():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=Path('apps/dashboard/index.html').read_text().split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks='''
const assert=require('assert');
const rendered=ouTable([{market_side:'HOME_FAVORITE',ah_line:-.75,ah_price_bucket:'1.90-1.99',ou_line:'2.75',selection:'OVER',ou_price_bucket:'1.80-1.89',n:10,price_win_pct:60,push_pct:10,roi_pct:12.5,full_win:4,half_win:2,push:1,half_loss:1,full_loss:2,mainline_verified_n:9,avg_total_goals:3.15,sample_label:'TINY'}]);
assert(!rendered.includes('undefined'));
assert(rendered.includes('FW / HW / P / HL / FL'));
assert(rendered.includes('2.75')&&rendered.includes('OVER')&&rendered.includes('60.0%')&&rendered.includes('12.5%'));
assert(rendered.includes('4/2/1/1/2')&&rendered.includes('9/10'));
assert(!rendered.includes('Over 2.5'));
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


def test_mobile_round_labels_and_three_distinct_wr_bars():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=Path('apps/dashboard/index.html').read_text().split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks='''
const assert=require('assert');
assert.equal(scanLabel({scheduled_target_at:'2026-10-13T08:00:00Z'},0),'Scan 15:00');
assert.equal(scanLabel({scheduled_target_at:'2026-10-13T11:00:00Z'},1),'Scan 18:00');
assert.equal(scanLabel({scheduled_target_at:null},2),'r3');
const s={provider:'oddspapi',bookmaker:'pinnacle',source_semantics:'CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED',observed_at:'2026-10-13T08:00:00Z',kickoff:'2026-10-13T12:00:00Z',ou:{line:2.75,over_price:1.85,under_price:1.95},ah:{selected_side_line:-.75,selected_side_price:1.95},favorite_side:'H'};
assert.deepEqual(realOuQuote(s),{line:2.75,over:1.85,under:1.95,mainline:true});
const sample={n:8,over_2_5_n:2,under_2_5_n:6,goals_n:8,avg_total_goals:2.75};
const freq=ou25GoalBar(sample);
assert(freq.includes('Over 2.5')&&freq.includes('Under 2.5'));
assert(freq.includes('25.0%')&&freq.includes('75.0%')&&freq.includes('N=8'));
assert(freq.includes('width:25%')&&freq.includes('width:75%'));
const paired={n:8,over_win_n:2,under_win_n:4,push_n:2,over_full_win:1,over_half_win:1,under_full_win:4,under_half_win:0,over_roi_pct:-12.5,under_roi_pct:23,mainline_verified_n:8};
const split=realOuBox(s,paired);
assert(split.includes('Over 2.75')&&split.includes('Under 2.75'));
assert(split.includes('25.0%')&&split.includes('50.0%')&&split.includes('Push 2'));
assert(split.includes('width:25%')&&split.includes('width:50%'));
assert(split.includes('1.850')&&split.includes('1.950')&&split.includes('N=8'));
assert(!split.includes('NaN'));
assert(realOuBox({...s,ou:null},null).includes('ไม่มีข้อมูล O/U รอบนี้'));
scopeReceipt={excluded_fixture_reasons:{},untrusted_observations:[]};
const stats={market_state_by_side_line_price:[],over_under_2_5_by_ah_line_price:[{market_side:'HOME_FAVORITE',ah_line:'-0.75',ah_price_bucket:'1.90-1.99',...sample}],real_ou_paired_by_ah_line_price_ou_line_price_buckets:[{market_side:'HOME_FAVORITE',ah_line:'-0.75',ah_price_bucket:'1.90-1.99',ou_line:'2.75',over_price_bucket:'1.80-1.89',under_price_bucket:'1.90-1.99',...paired}]};
const metrics=wrBox(s,stats);
assert(metrics.includes('AH · Win Rate'));
assert(metrics.includes('Over 2.5')&&metrics.includes('Under 2.5'));
assert(!metrics.includes('Over 2.75')&&!metrics.includes('Under 2.75')); // Price market belongs to a separate timeline
const splitTimeline=ouScanTimeline([s,{...s,ou:null,observed_at:'2026-10-13T09:00:00Z'}],stats);
assert(splitTimeline.includes('Over 2.75')&&splitTimeline.includes('1.850'));
assert(splitTimeline.includes('Under 2.75')&&splitTimeline.includes('1.950'));
assert(splitTimeline.includes('ไม่มีข้อมูล O/U รอบนี้')&&splitTimeline.includes('N=8'));
assert(splitTimeline.includes('Scan ')&&splitTimeline.includes('market-section market-ou'));
assert(!metrics.includes('market-section market-ou'));
assert(ouTransitionKinds(s,{...s,observed_at:'2026-10-13T09:00:00Z',ou:{line:3.0,over_price:1.93,under_price:1.87}}).includes('LINE_CHANGE'));
assert.deepEqual(ouTransitionKinds(s,{...s,observed_at:'2026-10-13T09:00:00Z',bookmaker:'other'}),[]);
const ouMini=miniOuTimeline([s,{...s,observed_at:'2026-10-13T09:00:00Z',ou:null}]);
assert(ouMini.includes('ไม่มีราคา O/U'));
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
    assert 'class="round-ah-n ${ahSampleTier(signalStats(s,st).ah?.settled_n)}"' in html
    assert 'N=${Number(signalStats(s,st).ah?.settled_n)>0' in html
    assert '.round-price-top{display:flex' in html


def test_ah_sample_n_badge_color_tiers():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    html=Path('apps/dashboard/index.html').read_text()
    assert 'ahSampleTier(signalStats(s,st).ah?.settled_n)' in html
    assert all(f'.round-price-top .round-ah-n.{tier}' in html for tier in ('n-tiny', 'n-early', 'n-developing', 'n-moderate', 'n-large'))
    script=html.split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks='''
const assert=require('assert');
for(const [n,tier] of [[null,'n-unknown'],[0,'n-unknown'],[8,'n-tiny'],[19,'n-tiny'],[20,'n-early'],[39,'n-early'],[40,'n-developing'],[59,'n-developing'],[60,'n-moderate'],[99,'n-moderate'],[100,'n-large']])assert.equal(ahSampleTier(n),tier);
'''
    result=subprocess.run([node,'-e',script+checks],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_favorite_ah_betting_win_label_is_clear():
    html=Path('apps/dashboard/index.html').read_text()
    assert "metricBar('เดิมพันฝั่งต่อชนะ'" in html
    assert "signalBadge('เดิมพันฝั่งต่อชนะ'" in html
    assert "signalBadge('เดิมพันฝั่งต่อชนะต่ำ'" in html
    assert "'AH WR ต่อ'" not in html


def test_ah_favorite_bar_uses_red_and_white_segments():
    html=Path('apps/dashboard/index.html').read_text()
    assert 'metric-track ah-split-track' in html
    assert 'ah-segment favorite' in html
    assert 'ah-segment underdog' in html
    assert 'width:${p}%' in html
    assert 'width:${100-p}%' in html
    assert '.ah-segment.favorite{background:#ef5264}' in html
    assert '.ah-segment.underdog{background:#f4f7fc}' in html
    assert 'ส่วนที่ไม่ใช่ชัยชนะฝั่งต่อ' in html


def test_market_signal_badges_match_bar_colors():
    html=Path('apps/dashboard/index.html').read_text()
    assert "signal-favorite" in html and "signal-underdog" in html
    assert ".signal-ah.signal-high.signal-favorite{background:rgba(239,82,100,.18)!important;border-color:#ef5264" in html
    assert ".signal-ah.signal-low.signal-underdog{background:rgba(244,247,252,.13)!important;border-color:#f4f7fc" in html
    assert ".signal-ou.signal-high:not(.signal-under){background:rgba(255,180,94,.17)!important;border-color:#ffb45e" in html
    assert ".signal-ou.signal-under{background:rgba(104,174,250,.17)!important;border-color:#68aefa" in html


def test_fixture_title_centered_and_competition_country_grounded():
    html=Path('apps/dashboard/index.html').read_text()
    assert 'class="teams fixture-title"' in html
    assert '.fixture .fixture-title{text-align:center;width:100%' in html
    assert 'competitionCountry(named.league||first.league,named)' in html
    assert '"tff 1 lig":"Turkey"' in html
    assert '"meistriliiga":"Estonia"' in html
    assert '"uefa champions league":"Europe"' in html
    assert "return VERIFIED_COMPETITION_COUNTRIES[String(league||'').trim().toLowerCase()]||''" in html


def test_dashboard_due_ft_uses_active_matured_manifest_not_future_or_quarantine():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    html=Path('apps/dashboard/index.html').read_text()
    assert 'FT ถึงกำหนด ≥3 ชม.' in html
    assert 'FT ทุกคู่' in html
    script=html.split('<script>',1)[1].split('</script>',1)[0].rsplit('load();',1)[0]
    checks = """
const assert=require('assert');
const at=Date.parse('2026-10-16T17:00:00Z');
const rows=[
 {fixture_id:'old',status:'MISSING_FT',kickoff:'2026-10-16T12:00:00Z'},
 {fixture_id:'recent',status:'MISSING_FT',kickoff:'2026-10-16T16:00:00Z'},
 {fixture_id:'blocked',status:'IDENTITY_CONFLICT',kickoff:'2026-10-16T12:00:00Z'},
 {fixture_id:'postponed',status:'POSTPONED',kickoff:'2026-10-16T12:00:00Z'},
 {fixture_id:'retired',status:'RETIRED_UNRESOLVED',kickoff:'2026-10-16T12:00:00Z'},
 {fixture_id:'archive',status:'MISSING_FT',retired_from_active_queue:true,kickoff:'2026-10-16T12:00:00Z'},
 {fixture_id:'unknown',status:'MISSING_FT',kickoff:'2026-10-16'}
];
const s={settled_fixtures:90,raw_unresolved_ft_fixtures:7};
const ledger={missing_ft_count:7,fixtures:rows};
const due=ftDueSummary(s,ledger,at);
assert.deepEqual(due,{overdue:1,recent:1,unknown:1,denominator:91,rate:9000/91});
assert.equal(ftDueSummary(s,{...ledger,missing_ft_count:5},at),null);
assert.equal(ftDueSummary(s,null,at),null);
"""
    r=subprocess.run([node,'-e',script+checks],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
