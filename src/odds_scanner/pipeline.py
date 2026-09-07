from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from .football_data import download_history, decode_csv, SEASONS
from .normalize import normalize_rows, write_csv
from .multimarket import normalize_multimarket_rows
from .backtest import build_report, write_report
from .joint_backtest import build_joint_report


def run(root: Path, download: bool=True):
    raw=root/"data/raw"
    norm=root/"data/normalized/history.csv"
    multi_norm=root/"data/normalized/multimarket_history.csv"
    report=root/"reports/backtest.json"
    joint_report_path=root/"reports/joint_patterns.json"
    provenance_report=root/"reports/data_provenance.json"
    paths=download_history(raw) if download else sorted(raw.glob("E0_*.csv"))
    all_rows=[]
    multi_rows=[]
    for p in paths:
        season=p.stem.split("_")[-1]
        decoded=decode_csv(p.read_bytes())
        all_rows.extend(normalize_rows(decoded,season))
        multi_rows.extend(normalize_multimarket_rows(decoded,season))
    write_csv(all_rows,norm)
    write_csv(multi_rows,multi_norm)
    test=set(SEASONS[-3:])
    rep=build_report(all_rows,test_seasons=test,min_n=20)
    write_report(rep,report)
    joint=build_joint_report(multi_rows,test_seasons=test,min_n=20)
    joint_report_path.parent.mkdir(parents=True,exist_ok=True)
    joint_report_path.write_text(json.dumps(joint,ensure_ascii=False,indent=2),encoding="utf-8")
    source_provenance=raw/"provenance.json"
    if source_provenance.exists():
        provenance_report.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_provenance, provenance_report)
    rep["joint_patterns"]={"source_rows":len(multi_rows),"buckets":len(joint["buckets"])}
    return rep

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--no-download",action="store_true")
    args=ap.parse_args()
    rep=run(Path(args.root),download=not args.no_download)
    print(json.dumps({"rows":rep["rows"],"buckets":len(rep["buckets"]),"test_seasons":rep["test_seasons"],"joint_patterns":rep["joint_patterns"]}))
if __name__=="__main__": main()
