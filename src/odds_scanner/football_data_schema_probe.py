from __future__ import annotations

import csv
import io
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPORT_PATH = Path("reports/football_data_schema_probe.json")
BASE = "https://www.football-data.co.uk/mmz4281/{season}/{division}.csv"
DIVISIONS = {"E0": "Premier League", "D1": "Bundesliga", "I1": "Serie A", "SP1": "LaLiga", "F1": "Ligue 1"}
SEASONS = ("1920", "2021", "2122", "2223", "2324", "2425", "2526")
KEY_COLUMNS = (
    "FTHG", "FTAG", "FTR",
    "AvgH", "AvgD", "AvgA", "MaxH", "MaxD", "MaxA",
    "Avg>2.5", "Avg<2.5", "Max>2.5", "Max<2.5",
    "AHh", "AvgAHH", "AvgAHA", "MaxAHH", "MaxAHA",
    "AvgCH", "AvgCD", "AvgCA", "MaxCH", "MaxCD", "MaxCA",
    "AvgC>2.5", "AvgC<2.5", "MaxC>2.5", "MaxC<2.5",
    "AHCh", "AvgCAHH", "AvgCAHA", "MaxCAHH", "MaxCAHA",
)
USER_AGENT = "football-odds-scanner/0.1 research schema probe"


def fetch_csv(url: str, timeout: int = 30) -> tuple[list[str], list[dict[str, str]]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(4_000_000)
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    rows = [dict(r) for r in reader if isinstance(r, dict)]
    return headers, rows


def inspect_dataset(headers: list[str], rows: list[dict[str, str]]) -> dict:
    hset = set(headers)
    present = [c for c in KEY_COLUMNS if c in hset]
    nonempty = {c: sum(bool((r.get(c) or "").strip()) for r in rows) for c in present}
    ah_lines = sorted({(r.get("AHh") or "").strip() for r in rows if (r.get("AHh") or "").strip()})
    ahc_lines = sorted({(r.get("AHCh") or "").strip() for r in rows if (r.get("AHCh") or "").strip()})
    return {
        "rows": len(rows),
        "headers": headers,
        "key_columns_present": present,
        "key_nonempty_counts": nonempty,
        "ah_early_unique_lines": ah_lines[:100],
        "ah_closing_unique_lines": ahc_lines[:100],
        "has_early_1x2": all(c in hset for c in ("AvgH", "AvgD", "AvgA")),
        "has_closing_1x2": all(c in hset for c in ("AvgCH", "AvgCD", "AvgCA")),
        "has_early_ou25": all(c in hset for c in ("Avg>2.5", "Avg<2.5")),
        "has_closing_ou25": all(c in hset for c in ("AvgC>2.5", "AvgC<2.5")),
        "has_early_ah": all(c in hset for c in ("AHh", "AvgAHH", "AvgAHA")),
        "has_closing_ah": all(c in hset for c in ("AHCh", "AvgCAHH", "AvgCAHA")),
    }


def run_probe(root: Path = Path(".")) -> dict:
    datasets: list[dict] = []
    for season in SEASONS:
        for division, league in DIVISIONS.items():
            url = BASE.format(season=season, division=division)
            item = {"season": season, "division": division, "league": league, "url": url}
            try:
                headers, rows = fetch_csv(url)
                item.update({"status": "OK", **inspect_dataset(headers, rows)})
            except urllib.error.HTTPError as exc:
                item.update({"status": "HTTP_ERROR", "http_status": int(exc.code)})
            except Exception as exc:
                item.update({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
            datasets.append(item)

    ok = [d for d in datasets if d.get("status") == "OK"]
    complete_six_market = [d for d in ok if all(d.get(k) for k in (
        "has_early_1x2", "has_closing_1x2", "has_early_ou25", "has_closing_ou25", "has_early_ah", "has_closing_ah"
    ))]
    report = {
        "schema_version": "1.0",
        "classification": "FOOTBALL_DATA_MULTI_SEASON_SCHEMA_PROBE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "football-data.co.uk",
        "source_semantics": {
            "early": "FOOTBALL_DATA_FIRST_COLLECTED_AFTER_MARKET_OPENING_NOT_TRUE_OPEN",
            "closing": "FOOTBALL_DATA_CLOSING_C_COLUMNS",
        },
        "promotion_allowed": False,
        "datasets_attempted": len(datasets),
        "datasets_ok": len(ok),
        "datasets_with_early_and_closing_1x2_ou25_ah": len(complete_six_market),
        "datasets": datasets,
    }
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run_probe()
    print({k: result[k] for k in ("datasets_attempted", "datasets_ok", "datasets_with_early_and_closing_1x2_ou25_ah", "promotion_allowed")})
