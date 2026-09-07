from __future__ import annotations
import argparse, json
from pathlib import Path
from .football_data import download_history, decode_csv, SEASONS
from .normalize import normalize_rows, write_csv
from .backtest import build_report, write_report

def run(root: Path, download: bool=True):
    raw=root/"data/raw"; norm=root/"data/normalized/history.csv"; report=root/"reports/backtest.json"
    paths=download_history(raw) if download else sorted(raw.glob("E0_*.csv"))
    all_rows=[]
    for p in paths:
        season=p.stem.split("_")[-1]
        all_rows.extend(normalize_rows(decode_csv(p.read_bytes()),season))
    write_csv(all_rows,norm)
    test=set(SEASONS[-3:])
    rep=build_report(all_rows,test_seasons=test,min_n=20)
    write_report(rep,report)
    return rep

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--no-download",action="store_true")
    args=ap.parse_args()
    rep=run(Path(args.root),download=not args.no_download)
    print(json.dumps({"rows":rep["rows"],"buckets":len(rep["buckets"]),"test_seasons":rep["test_seasons"]}))
if __name__=="__main__": main()
