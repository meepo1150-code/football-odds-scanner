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
    """Validate recorded manual assertions; this does not fetch source pages."""
    sources=e.get("sources")
    if not isinstance(sources,list) or not sources:
        return False,"MISSING_SOURCE_ASSERTIONS"
    hosts=set(); official=False
    ko=_utc(e.get("kickoff"))
    if ko is None or not _name(e.get("home")) or not _name(e.get("away")):
        return False,"INVALID_MATCH_IDENTITY"
    for source in sources:
        if not isinstance(source,dict): return False,"MALFORMED_SOURCE"
        try:
            url=urlparse(str(source.get("url") or ""))
            host=_host(source.get("url"))
            if url.scheme != "https" or not host or url.username or url.password or url.port:
                return False,"INVALID_SOURCE_URL"
        except ValueError:
            return False,"INVALID_SOURCE_URL"
        if host in hosts: return False,"DUPLICATE_SOURCE_HOST"
        hosts.add(host)
        tier=source.get("tier")
        if tier not in {"A_OFFICIAL","B_REPUTABLE"}: return False,"INVALID_SOURCE_TIER"
        official=official or tier=="A_OFFICIAL"
        assertion=source.get("assertion")
        if not isinstance(assertion,dict): return False,"MISSING_SOURCE_ASSERTIONS"
        if assertion.get("verification_method") != "MANUAL_WEB_REVIEW":
            return False,"INVALID_VERIFICATION_METHOD"
        if not isinstance(assertion.get("source_title"),str) or not assertion["source_title"].strip():
            return False,"MISSING_SOURCE_TITLE"
        if assertion.get("status") != "FT": return False,"SOURCE_RESULT_NOT_FINAL"
        for field in ("home","away"):
            if not isinstance(assertion.get(field),str) or _name(assertion[field]) != _name(e.get(field)):
                return False,"SOURCE_IDENTITY_MISMATCH"
        for field in ("ft_home_goals","ft_away_goals"):
            if type(assertion.get(field)) is not int or assertion[field] != e.get(field):
                return False,"SOURCE_SCORE_MISMATCH"
        if not assertion.get("kickoff") and not assertion.get("match_date"):
            return False,"MISSING_SOURCE_DATE"
        # match_date is explicitly a UTC match date. Local dates must first be
        # reconciled against the source timezone by the reviewer.
        if assertion.get("kickoff") and _utc(assertion["kickoff"]) != ko:
            return False,"SOURCE_KICKOFF_MISMATCH"
        if assertion.get("match_date") and assertion["match_date"] != ko.date().isoformat():
            return False,"SOURCE_DATE_MISMATCH"
    if e.get("source_url") not in [x["url"] for x in sources]:
        return False,"PRIMARY_SOURCE_NOT_ASSERTED"
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
                "retrieved_at":e.get("retrieved_at"),"evidence_status":"FT",
                "source_assertions":e["sources"],"verification_method":"MANUAL_WEB_REVIEW"})
    added=merge_normalized_results(root/RESULTS_PATH,accepted)
    report={"classification":"WEB_RESULT_EVIDENCE_IMPORT","evidence_rows":len(_read(root/EVIDENCE_PATH)),
      "accepted_rows":len(accepted),"results_added":added,"skipped_trusted":sorted(set(skipped_trusted)),
      "quarantine":quarantine,"api_requests_used":0,"validation_relaxed":False,
      "provenance_policy":"PER_SOURCE_MANUAL_ASSERTIONS_REQUIRED",
      "automatic_page_content_verification":False,
      "existing_results_revalidated":False}
    p=root/REPORT_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report

if __name__=="__main__": print(json.dumps(import_evidence(),ensure_ascii=False))
