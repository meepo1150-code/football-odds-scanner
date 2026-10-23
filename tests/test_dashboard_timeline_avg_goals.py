"""Scan Timeline displays the FT goal average for its exact AH/price state.

The dashboard already looks up both its O/U bar and the verified FT goal average
from the same canonical market_side x AH line x AH price bucket report row.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess

import pytest

HTML = Path(__file__).resolve().parents[1] / "apps/dashboard/index.html"


def _js_functions():
    page = HTML.read_text(encoding="utf-8")
    start = page.index("function ouAverageLabel(")
    end = page.index("function miniTimeline(", start)
    functions = page[start:end]
    assert "function ouSplitBar(" in functions
    assert "N=${count} · FT ที่ยืนยัน</div>${ouAverageLabel(ou,count)}" in functions
    assert ".ou-goal-avg{" in page
    # Regression: lookup remains the existing exact side/line/decimal-price bucket.
    sig = page[page.index("function signalStats("):page.index("function signalKinds(")]
    assert "stats.over_under_2_5_by_ah_line_price" in sig
    assert "r.market_side===ms" in sig
    assert "lineKey(r.ah_line)===ln" in sig
    assert "r.ah_price_bucket" in sig
    return functions


def test_goal_average_attached_below_scan_timeline_ou_bar():
    _js_functions()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_goal_average_renders_only_when_verified_ft_sample_matches():
    helper = _js_functions()
    js = """const n=(v,d=2)=>Number(v).toFixed(d);
const metricBar=()=>'<div>ไม่มี FT ที่ยืนยัน</div>';
""" + helper + """
const valid={n:34,goals_n:34,avg_total_goals:2.73,over_2_5_pct:55.88,under_2_5_pct:44.12};
const empty={n:0,goals_n:0,avg_total_goals:null,over_2_5_pct:null,under_2_5_pct:null};
const old={...valid,avg_total_goals:undefined};
const mismatch={...valid,goals_n:33};
const zero={...valid,avg_total_goals:0};
console.log(JSON.stringify({
  full:ouSplitBar(valid),
  empty:ouSplitBar(empty),
  old:ouSplitBar(old),
  mismatch:ouSplitBar(mismatch),
  zero:ouSplitBar(zero)
}));"""
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True)
    rendered = json.loads(out.stdout)
    assert "N=34 · FT ที่ยืนยัน</div><div class=\"ou-goal-avg\"" in rendered["full"]
    assert "2.73</strong> ลูก/คู่" in rendered["full"]
    assert "Over 2.5" in rendered["full"] and "Under 2.5" in rendered["full"]
    assert "ou-goal-avg" not in rendered["empty"]
    assert "ou-goal-avg" not in rendered["old"]
    assert "ou-goal-avg" not in rendered["mismatch"]
    assert "0.00</strong> ลูก/คู่" in rendered["zero"]
