from __future__ import annotations
import json, os, time, urllib.parse, urllib.request, urllib.error
from datetime import timedelta
LAST_FETCH_DIAGNOSTICS = {}
from dataclasses import dataclass
from datetime import datetime, timezone

BASE="https://api.prop-line.com/v1"
ENV_KEY="PROPLINE_API_KEY"
# Reviewed active Europe/UEFA keys only. Never expand odds calls from an unreviewed catalog.
SPORTS=("soccer_epl","soccer_uefa_champs_league","soccer_uefa_europa_league","soccer_uefa_conference_league","soccer_efl_champ","soccer_germany_bundesliga","soccer_spain_la_liga","soccer_italy_serie_a","soccer_france_ligue_one","soccer_netherlands_eredivisie","soccer_sweden_allsvenskan","soccer_turkey_super_lig")

def retry_seconds(exc):
    value=exc.headers.get('Retry-After','3600') if exc.headers else '3600'
    try:return max(3600,float(value))
    except (TypeError,ValueError):
        try:
            from email.utils import parsedate_to_datetime
            return max(3600,(parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds())
        except (ValueError,TypeError):return 3600

def active_soccer_sports(key):
    try:
        payload=_get("/sports",key)
        items=payload.get("data") or payload.get("sports") or [] if isinstance(payload,dict) else payload
        from .research_population import exclusion_reason
        keys=[str(x.get("key")) for x in (items or []) if isinstance(x,dict) and x.get("active") is not False and str(x.get("key","")) in SPORTS and exclusion_reason({'provider':'propline', 'country':x.get('country'), 'league':x.get('title') or x.get('name') or x.get('key')}) is None]
        # A real catalog whose entries are all excluded must not re-enable fallback.
        return tuple(dict.fromkeys(keys)) if items else SPORTS
    except urllib.error.HTTPError as exc:
        if exc.code in (401,403,429):raise
        return SPORTS
    except Exception:
        return SPORTS
PREFERRED=("pinnacle",)

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
    deadline=time.monotonic()+240
    LAST_FETCH_DIAGNOSTICS.clear()
    LAST_FETCH_DIAGNOSTICS.update(http_requests_attempted=1,retry_cap=0,timeout_seconds=20)
    try:sports=active_soccer_sports(key)
    except urllib.error.HTTPError as exc:
        LAST_FETCH_DIAGNOSTICS.update(cooldown_until=(datetime.now(timezone.utc)+timedelta(seconds=retry_seconds(exc))).isoformat(),failure_class='RATE_LIMITED' if exc.code==429 else 'ACCOUNT_OR_AUTH_BLOCKED')
        return [],[f'catalog:HTTPError:{exc.code}']
    for sport in sports:
        if time.monotonic()+20>deadline:
            LAST_FETCH_DIAGNOSTICS['bounded_runtime_partial']=True
            errors.append('TRANSPORT_TIME_BUDGET_REACHED; remaining sports deferred')
            break
        LAST_FETCH_DIAGNOSTICS["http_requests_attempted"]+=1
        try: events=_get(f"/sports/{sport}/odds",key,{"markets":"h2h,spreads,totals"})
        except Exception as e:
            message=str(e).replace(key,"[REDACTED]")
            errors.append(f"{sport}:{type(e).__name__}:{message}")
            if isinstance(e,urllib.error.HTTPError) and e.code in (429,401,403):
                # Stop the catalog fan-out immediately on account/rate-limit failures.
                seconds=retry_seconds(e)
                LAST_FETCH_DIAGNOSTICS.update(cooldown_until=(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat(),failure_class='RATE_LIMITED' if e.code==429 else 'ACCOUNT_OR_AUTH_BLOCKED')
                break
            continue
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
    return {"provider":"propline","generated_at":now,"status":("PARTIAL" if errors else "OK") if rows else "NO_ROWS",**LAST_FETCH_DIAGNOSTICS,"rows":len(rows),"books":sorted(set(r["bookmaker"] for r in rows)),"sports":sorted(set(r["sport"] for r in rows)),"quarter_ah":sum(1 for r in rows if r["ah_home_line"] is not None and abs(float(r["ah_home_line"])*2-round(float(r["ah_home_line"])*2))>1e-8),"errors":errors[:10],"samples":rows[:3]}

if __name__=="__main__": print(json.dumps(probe(),ensure_ascii=False))
