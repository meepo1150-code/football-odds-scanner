from __future__ import annotations
import json, os, urllib.parse, urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

BASE="https://api.prop-line.com/v1"
ENV_KEY="PROPLINE_API_KEY"
SPORTS=("soccer_epl","soccer_uefa_champs_league","soccer_uefa_europa_league","soccer_uefa_conference_league","soccer_efl_champ","soccer_germany_bundesliga","soccer_spain_la_liga","soccer_italy_serie_a","soccer_france_ligue_one","soccer_netherlands_eredivisie","soccer_japan_j_league","soccer_usa_mls","soccer_sweden_allsvenskan","soccer_turkey_super_lig")

def active_soccer_sports(key):
    try:
        payload=_get("/sports",key)
        items=payload.get("data") or payload.get("sports") or [] if isinstance(payload,dict) else payload
        keys=[str(x.get("key")) for x in (items or []) if isinstance(x,dict) and x.get("active") is not False and str(x.get("key","")).startswith("soccer")]
        return tuple(dict.fromkeys(keys)) or SPORTS
    except Exception:
        return SPORTS
PREFERRED=("pinnacle","marathonbet","matchbook","betonlineag","bovada")

def _get(path,key,params=None):
    q=dict(params or {}); q["apiKey"]=key
    req=urllib.request.Request(BASE+path+"?"+urllib.parse.urlencode(q),headers={"Accept":"application/json","User-Agent":"football-odds-scanner/0.1"})
    with urllib.request.urlopen(req,timeout=20) as r: return json.loads(r.read().decode())

def _dec(v):
    try:
        x=float(v)
        # PropLine emits American prices as integers (e.g. +276 / -112),
        # while decimal prices are already small positive floats.
        if x >= 10: return 1 + x / 100
        if x <= -10: return 1 + 100 / abs(x)
        if x > 1: return x
    except (TypeError, ValueError):
        pass
    return None

def fetch(key=None):
    key=key or os.getenv(ENV_KEY)
    if not key: raise RuntimeError(f"{ENV_KEY} is not configured")
    rows=[]; errors=[]
    sports=active_soccer_sports(key)
    for sport in sports:
        try: events=_get(f"/sports/{sport}/odds",key,{"markets":"h2h,spreads,totals"})
        except Exception as e: errors.append(f"{sport}:{type(e).__name__}:{e}"); continue
        if isinstance(events,dict): events=events.get("data") or events.get("events") or []
        for ev in events or []:
            books=ev.get("bookmakers") or []
            book=next((b for k in PREFERRED for b in books if str(b.get("key","")).lower()==k), books[0] if books else None)
            if not book: continue
            # A provider can expose more than one object for the same market key.
            # Do not collapse those objects into a dict and accidentally keep an
            # alternate spread.  For AH, only accept a two-sided pair whose
            # decimal prices form a plausible mainline (both 1.80..2.20).
            market_list=book.get("markets",[])
            h2h=next((m for m in market_list if m.get("key")=="h2h"),None)
            tot=next((m for m in market_list if m.get("key")=="totals"),None)
            spread_candidates=[m for m in market_list if m.get("key")=="spreads"]
            sp=None
            home,away=ev.get("home_team"),ev.get("away_team")
            for candidate in spread_candidates:
                co=candidate.get("outcomes") or []
                ch=next((o for o in co if o.get("name")==home),None)
                ca=next((o for o in co if o.get("name")==away),None)
                if not ch or not ca: continue
                hp,ap=_dec(ch.get("price")),_dec(ca.get("price"))
                try:
                    opposite=abs(float(ch.get("point"))+float(ca.get("point"))) < 1e-9
                except (TypeError,ValueError):
                    opposite=False
                if opposite and hp is not None and ap is not None and 1.80 <= hp <= 2.20 and 1.80 <= ap <= 2.20:
                    sp=candidate; break
            if not sp: continue
            outs=sp.get("outcomes") or []
            ho=next((o for o in outs if o.get("name")==home),None); ao=next((o for o in outs if o.get("name")==away),None)
            if not ho or not ao: continue
            tout=(tot or {}).get("outcomes") or []
            over=next((o for o in tout if str(o.get("name","")).lower()=="over"),None); under=next((o for o in tout if str(o.get("name","")).lower()=="under"),None)
            mout=(h2h or {}).get("outcomes") or []
            def price(name): 
                o=next((x for x in mout if x.get("name")==name),None); return _dec(o.get("price")) if o else None
            draw=next((x for x in mout if str(x.get("name","")).lower()=="draw"),None)
            rows.append({"sport":sport,"event_id":str(ev.get("id")),"kickoff":ev.get("commence_time"),"home":home,"away":away,"bookmaker":book.get("key"),"bookmaker_updated_at":book.get("last_update"),"ah_home_line":ho.get("point"),"ah_home_odds":_dec(ho.get("price")),"ah_away_line":ao.get("point"),"ah_away_odds":_dec(ao.get("price")),"ou_line":(over or under or {}).get("point"),"over_odds":_dec(over.get("price")) if over else None,"under_odds":_dec(under.get("price")) if under else None,"one_x_two_home":price(home),"one_x_two_draw":_dec(draw.get("price")) if draw else None,"one_x_two_away":price(away)})
    return rows,errors

def probe():
    now=datetime.now(timezone.utc).isoformat()
    try: rows,errors=fetch()
    except Exception as e: return {"provider":"propline","generated_at":now,"status":"UNAVAILABLE","rows":0,"errors":[f"{type(e).__name__}: {e}"]}
    return {"provider":"propline","generated_at":now,"status":"OK" if rows else "NO_ROWS","rows":len(rows),"books":sorted(set(r["bookmaker"] for r in rows)),"sports":sorted(set(r["sport"] for r in rows)),"quarter_ah":sum(1 for r in rows if r["ah_home_line"] is not None and abs(float(r["ah_home_line"])*2-round(float(r["ah_home_line"])*2))>1e-8),"errors":errors[:10],"samples":rows[:3]}

if __name__=="__main__": print(json.dumps(probe(),ensure_ascii=False))
