"""Scan Timeline uses actual same-snapshot O/U quotes and separate priced WR.

AH keeps its original two summary bars; actual quote WR lives in the separate O/U timeline.
"""
from pathlib import Path
import shutil
import subprocess
import pytest

HTML = Path(__file__).resolve().parents[1] / "apps/dashboard/index.html"


def _script():
    text = HTML.read_text(encoding="utf-8")
    assert "function realOuQuote(" in text
    assert "function realOuBox(" in text
    assert "function signalStats(" in text
    assert "stats.real_ou_paired_by_line_over_price_bucket" in text
    assert "lineKey(r.ah_line)===ln" in text
    assert "r.ah_price_bucket" in text
    assert "r.over_price_bucket" in text
    assert "r.under_price_bucket" not in text
    assert "lineKey(r.ou_line)===lineKey(q.line)" in text
    assert "function miniOuTimeline(" in text
    assert "function ouScanTimeline(" in text
    assert "market-section market-ah" in text and "market-section market-ou" in text
    assert "ราคา Over จริง" in text
    assert "function ou25GoalBar(" in text
    assert "function realOuBox(" in text
    assert "stats.over_under_2_5_by_ah_line_price" in text
    assert "stats.real_ou_paired_by_line_over_price_bucket" in text
    return text.split("<script>", 1)[1].split("</script>", 1)[0].rsplit("load();", 1)[0]


def test_ou_real_line_is_referenced_for_timeline_and_historical():
    _script()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_ou_real_per_scan_quote_requires_prematch_and_no_carry_forward():
    script = _script()
    checks = """
const assert=require('assert');
const snap={provider:'oddspapi',fixture_id:'x',bookmaker:'pinnacle',favorite_side:'H',
  source_semantics:'CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED',
  observed_at:'2026-10-13T08:00:00Z',kickoff:'2026-10-13T12:00:00Z',
  ah:{selected_side_line:-.75,selected_side_price:1.95},
  ou:{line:2.75,over_price:1.85,under_price:1.95}};
assert.equal(realOuQuote(snap).line,2.75);
assert.equal(realOuQuote({...snap,ou:{}}),null);
assert.equal(realOuQuote({...snap,ou:null}),null);
assert.equal(realOuQuote({...snap,observed_at:snap.kickoff}),null);
assert.equal(realOuQuote({...snap,ou:{...snap.ou,line:2.6}}),null);
assert(realOuBox({...snap,ou:null},null,null).includes('ไม่มีข้อมูล O/U รอบนี้'));
scopeReceipt={excluded_fixture_reasons:{},untrusted_observations:[]};
const stats={
 market_state_by_side_line_price:[],
 over_under_2_5_by_ah_line_price:[{market_side:'HOME_FAVORITE',ah_line:'-0.75',ah_price_bucket:'1.90-1.99',n:35,over_2_5_n:21,under_2_5_n:14}],
 real_ou_paired_by_line_over_price_bucket:[
 {ou_line:'2.75',over_price_bucket:'1.80-1.89',n:35,over_win_n:20,under_win_n:12,push_n:3,over_win_pct:57.14,under_win_pct:34.29}
 ]};
const grouped=signalStats(snap,stats);
assert.equal(grouped.ouOver.price_win_pct,57.14);
assert.equal(grouped.ouUnder.price_win_pct,34.29);
assert.equal(grouped.goalFreq.over_2_5_n,21);
assert.equal(grouped.ouPair.push_n,3);
assert.equal(grouped.ouPair.n,35);
// Same O/U line and Over odds must yield the SAME N even when AH changes.
const unrelatedAH={...snap,favorite_side:'A',ah:{selected_side_line:-1.75,selected_side_price:2.65}};
const independent=signalStats(unrelatedAH,stats);
assert.equal(independent.ah,null);
assert.equal(independent.goalFreq,null);
assert.equal(independent.ouPair.n,35);
assert.equal(independent.ouOver.price_win_pct,57.14);
assert.equal(signalStats({...snap,ou:null},stats).ouOver,null);
"""
    out = subprocess.run(["node", "-e", script + checks], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
