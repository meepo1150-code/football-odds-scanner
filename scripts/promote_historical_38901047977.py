"""Promote reviewed Historical AH into the original Research V2 snapshot source."""
import argparse, json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE=Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
HIST=Path("data/historical/reconstructed_ah_slots.jsonl")
RECEIPT=Path("reports/historical_38901047977_promotion.json")
BKK=ZoneInfo("Asia/Bangkok")
def dt(s):
    x=datetime.fromisoformat(str(s).replace("Z","+00:00"))
    if x.tzinfo is None:raise ValueError("Timezone missing")
    return x
def read(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def build(original,historical,manifest):
    candidates={(str(c["fixture_id"]),str(c["bookmaker"]).lower()):c for c in manifest["candidates"]}
    if len(historical)!=105:raise ValueError("Expected 105 reviewed historical slots")
    output={};keys=set()
    for h in historical:
        fid=str(h["fixture_id"]);bk=str(h["bookmaker"]).lower();slot=dt(h["slot_utc"])
        c=candidates.get((fid,bk))
        if c is None or dt(c["kickoff"])!=dt(h["kickoff_utc"]) or slot>=dt(c["kickoff"]):raise ValueError("Fixture identity/kickoff mismatch")
        if h.get("line_selection")!="BALANCED_LINE" or h.get("market")!="AH" or h.get("mainline_verified") is not False:raise ValueError("Unreviewed market")
        obs=[o for o in c["observations"] if o.get("fixture_id")==fid and str(o.get("bookmaker","")).lower()==bk and (o.get("home"),o.get("away"),o.get("league"),o.get("kickoff"))==(c["home"],c["away"],c["league"],c["kickoff"]) and o.get("favorite_side") in ("H","A")]
        if not obs or len({o["favorite_side"] for o in obs})!=1:raise ValueError("Favorite/fixture identity not established")
        base=dict(obs[-1]);fav=base["favorite_side"]
        line=float(h["home_line"]);hp=float(h["quotes"]["home"]["price"]);ap=float(h["quotes"]["away"]["price"])
        ht=dt(h["quotes"]["home"]["quote_at_utc"]);at=dt(h["quotes"]["away"]["quote_at_utc"])
        if not (abs(line*4-round(line*4))<1e-8 and abs(line+float(h["away_line"]))<1e-8 and 1.8<=hp<=2.2 and 1.8<=ap<=2.2 and ht<=slot and at<=slot):raise ValueError("Price or timestamp invalid")
        local=slot.astimezone(BKK);day=(local.date()-timedelta(days=1) if local.hour<6 else local.date()).isoformat()
        key=(fid,bk,slot.isoformat())
        if key in keys:raise ValueError("Duplicate slot")
        keys.add(key)
        base.update(provider="oddspapi",football_day=day,bookmaker=h["bookmaker"],observed_at=max(ht,at).isoformat(),scheduled_target_at=slot.isoformat(),historical_target_slot_at=slot.isoformat(),historical_quote_home_at=ht.isoformat(),historical_quote_away_at=at.isoformat(),historical_provenance="ODDSPAPI_RECONSTRUCTED_FROM_RUN_38901047977",historical_market_id=h.get("market_id"),source_semantics="HISTORICAL_BALANCED_LINE_AS_OF_SLOT",mainline_verified=False,research_only=True,one_x_two={},ou={},favorite_fair_probability=None,ah={"home_line":line,"away_line":-line,"home_price":hp,"away_price":ap,"selected_side_line":line if fav=="H" else -line,"selected_side_price":hp if fav=="H" else ap,"opposite_side_price":ap if fav=="H" else hp})
        output[key]=base
    def is_replaced(r):
        try:slot=dt(r.get("scheduled_target_at") or r.get("historical_target_slot_at")).isoformat()
        except (ValueError,TypeError):return False
        return (str(r.get("fixture_id")),str(r.get("bookmaker","")).lower(),slot) in keys
    kept=[r for r in original if not is_replaced(r)]
    return kept+list(output.values()),{"source_run":38901047977,"historical_slots":len(output),"replaced_exact_target_rows":len(original)-len(kept),"canonical_rows_before":len(original),"canonical_rows_after":len(kept)+len(output),"formula_changed":False,"api_requests":0},keys
def main():
    p=argparse.ArgumentParser();p.add_argument("--manifest",type=Path,required=True);p.add_argument("--dry-run",action="store_true");a=p.parse_args()
    raw=SOURCE.read_text();original=[json.loads(s) for s in raw.splitlines() if s.strip()]
    result,receipt,keys=build(original,read(HIST),json.loads(a.manifest.read_text()))
    print(json.dumps(receipt,indent=2))
    if a.dry_run:return
    def replace_line(s):
        r=json.loads(s)
        try:slot=dt(r.get("scheduled_target_at") or r.get("historical_target_slot_at")).isoformat()
        except (ValueError,TypeError):return False
        return (str(r.get("fixture_id")),str(r.get("bookmaker","")).lower(),slot) in keys
    kept=[s for s in raw.splitlines(keepends=True) if not replace_line(s)]
    if len(kept)+105!=len(result):raise ValueError("Canonical preservation mismatch")
    SOURCE.write_text("".join(kept+[json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in result[-105:]]))
    RECEIPT.parent.mkdir(parents=True,exist_ok=True);RECEIPT.write_text(json.dumps(receipt,indent=2)+"\n")
if __name__=="__main__":main()
