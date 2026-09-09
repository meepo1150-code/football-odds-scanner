from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone

from .flashscore_exact_probe import first_flashscore_ref, USER_AGENT

REPORT_PATH = Path("reports/flashscore_structured_result_probe.json")


class StructuredHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts: list[str] = []
        self.meta: list[dict[str, str]] = []
        self.script_types: dict[str, int] = {}
        self.script_ids: list[str] = []
        self._script_type: str | None = None
        self._script_buf: list[str] = []
        self.jsonld: list[object] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        amap = {str(k).lower(): str(v) for k, v in attrs if k and v is not None}
        if tag.lower() == "title":
            self.in_title = True
        elif tag.lower() == "meta":
            name = amap.get("property") or amap.get("name")
            content = amap.get("content")
            if name and content and name.lower() in {
                "og:title", "og:description", "twitter:title", "twitter:description", "description"
            }:
                self.meta.append({"name": name, "content": content[:500]})
        elif tag.lower() == "script":
            stype = amap.get("type", "")
            self.script_types[stype] = self.script_types.get(stype, 0) + 1
            if amap.get("id"):
                self.script_ids.append(amap["id"][:120])
            self._script_type = stype.lower()
            self._script_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False
        elif tag.lower() == "script":
            if self._script_type == "application/ld+json" and self._script_buf:
                raw = "".join(self._script_buf).strip()
                try:
                    self.jsonld.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
            self._script_type = None
            self._script_buf = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self._script_type is not None:
            self._script_buf.append(data)


def _sanitize_jsonld(value, depth: int = 0):
    """Keep only compact sports/result-like structured fields; never persist page blobs."""
    if depth > 5:
        return None
    allowed = {
        "@type", "name", "startDate", "endDate", "eventStatus", "description",
        "homeTeam", "awayTeam", "competitor", "result", "score", "homeScore",
        "awayScore", "winner", "url"
    }
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in allowed:
                sv = _sanitize_jsonld(v, depth + 1)
                if sv is not None:
                    out[str(k)] = sv
        return out or None
    if isinstance(value, list):
        items = [_sanitize_jsonld(v, depth + 1) for v in value[:20]]
        return [x for x in items if x is not None] or None
    if isinstance(value, (str, int, float, bool)):
        text = str(value)
        return text[:500] if isinstance(value, str) else value
    return None


def inspect_html(body: bytes) -> dict:
    text = body.decode("utf-8", errors="replace")
    parser = StructuredHTMLParser()
    parser.feed(text)
    title = " ".join(x.strip() for x in parser.title_parts if x.strip())[:500]
    sanitized = [_sanitize_jsonld(x) for x in parser.jsonld]
    sanitized = [x for x in sanitized if x]
    lower = text.lower()
    signals = {
        "contains_jsonld": bool(parser.jsonld),
        "contains_eventstatus_token": "eventstatus" in lower,
        "contains_homescore_token": "homescore" in lower,
        "contains_awayscore_token": "awayscore" in lower,
        "contains_score_token": bool(re.search(r"\bscore\b", lower)),
        "contains_match_id_token": "mid=" in lower,
    }
    return {
        "title": title,
        "meta": parser.meta[:10],
        "script_type_counts": dict(sorted(parser.script_types.items())),
        "script_ids": sorted(set(parser.script_ids))[:30],
        "structured_jsonld": sanitized[:5],
        "signals": signals,
        "html_bytes_inspected": len(body),
    }


def fetch_event(ref: dict, timeout: int = 20) -> tuple[dict, bytes | None]:
    fid = ref["flashscore_id"]
    url = f"https://www.flashscore.com/match/{fid}/"
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(1_000_000)
            return {
                "status": int(resp.status),
                "final_url": resp.geturl(),
                "content_type": resp.headers.get("Content-Type"),
            }, body
    except urllib.error.HTTPError as exc:
        return {"status": int(exc.code), "error": f"HTTPError: {exc}"}, None
    except Exception as exc:
        return {"status": None, "error": f"{type(exc).__name__}: {exc}"}, None


def run_probe(root: Path = Path(".")) -> dict:
    ref = first_flashscore_ref(root)
    report = {
        "schema_version": "1.0",
        "classification": "EXACT_ID_STRUCTURED_RESULT_EVIDENCE_PROBE",
        "provider": "flashscore",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "promotion_allowed": False,
        "mapping_policy": "ODDSPAPI_EXACT_EXTERNAL_PROVIDER_ID_ONLY",
    }
    if not ref:
        report.update({"status": "NO_EXACT_REF", "requests_attempted": 0})
    else:
        fetch, body = fetch_event(ref)
        report.update({"fixture_ref": ref, "requests_attempted": 1, "fetch": fetch})
        if body is None or fetch.get("status") != 200:
            report["status"] = "UNAVAILABLE"
        else:
            evidence = inspect_html(body)
            report["evidence"] = evidence
            report["status"] = "STRUCTURED_EVIDENCE_PRESENT" if evidence["structured_jsonld"] else "NO_STRUCTURED_RESULT_EVIDENCE"
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(run_probe())
