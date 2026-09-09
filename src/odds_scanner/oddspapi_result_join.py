from __future__ import annotations
import json
from pathlib import Path

from .oddspapi_history_store import iter_rows as iter_tick_rows
from .oddspapi_prematch import extract_fixture

RESULTS=Path("data/normalized/oddspapi_finished_results.jsonl")
OUTPUT=Path("data/normalized/oddspapi_prematch_joined.jsonl")
REPORT=Path("reports/oddspapi_result_join.json")


def _rows(path:Path)->list[dict]:
    if not path.exists():
        return []
    out=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row=json.loads(line)
        except (json.JSONDecodeError,TypeError):
            continue
        if isinstance(row,dict):
            out.append(row)
    return out


def normalize_result(fixture:dict)->dict|None:
    """Accept only explicit finished FT result scores; never infer from period sums or team names."""
    if fixture.get("statusId")!=2 or fixture.get("fixtureId") is None:
        return None
    hg=ag=None
    source=None
    result=(fixture.get("scores") or {}).get("result") if isinstance(fixture.get("scores"),dict) else None
    if isinstance(result,dict) and isinstance(result.get("participant1Score"),(int,float)) and isinstance(result.get("participant2Score"),(int,float)):
        hg,ag=int(result["participant1Score"]),int(result["participant2Score"])
        source="ODDSPAPI_FIXTURE_SCORES_RESULT"
    else:
        for a,b in (("participant1Score","participant2Score"),("homeScore","awayScore"),("score1","score2")):
            if isinstance(fixture.get(a),(int,float)) and isinstance(fixture.get(b),(int,float)):
                hg,ag=int(fixture[a]),int(fixture[b])
                source="ODDSPAPI_FINISHED_FIXTURE_EXPLICIT_SCORE"
                break
    if hg is None or ag is None or hg<0 or ag<0:
        return None
    return {"fixture_id":str(fixture["fixtureId"]),"ft_home_goals":hg,"ft_away_goals":ag,"result_source":source}


def join_rows(prematch_rows:list[dict],results:list[dict])->tuple[list[dict],dict]:
    index={str(r.get("fixture_id")):r for r in results if r.get("fixture_id") is not None}
    joined=[]
    missing=[]
    for row in prematch_rows:
        fid=str(row.get("fixture_id"))
        result=index.get(fid)
        if not result:
            missing.append(fid)
            continue
        item=dict(row)
        item.update({
            "ft_home_goals":result["ft_home_goals"],
            "ft_away_goals":result["ft_away_goals"],
            "result_source":result.get("result_source"),
            "result_join_status":"JOINED",
            "promotion_eligible":False,
        })
        joined.append(item)
    report={
        "schema_version":"1.2",
        "classification":"RESULT_JOIN_QA_ONLY",
        "prematch_fixtures":len(prematch_rows),
        "result_fixtures":len(index),
        "joined_fixtures":len(joined),
        "missing_result_fixtures":len(missing),
        "join_rate":round(len(joined)/len(prematch_rows),6) if prematch_rows else 0.0,
        "prematch_semantics":"STRICT_PREMATCH_CREATED_AT_LT_KICKOFF",
        "promotion_allowed":False,
        "promotion_blockers":["ODDSPAPI_HISTORY_NOT_MULTI_SEASON","VALIDATION_NOT_RUN"],
    }
    return joined,report


def write_join(root:Path=Path("."))->dict:
    raw_rows=list(iter_tick_rows(root))
    prematch_rows=[]
    for row in raw_rows:
        extracted=extract_fixture(row)
        if extracted.get("one_x_two") or extracted.get("asian_handicap") or extracted.get("over_under"):
            prematch_rows.append(extracted)
    joined,report=join_rows(prematch_rows,_rows(root/RESULTS))
    report["raw_history_fixtures"]=len(raw_rows)
    out=root/OUTPUT
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in joined),encoding="utf-8")
    rp=root/REPORT
    rp.parent.mkdir(parents=True,exist_ok=True)
    rp.write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
