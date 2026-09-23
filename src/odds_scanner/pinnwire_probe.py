from __future__ import annotations
import json, urllib.parse, urllib.request
from datetime import datetime, timezone

BASE="https://pinnwire.com/kit/v1/markets"

def probe():
    now=datetime.now(timezone.utc).isoformat()
    try:
        url=BASE+"?"+urllib.parse.urlencode({"sport_id":1,"key":"demo","fresh":"football-odds-scanner"})
        req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"football-odds-scanner/0.1"})
        with urllib.request.urlopen(req,timeout=20) as r:
            payload=json.loads(r.read().decode())
        events=payload.get("events") or payload.get("data") or []
        samples=[]; spreads=0
        for ev in events:
            periods=ev.get("periods") or {}
            p0=periods.get("num_0") or periods.get("0") or {}
            sp=p0.get("spreads") or {}
            if sp: spreads+=1
            if len(samples)<3: samples.append({"id":ev.get("id"),"home":ev.get("home"),"away":ev.get("away"),"starts":ev.get("starts") or ev.get("start_time"),"spread_keys":list(sp)[:5] if isinstance(sp,dict) else [], "period_keys":list(periods)[:8] if isinstance(periods,dict) else [], "period0":p0})
        return {"provider":"pinnwire_demo","generated_at":now,"status":"OK" if events else "NO_EVENTS","events":len(events),"events_with_spreads":spreads,"provider_generated_at":payload.get("generated_at"),"samples":samples}
    except Exception as e:
        return {"provider":"pinnwire_demo","generated_at":now,"status":"UNAVAILABLE","events":0,"errors":[f"{type(e).__name__}: {e}"]}

if __name__=="__main__": print(json.dumps(probe(),ensure_ascii=False))
