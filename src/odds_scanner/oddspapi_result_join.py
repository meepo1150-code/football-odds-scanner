from __future__ import annotations

import json
from pathlib import Path

TICKS=Path("data/normalized/oddspapi_history_ticks.jsonl")
RESULTS=Path("data/normalized/oddspapi_finished_results.jsonl")
OUTPUT=Path("data/normalized/oddspapi_prematch_joined.jsonl")
REPORT=Path("reports/oddspapi_result_join.json")


def _rows(path: Path) -> list[dict]:
    if not path.exists(): return []
    out=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        try: row=json.loads(line)
        except (json.JSONDecodeError,TypeError): continue
        if isinstance(row,dict): out.append(row)
    return out


def normalize_result(fixture: dict) -> dict | None:
    """Accept only explicit finished full-time score fields; never infer from names/odds."""
    if fixture.get("statusId") != 2 or fixture.get("fixtureId") is None:
        return None
    pairs=(("participant1Score","participant2Score"),("homeScore","awayScore"),("score1","score2"))
    hg=ag=None
    for a,b in pairs:
        if isinstance(fixture.get(a),(int,float)) and isinstance(fixture.get(b),(int,float)):
            hg,ag=int(fixture[a]),int(fixture[b]); break
    if hg is None or ag is None or hg<0 or ag<0: return None
    return {"fixture_id":str(fixture["fixtureId"]),"ft_home_goals":hg,"ft_away_goals":ag,"result_source":"ODDSPAPI_FINISHED_FIXTURE_EXPLICIT_SCORE"}


def join_rows(ticks: list[dict], results: list[dict]) -> tuple[list[dict],dict]:
    index={str(r.get("fixture_id")):r for r in results if r.get("fixture_id") is not None}
    joined=[]; missing=[]
    for row in ticks:
        fid=str(row.get("fixture_id"))
        result=index.get(fid)
        if not result:
            missing.append(fid); continue
        item=dict(row)
        item.update({"ft_home_goals":result["ft_home_goals"],"ft_away_goals":result["ft_away_goals"],"result_source":result.get("result_source"),"result_join_status":"JOINED","promotion_eligible":False})
        joined.append(item)
    report={"schema_version":"1.0","classification":"RESULT_JOIN_QA_ONLY","tick_fixtures":len(ticks),"result_fixtures":len(index),"joined_fixtures":len(joined),"missing_result_fixtures":len(missing),"join_rate":round(len(joined)/len(ticks),6) if ticks else 0.0,"promotion_allowed":False,"promotion_blockers":["ODDSPAPI_HISTORY_NOT_MULTI_SEASON","VALIDATION_NOT_RUN"]}
    return joined,report


def write_join(root: Path=Path(".")) -> dict:
    joined,report=join_rows(_rows(root/TICKS),_rows(root/RESULTS))
    out=root/OUTPUT; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in joined),encoding="utf-8")
    rp=root/REPORT; rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
