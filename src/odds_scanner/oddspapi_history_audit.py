from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ARCHIVE = Path("data/normalized/oddspapi_history_ticks.jsonl")
REPORT = Path("reports/oddspapi_history_audit.json")


def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row=json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row,dict):
            rows.append(row)
    return rows


def _ticks(series) -> list[dict]:
    return series if isinstance(series,list) else []


def audit_rows(rows: list[dict]) -> dict:
    leagues=Counter()
    ah_lines=Counter()
    ou_lines=Counter()
    fixtures_with_1x2=fixtures_with_ah=fixtures_with_ou=0
    fixtures_with_all=0
    invalid_quarter_lines=0
    timestamped_ticks=0
    active_ticks=0
    earliest=None
    latest=None

    for row in rows:
        leagues[str(row.get("league") or "UNKNOWN")]+=1
        ox=row.get("one_x_two")
        has_1x2=isinstance(ox,dict) and all(_ticks(ox.get(k)) for k in ("home","draw","away"))
        ah=row.get("asian_handicap") if isinstance(row.get("asian_handicap"),list) else []
        ou=row.get("over_under") if isinstance(row.get("over_under"),list) else []
        has_ah=bool(ah); has_ou=bool(ou)
        fixtures_with_1x2+=int(has_1x2); fixtures_with_ah+=int(has_ah); fixtures_with_ou+=int(has_ou)
        fixtures_with_all+=int(has_1x2 and has_ah and has_ou)

        series=[]
        if isinstance(ox,dict):
            series += [_ticks(ox.get(k)) for k in ("home","draw","away")]
        for market in ah:
            line=market.get("line")
            if isinstance(line,(int,float)):
                ah_lines[f"{float(line):.2f}"]+=1
                if abs(float(line)*4-round(float(line)*4))>1e-9: invalid_quarter_lines+=1
            series += [_ticks(market.get("home")),_ticks(market.get("away"))]
        for market in ou:
            line=market.get("line")
            if isinstance(line,(int,float)):
                ou_lines[f"{float(line):.2f}"]+=1
                if abs(float(line)*4-round(float(line)*4))>1e-9: invalid_quarter_lines+=1
            series += [_ticks(market.get("over")),_ticks(market.get("under"))]
        for ticks in series:
            for tick in ticks:
                ts=tick.get("created_at")
                if isinstance(ts,str):
                    timestamped_ticks+=1
                    earliest=ts if earliest is None or ts<earliest else earliest
                    latest=ts if latest is None or ts>latest else latest
                active_ticks+=int(tick.get("active") is True)

    return {
        "schema_version":"1.0",
        "classification":"DATA_QUALITY_AUDIT_ONLY",
        "promotion_allowed":False,
        "fixture_rows":len(rows),
        "unique_fixture_ids":len({str(r.get("fixture_id")) for r in rows if r.get("fixture_id") is not None}),
        "league_counts":dict(sorted(leagues.items())),
        "coverage":{
            "fixtures_with_1x2":fixtures_with_1x2,
            "fixtures_with_asian_handicap":fixtures_with_ah,
            "fixtures_with_over_under":fixtures_with_ou,
            "fixtures_with_1x2_ah_ou":fixtures_with_all,
            "invalid_non_quarter_lines":invalid_quarter_lines,
            "timestamped_ticks":timestamped_ticks,
            "active_ticks":active_ticks,
            "earliest_tick":earliest,
            "latest_tick":latest,
        },
        "asian_handicap_line_counts":dict(sorted(ah_lines.items(),key=lambda x:float(x[0]))),
        "over_under_line_counts":dict(sorted(ou_lines.items(),key=lambda x:float(x[0]))),
        "result_join_status":"NOT_JOINED",
        "promotion_blockers":["MATCH_RESULTS_NOT_JOINED","ODDSPAPI_HISTORY_NOT_MULTI_SEASON"],
    }


def write_audit(root: Path=Path(".")) -> dict:
    report=audit_rows(_read_rows(root/ARCHIVE))
    path=root/REPORT
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(write_audit(),indent=2))
