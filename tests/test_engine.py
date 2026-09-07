from pathlib import Path
from odds_scanner.football_data import decode_csv
from odds_scanner.normalize import normalize_rows, fair_probs
from odds_scanner.backtest import build_report

def test_fair_probabilities_sum_to_one():
    p,m=fair_probs(1.75,3.8,4.8)
    assert abs(sum(p)-1)<1e-12
    assert m>0

def test_normalize_and_backtest():
    raw=Path(__file__).parent/"fixtures/sample.csv"
    rows=normalize_rows(decode_csv(raw.read_bytes()),"2324")
    assert len(rows)==3
    rep=build_report(rows,test_seasons={"2324"},min_n=1)
    assert rep["rows"]==3
    assert any(x["side"]=="H" for x in rep["buckets"])
    assert all(x["split"]=="test" for x in rep["buckets"])
