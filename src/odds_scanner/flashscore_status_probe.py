from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .flashscore_exact_probe import first_flashscore_ref
from .flashscore_structured_probe import fetch_event, inspect_html

REPORT_PATH = Path("reports/flashscore_explicit_status_score_probe.json")

# Conservative key/value forms only. We report extracted scalar values, never raw HTML.
_STATUS_PATTERNS = [
    re.compile(r'"eventStatus"\s*:\s*"([^"\\]{1,80})"', re.I),
    re.compile(r'\\"eventStatus\\"\s*:\s*\\"([^"\\]{1,80})\\"', re.I),
    re.compile(r'eventStatus\s*[:=]\s*["\']([^"\']{1,80})["\']', re.I),
]


def extract_event_status_values(body: bytes) -> list[str]:
    text = body.decode("utf-8", errors="replace")
    values: list[str] = []
    for pattern in _STATUS_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if value and value not in values:
                values.append(value)
    return values[:20]


def extract_og_title_score(evidence: dict) -> dict | None:
    for item in evidence.get("meta") or []:
        if str(item.get("name") or "").lower() != "og:title":
            continue
        content = str(item.get("content") or "").strip()
        # Score must be the final terminal token pair in the title.
        match = re.search(r'(?<!\d)(\d{1,2})\s*[-:]\s*(\d{1,2})\s*$', content)
        if not match:
            continue
        return {
            "home_goals": int(match.group(1)),
            "away_goals": int(match.group(2)),
            "source": "FLASHSCORE_OG_TITLE_TERMINAL_SCORE",
            "title": content[:300],
        }
    return None


def run_probe(root: Path = Path(".")) -> dict:
    ref = first_flashscore_ref(root)
    report = {
        "schema_version": "1.0",
        "classification": "EXACT_ID_EXPLICIT_STATUS_SCORE_PROBE",
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
            statuses = extract_event_status_values(body)
            score = extract_og_title_score(evidence)
            report.update({
                "event_status_values": statuses,
                "explicit_score": score,
                "status": "EXPLICIT_STATUS_AND_SCORE" if statuses and score else (
                    "SCORE_WITHOUT_EXPLICIT_STATUS" if score else "NO_EXPLICIT_RESULT_CONTRACT"
                ),
            })
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(run_probe())
