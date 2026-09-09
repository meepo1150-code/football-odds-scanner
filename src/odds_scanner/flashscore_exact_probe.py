from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REFS_PATH = Path("data/normalized/oddspapi_fixture_refs.jsonl")
REPORT_PATH = Path("reports/flashscore_exact_id_probe.json")
USER_AGENT = "Mozilla/5.0 (compatible; football-odds-scanner/0.1; research-only)"


def first_flashscore_ref(root: Path = Path(".")) -> dict | None:
    path = root / REFS_PATH
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        providers = row.get("external_providers") if isinstance(row, dict) else None
        flash_id = providers.get("flashscoreId") if isinstance(providers, dict) else None
        if isinstance(flash_id, str) and flash_id.strip():
            return {
                "fixture_id": str(row.get("fixture_id")),
                "flashscore_id": flash_id.strip(),
                "home": row.get("home"),
                "away": row.get("away"),
                "kickoff": row.get("kickoff"),
            }
    return None


def probe_url(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(65536)
            return {
                "status": int(resp.status),
                "final_url": resp.geturl(),
                "content_type": resp.headers.get("Content-Type"),
                "sample_bytes": len(body),
                "html_like": b"<html" in body.lower() or b"<!doctype" in body.lower(),
            }
    except urllib.error.HTTPError as exc:
        return {"status": int(exc.code), "error": f"HTTPError: {exc}"}
    except Exception as exc:
        return {"status": None, "error": f"{type(exc).__name__}: {exc}"}


def run_probe(root: Path = Path(".")) -> dict:
    ref = first_flashscore_ref(root)
    report = {
        "schema_version": "1.0",
        "classification": "EXACT_EXTERNAL_ID_CONNECTIVITY_PROBE",
        "provider": "flashscore",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "promotion_allowed": False,
        "mapping_policy": "ODDSPAPI_EXACT_EXTERNAL_PROVIDER_ID_ONLY",
    }
    if not ref:
        report.update({"status": "NO_EXACT_REF", "requests_attempted": 0})
    else:
        fid = ref["flashscore_id"]
        urls = [
            f"https://www.flashscore.com/match/{fid}/",
            f"https://www.flashscore.com/match/{fid}/#/match-summary/match-summary",
            f"https://www.flashscore.com/match/{fid}/#/match-summary",
        ]
        probes = [{"url_form": i + 1, **probe_url(url)} for i, url in enumerate(urls)]
        ok = any(p.get("status") == 200 for p in probes)
        report.update({
            "status": "PUBLIC_PAGE_REACHABLE" if ok else "BLOCKED_OR_UNREACHABLE",
            "requests_attempted": len(probes),
            "fixture_ref": ref,
            "probes": probes,
        })
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(run_probe())
