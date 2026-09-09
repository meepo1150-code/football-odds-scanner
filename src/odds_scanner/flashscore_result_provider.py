from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .flashscore_exact_probe import USER_AGENT
from .oddspapi_fixture_refs import REFS_PATH
from .oddspapi_result_cache import RESULTS_PATH, merge_normalized_results

REPORT_PATH = Path("reports/flashscore_result_backfill.json")
SCORE_RE = re.compile(r"\s(\d+)\s*-\s*(\d+)\s*$")


class MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        amap = {str(k).lower(): str(v) for k, v in attrs if k and v is not None}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = (amap.get("property") or amap.get("name") or "").lower()
            value = amap.get("content")
            if key in {"og:title", "og:description", "description"} and value:
                self.meta[key] = value.strip()[:500]

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join(x.strip() for x in self.title_parts if x.strip())[:500]


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _flashscore_id(ref: dict) -> str | None:
    providers = ref.get("external_providers")
    value = providers.get("flashscoreId") if isinstance(providers, dict) else None
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def parse_exact_result(ref: dict, *, final_url: str, body: bytes) -> dict | None:
    """Parse a final score only from the exact external Flashscore event page.

    Exact identity comes from OddsPapi externalProviders.flashscoreId. Team names
    are never used to discover or fuzzy-match an event. The final URL must carry
    the same `mid` identifier and the page must expose a score suffix in og:title.
    """
    flashscore_id = _flashscore_id(ref)
    fixture_id = ref.get("fixture_id")
    if not flashscore_id or fixture_id is None:
        return None

    query_mid = parse_qs(urlparse(final_url).query).get("mid", [])
    if flashscore_id not in query_mid:
        return None

    parser = MetaParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    og_title = parser.meta.get("og:title")
    if not og_title:
        return None
    match = SCORE_RE.search(og_title)
    if not match:
        return None
    hg, ag = int(match.group(1)), int(match.group(2))
    if hg < 0 or ag < 0 or hg > 30 or ag > 30:
        return None

    # Archive refs are created from OddsPapi finished-fixture discovery. Keep
    # this provider research-only and promotion-disabled even after exact join.
    return {
        "fixture_id": str(fixture_id),
        "ft_home_goals": hg,
        "ft_away_goals": ag,
        "result_source": "FLASHSCORE_EXACT_EXTERNAL_ID_OG_TITLE_FINAL_SCORE",
        "result_identity": "ODDSPAPI_EXTERNALPROVIDERS_FLASHSCOREID_EXACT",
        "provider_event_id": flashscore_id,
        "provider_evidence": {
            "og_title": og_title,
            "page_title": parser.title,
            "og_description": parser.meta.get("og:description"),
        },
        "promotion_eligible": False,
    }


def fetch_exact_result(ref: dict, timeout: int = 20) -> tuple[dict | None, dict]:
    flashscore_id = _flashscore_id(ref)
    if not flashscore_id:
        return None, {"status": "NO_FLASHSCORE_ID"}
    url = f"https://www.flashscore.com/match/{flashscore_id}/"
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(1_000_000)
            meta = {"http_status": int(resp.status), "final_url": resp.geturl()}
            if int(resp.status) != 200:
                return None, meta
            return parse_exact_result(ref, final_url=resp.geturl(), body=body), meta
    except urllib.error.HTTPError as exc:
        return None, {"http_status": int(exc.code), "error": f"HTTPError: {exc}"}
    except Exception as exc:
        return None, {"http_status": None, "error": f"{type(exc).__name__}: {exc}"}


def run_backfill(root: Path = Path("."), *, max_requests: int = 20, sleep_seconds: float = 1.0) -> dict:
    refs = _load_jsonl(root / REFS_PATH)
    existing = {str(x.get("fixture_id")) for x in _load_jsonl(root / RESULTS_PATH) if x.get("fixture_id") is not None}
    candidates = [r for r in refs if _flashscore_id(r) and str(r.get("fixture_id")) not in existing]
    attempted = 0
    normalized: list[dict] = []
    failures: list[dict] = []
    for ref in candidates[:max_requests]:
        attempted += 1
        result, meta = fetch_exact_result(ref)
        if result:
            normalized.append(result)
        else:
            failures.append({"fixture_id": ref.get("fixture_id"), "flashscore_id": _flashscore_id(ref), **meta})
        if sleep_seconds > 0 and attempted < min(max_requests, len(candidates)):
            time.sleep(sleep_seconds)

    added = merge_normalized_results(root / RESULTS_PATH, normalized)
    report = {
        "schema_version": "1.0",
        "classification": "EXACT_ID_RESULT_BACKFILL_RESEARCH_ONLY",
        "provider": "flashscore",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mapping_policy": "ODDSPAPI_EXTERNALPROVIDERS_FLASHSCOREID_EXACT_ONLY",
        "score_policy": "OG_TITLE_SCORE_SUFFIX_FROM_EXACT_EVENT_PAGE",
        "reference_rows": len(refs),
        "eligible_candidates": len(candidates),
        "requests_attempted": attempted,
        "results_parsed": len(normalized),
        "results_added": added,
        "failures": failures[:50],
        "promotion_allowed": False,
        "promotion_blockers": ["ODDSPAPI_HISTORY_NOT_MULTI_SEASON", "FROZEN_VALIDATION_NOT_RUN"],
    }
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(run_backfill())
