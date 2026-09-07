from __future__ import annotations

import csv
import io
import urllib.request
from datetime import date
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/pjc-codes/football-data/main/data/Matches.csv"
BIG5_DIVISIONS = {"E0", "D1", "I1", "SP1", "F1"}


def fetch_big5_bytes(url: str = SOURCE_URL, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "football-odds-scanner/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = r.read()
    if not payload:
        raise ValueError("Empty multi-league dataset response")
    return payload


def _season_code(match_date: str) -> str:
    d = date.fromisoformat(match_date)
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def _f(v: str) -> float:
    x = float(v)
    if x <= 0:
        raise ValueError
    return x


def _valid_asian_grid(line: float) -> bool:
    return abs(line * 4 - round(line * 4)) < 1e-8


def _devig_three(h: float, d: float, a: float) -> tuple[float, float, float]:
    raw = [1 / h, 1 / d, 1 / a]
    s = sum(raw)
    return raw[0] / s, raw[1] / s, raw[2] / s


def normalize_big5_csv(
    payload: bytes,
    *,
    divisions: set[str] | None = None,
    min_season: str = "1920",
    max_season: str = "2425",
) -> list[dict]:
    wanted = divisions or BIG5_DIVISIONS
    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    required = {
        "Division", "MatchDate", "HomeTeam", "AwayTeam", "FTHome", "FTAway",
        "OddHome", "OddDraw", "OddAway", "Over25", "Under25",
        "HandiSize", "HandiHome", "HandiAway",
    }
    if not required.issubset(reader.fieldnames or []):
        missing = sorted(required - set(reader.fieldnames or []))
        raise ValueError(f"Unexpected breadth dataset schema; missing {missing}")

    for r in reader:
        if r.get("Division") not in wanted:
            continue
        try:
            season = _season_code(r["MatchDate"])
            if season < min_season or season > max_season:
                continue
            hg, ag = int(float(r["FTHome"])), int(float(r["FTAway"]))
            h, d, a = _f(r["OddHome"]), _f(r["OddDraw"]), _f(r["OddAway"])
            over, under = _f(r["Over25"]), _f(r["Under25"])
            home_line = float(r["HandiSize"])
            ah_home, ah_away = _f(r["HandiHome"]), _f(r["HandiAway"])
        except (TypeError, ValueError, KeyError):
            continue
        # Some aggregate rows contain synthetic/averaged handicap values such as
        # -2.30. These are not settleable Asian lines. Reject them rather than
        # rounding to a nearby quarter-line, which would manufacture a market.
        if not _valid_asian_grid(home_line):
            continue

        fair_h, _, fair_a = _devig_three(h, d, a)
        if fair_h >= fair_a:
            fav_side = "H"
            fav_prob = fair_h
            fav_line = home_line
            fav_ah_price = ah_home
        else:
            fav_side = "A"
            fav_prob = fair_a
            fav_line = -home_line
            fav_ah_price = ah_away

        rows.append({
            "season": season,
            "division": r["Division"],
            "date": r["MatchDate"],
            "home": r["HomeTeam"],
            "away": r["AwayTeam"],
            "home_goals": hg,
            "away_goals": ag,
            "favorite_side": fav_side,
            "favorite_fair_probability": fav_prob,
            "one_x_two_source": "Bet365",
            "favorite_ah_line": fav_line,
            "favorite_ah_price": fav_ah_price,
            "ah_source": "Bet365",
            "ou_line": 2.5,
            "over_price": over,
            "under_price": under,
            "ou_source": "Bet365",
        })
    return rows


def download_and_normalize_big5(path: Path) -> list[dict]:
    payload = fetch_big5_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return normalize_big5_csv(payload)
