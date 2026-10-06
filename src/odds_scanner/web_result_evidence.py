from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlparse
from .oddspapi_result_cache import RESULTS_PATH, merge_normalized_results
from .pinnwire_result_join import SNAPSHOTS_PATH, _read, _utc, _name
from .web_result_recovery import validate_evidence

EVIDENCE_PATH=Path("data/research/web_result_evidence.jsonl")
REPORT_PATH=Path("reports/web_result_evidence_import.json")

def _host(url):
    return (urlparse(str(url)).hostname or "").casefold().removeprefix("www.")

def _same_identity(e,s):
    return (_name(e.get("home"))==_name(s.get("home"))
            and _name(e.get("away"))==_name(s.get("away"))
            and _utc(e.get("kickoff"))==_utc(s.get("kickoff")))

def _quality(e):
    sources=e.get("sources") or []
    if not sources and e.get("source_url"):
        sources=[{"url":e["source_url"],"tier":e.get("source_tier")}]
    official=[x for x in sources if str(x.get("tier") or "").upper()=="A_OFFICIAL" and str(x.get("url") or "").startswith("https://")]
    reputable=[x for x in sources if str(x.get("tier") or "").upper() in {"A_OFFICIAL","B_REPUTABLE"} and str(x.get("url") or "").startswith("https://")]
    hosts={_host(x.get("url")) for x in reputable if _host(x.get("url"))}
    if official: return True,"TIER_A_OFFICIAL"
    if len(hosts)>=2: return True,"TIER_B_TWO_INDEPENDENT_SOURCES"
    return False,"INSUFFICIENT_SOURCE_CORROBORATION"

def import_evidence(root=Path(".")):
    snaps=_read(root/SNAPSHOTS_PATH)
    by_id={str(s.get("fixture_id")):s for s in snaps if s.get("fixture_id")}
    existing={str(r.get("fixture_id")):r for r in _read(root/RESULTS_PATH) if r.get("fixture_id")}
    accepted=[]; quarantine=[]; skipped_trusted=[]
    for e in _read(root/EVIDENCE_PATH):
        ids=e.get("fixture_ids") or [e.get("fixture_id")]
        ids=[str(x) for x in ids if x]
        # Expand only across the exact deterministic match identity.
        for candidate_id,s in by_id.items():
            if _same_identity(e,s) and candidate_id not in ids:
                ids.append(candidate_id)
        ok,reason=validate_evidence(e)
        if not ok:
            quarantine.append({"fixture_id":e.get("fixture_id"),"reason":reason}); continue
        qok,qreason=_quality(e)
        if not qok:
            quarantine.append({"fixture_id":e.get("fixture_id"),"reason":qreason}); continue
        valid_ids=[]
        for fid in ids:
            s=by_id.get(fid)
            if not s or not _same_identity(e,s):
                quarantine.append({"fixture_id":fid,"reason":"IDENTITY_MISMATCH_OR_UNKNOWN_FIXTURE"}); continue
            old=existing.get(fid)
            if old and not str(old.get("result_source") or "").startswith("WEB_EVIDENCE"):
                skipped_trusted.append(fid); continue
            if old and (old.get("ft_home_goals"),old.get("ft_away_goals")) != (e["ft_home_goals"],e["ft_away_goals"]):
                quarantine.append({"fixture_id":fid,"reason":"CONFLICT_WITH_EXISTING_WEB_EVIDENCE"}); continue
            valid_ids.append(fid)
        for fid in valid_ids:
            accepted.append({"fixture_id":fid,"ft_home_goals":e["ft_home_goals"],"ft_away_goals":e["ft_away_goals"],
                "result_source":"WEB_EVIDENCE_"+qreason,"source_urls":[x.get("url") for x in (e.get("sources") or [])],
                "retrieved_at":e.get("retrieved_at"),"evidence_status":"FT"})
    added=merge_normalized_results(root/RESULTS_PATH,accepted)
    report={"classification":"WEB_RESULT_EVIDENCE_IMPORT","evidence_rows":len(_read(root/EVIDENCE_PATH)),
      "accepted_rows":len(accepted),"results_added":added,"skipped_trusted":sorted(set(skipped_trusted)),
      "quarantine":quarantine,"api_requests_used":0}
    p=root/REPORT_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report

if __name__=="__main__": print(json.dumps(import_evidence(),ensure_ascii=False))
