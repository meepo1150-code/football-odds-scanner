from __future__ import annotations

import csv
import html
import io
import json
import re
import urllib.request
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DATA_PAGE = "https://sgodds.com/football/data"
BASE = "https://sgodds.com"
DOWNLOAD_RE = re.compile(r'href=["\'](?P<href>/downloads/sgodds-\d+-(?P<slug>[a-z0-9-]+)\.csv)["\']', re.I)
VS_RE = re.compile(r"\s+vs\.?\s+", re.I)
USER_AGENT = "football-odds-scanner/0.1 personal-research"


@dataclass(frozen=True)
class CurrentMarket:
    source: str
    league: str
    date: str
    kickoff: str
    home: str
    away: str
    ah_home_line: float | None
    ah_home_odds: float | None
    ah_away_line: float | None
    ah_away_odds: float | None
    ou_line: float | None
    over_odds: float | None
    under_odds: float | None
    one_x_two_home: float | None
    one_x_two_draw: float | None
    one_x_two_away: float | None


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/csv,*/*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _num(value) -> float | None:
    if value is None:
        return None
    try:
        v = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return v


def _valid_odds(value) -> float | None:
    v = _num(value)
    return v if v is not None and v > 1.0 else None


def _quarter_grid(value: float | None) -> bool:
    if value is None:
        return False
    return abs(value * 4 - round(value * 4)) < 1e-9


def two_way_fair_probs(a_odds: float, b_odds: float) -> tuple[float, float, float]:
    ia, ib = 1.0 / a_odds, 1.0 / b_odds
    total = ia + ib
    return ia / total, ib / total, total - 1.0


def enumerate_downloads(page_html: str | None = None) -> dict[str, str]:
    if page_html is None:
        page_html = _get(DATA_PAGE).decode("utf-8", errors="replace")
    found: dict[str, str] = {}
    for match in DOWNLOAD_RE.finditer(html.unescape(page_html)):
        found[match.group("slug")] = BASE + match.group("href")
    if not found:
        raise RuntimeError("sgodds data page exposed no CSV download links")
    return found


def parse_csv(payload: bytes | str, league: str) -> list[CurrentMarket]:
    text = payload.decode("utf-8-sig", errors="replace") if isinstance(payload, bytes) else payload
    rows = csv.DictReader(io.StringIO(text))
    out: list[CurrentMarket] = []
    for row in rows:
        match = str(row.get("Match", "")).strip()
        teams = VS_RE.split(match, maxsplit=1)
        if len(teams) != 2:
            continue
        home, away = teams[0].strip(), teams[1].strip()
        start = str(row.get("Start Time", "")).strip()
        date, kickoff = "", ""
        if start:
            parts = start.split()
            date = parts[0] if parts else ""
            kickoff = parts[1][:5] if len(parts) > 1 else ""

        ah_home_line = _num(row.get("Ah_01_Hcap"))
        ah_away_line = _num(row.get("Ah_02_Hcap"))
        ou_line = _num(row.get("Ou_hcap"))
        # Never coerce malformed Asian lines into a valid market.
        if ah_home_line is not None and not _quarter_grid(ah_home_line):
            ah_home_line = None
        if ah_away_line is not None and not _quarter_grid(ah_away_line):
            ah_away_line = None
        if ou_line is not None and not _quarter_grid(ou_line):
            ou_line = None

        out.append(CurrentMarket(
            source="sgodds_singapore_pools_open",
            league=league,
            date=date,
            kickoff=kickoff,
            home=home,
            away=away,
            ah_home_line=ah_home_line,
            ah_home_odds=_valid_odds(row.get("Ah_01")),
            ah_away_line=ah_away_line,
            ah_away_odds=_valid_odds(row.get("Ah_02")),
            ou_line=ou_line,
            over_odds=_valid_odds(row.get("Ou_01")),
            under_odds=_valid_odds(row.get("Ou_02")),
            one_x_two_home=_valid_odds(row.get("Ft1X2_01")),
            one_x_two_draw=_valid_odds(row.get("Ft1X2_02")),
            one_x_two_away=_valid_odds(row.get("Ft1X2_03")),
        ))
    return out


def fetch_current_markets(limit_leagues: int | None = None) -> list[CurrentMarket]:
    downloads = enumerate_downloads()
    items = list(downloads.items())
    if limit_leagues is not None:
        items = items[:limit_leagues]
    markets: list[CurrentMarket] = []
    for league, url in items:
        markets.extend(parse_csv(_get(url), league))
    return markets


def capability_summary(markets: Iterable[CurrentMarket]) -> dict:
    rows = list(markets)
    ou_lines = Counter(m.ou_line for m in rows if m.ou_line is not None)
    ah_lines = Counter(m.ah_home_line for m in rows if m.ah_home_line is not None)
    tradable_ou = sum(
        1 for m in rows
        if m.ou_line is not None and m.over_odds is not None and m.under_odds is not None
    )
    tradable_ah = sum(
        1 for m in rows
        if m.ah_home_line is not None and m.ah_home_odds is not None and m.ah_away_odds is not None
    )
    return {
        "schema_version": "1.0",
        "provider": "sgodds_singapore_pools_open",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "leagues": sorted({m.league for m in rows}),
        "tradable_ah_rows": tradable_ah,
        "tradable_ou_rows": tradable_ou,
        "ah_lines": {str(k): v for k, v in sorted(ah_lines.items())},
        "ou_lines": {str(k): v for k, v in sorted(ou_lines.items())},
        "alternate_ou_rows": sum(v for k, v in ou_lines.items() if k != 2.5),
        "quarter_ou_rows": sum(v for k, v in ou_lines.items() if abs(k * 2 - round(k * 2)) > 1e-9),
        "archive_policy": "No raw third-party odds are committed by this health check.",
    }


def write_health(root: Path, limit_leagues: int | None = None) -> dict:
    summary = capability_summary(fetch_current_markets(limit_leagues=limit_leagues))
    path = root / "reports/current_provider_health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    print(json.dumps(write_health(Path("."))))


if __name__ == "__main__":
    main()
