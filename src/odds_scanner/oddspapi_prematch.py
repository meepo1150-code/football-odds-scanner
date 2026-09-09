from __future__ import annotations

from datetime import datetime, timezone


def _utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def prematch_ticks(series, kickoff: str) -> list[dict]:
    ko=_utc(kickoff)
    if ko is None or not isinstance(series,list):
        return []
    valid=[]
    for tick in series:
        if not isinstance(tick,dict):
            continue
        ts=_utc(tick.get("created_at"))
        price=tick.get("price")
        if ts is None or ts>=ko or not isinstance(price,(int,float)) or float(price)<=1:
            continue
        valid.append((ts,tick))
    valid.sort(key=lambda x:x[0])
    return [x[1] for x in valid]


def opening_closing(series, kickoff: str) -> dict | None:
    ticks=prematch_ticks(series,kickoff)
    if not ticks:
        return None
    first,last=ticks[0],ticks[-1]
    return {
        "opening_price":float(first["price"]),
        "opening_at":first["created_at"],
        "closing_price":float(last["price"]),
        "closing_at":last["created_at"],
        "prematch_tick_count":len(ticks),
    }


def extract_fixture(row: dict) -> dict:
    kickoff=row.get("kickoff")
    ox=row.get("one_x_two") if isinstance(row.get("one_x_two"),dict) else {}
    one={k:opening_closing(ox.get(k),kickoff) for k in ("home","draw","away")}
    one={k:v for k,v in one.items() if v is not None}
    ah=[]
    for market in row.get("asian_handicap") or []:
        home=opening_closing(market.get("home"),kickoff)
        away=opening_closing(market.get("away"),kickoff)
        if home and away:
            ah.append({"line":market.get("line"),"home":home,"away":away})
    ou=[]
    for market in row.get("over_under") or []:
        over=opening_closing(market.get("over"),kickoff)
        under=opening_closing(market.get("under"),kickoff)
        if over and under:
            ou.append({"line":market.get("line"),"over":over,"under":under})
    return {
        "fixture_id":row.get("fixture_id"),"league":row.get("league"),"kickoff":kickoff,
        "home":row.get("home"),"away":row.get("away"),"bookmaker":row.get("bookmaker"),
        "one_x_two":one,"asian_handicap":ah,"over_under":ou,
        "snapshot_semantics":"STRICT_PREMATCH_CREATED_AT_LT_KICKOFF",
        "result_join_status":"NOT_JOINED","promotion_eligible":False,
    }
