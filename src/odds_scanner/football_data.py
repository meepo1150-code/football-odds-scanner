from __future__ import annotations
import csv, io, json, time, urllib.error, urllib.request
from pathlib import Path

BASE = "https://www.football-data.co.uk"
FIXTURES_URL = f"{BASE}/matches/resources/fixtures.csv"
MIRROR_URL = "https://raw.githubusercontent.com/AnishKhetani/premier-league-data/main/data/processed/results_with_odds.csv"
SEASONS = ["1617","1718","1819","1920","2021","2122","2223","2324","2425","2526"]

def season_url(code: str, division: str = "E0") -> str:
    return f"{BASE}/mmz4281/{code}/{division}.csv"

def fetch_bytes(url: str, timeout: int = 30, attempts: int = 5) -> bytes:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/152 Safari/537.36",
        "Accept": "text/csv,text/plain,*/*",
        "Cache-Control": "no-cache",
    }
    if url.startswith(BASE):
        headers["Referer"] = f"{BASE}/"
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
                if not payload:
                    raise ValueError(f"Empty response from {url}")
                return payload
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt == attempts:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt == attempts:
                raise
        time.sleep(min(2 ** (attempt - 1), 16))
    raise RuntimeError(f"Unable to fetch {url}: {last_error}")

def decode_csv(raw: bytes) -> list[dict[str,str]]:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Unable to decode CSV")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("CSV contains no data rows")
    return rows

def _write_raw_like(rows: list[dict[str, str]], path: Path) -> None:
    fields = ["Div","Date","HomeTeam","AwayTeam","FTR","AvgH","AvgD","AvgA","B365H","B365D","B365A","AvgCH","AvgCD","AvgCA","B365CH","B365CD","B365CA"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def _download_history_mirror(out_dir: Path, seasons: list[str], division: str) -> list[Path]:
    if division != "E0":
        raise ValueError("GitHub mirror fallback currently supports E0 only")
    payload = fetch_bytes(MIRROR_URL, attempts=3)
    source_rows = decode_csv(payload)
    by_season: dict[str, list[dict[str, str]]] = {s: [] for s in seasons}
    for r in source_rows:
        code = (r.get("season_code") or "").strip()
        if code not in by_season:
            continue
        mapped = {
            "Div": "E0",
            "Date": r.get("date", ""),
            "HomeTeam": r.get("home_team", ""),
            "AwayTeam": r.get("away_team", ""),
            "FTR": r.get("ftr", ""),
            "AvgH": r.get("market_avg_1x2_home", ""),
            "AvgD": r.get("market_avg_1x2_draw", ""),
            "AvgA": r.get("market_avg_1x2_away", ""),
            "B365H": r.get("bet365_1x2_home", ""),
            "B365D": r.get("bet365_1x2_draw", ""),
            "B365A": r.get("bet365_1x2_away", ""),
            "AvgCH": r.get("market_avg_1x2_home_close", ""),
            "AvgCD": r.get("market_avg_1x2_draw_close", ""),
            "AvgCA": r.get("market_avg_1x2_away_close", ""),
            "B365CH": r.get("bet365_1x2_home_close", ""),
            "B365CD": r.get("bet365_1x2_draw_close", ""),
            "B365CA": r.get("bet365_1x2_away_close", ""),
        }
        if mapped["HomeTeam"] and mapped["AwayTeam"] and mapped["FTR"] in {"H","D","A"}:
            by_season[code].append(mapped)
    paths: list[Path] = []
    for s in seasons:
        rows = by_season[s]
        if len(rows) < 300:
            raise ValueError(f"Mirror season {s} is incomplete: {len(rows)} rows")
        p = out_dir / f"{division}_{s}.csv"
        _write_raw_like(rows, p)
        paths.append(p)
    (out_dir / "provenance.json").write_text(json.dumps({
        "historical_source": "github_mirror",
        "mirror_url": MIRROR_URL,
        "upstream_source": BASE,
        "seasons": seasons,
    }, indent=2), encoding="utf-8")
    return paths

def download_history(out_dir: Path, seasons: list[str] | None = None, division: str = "E0") -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = list(seasons or SEASONS)
    paths=[]
    try:
        for s in wanted:
            p=out_dir / f"{division}_{s}.csv"
            payload = fetch_bytes(season_url(s, division), attempts=2)
            rows = decode_csv(payload)
            if not rows or "HomeTeam" not in rows[0] or "AwayTeam" not in rows[0]:
                raise ValueError(f"Unexpected Football-Data schema for season {s}")
            p.write_bytes(payload)
            paths.append(p)
        (out_dir / "provenance.json").write_text(json.dumps({
            "historical_source": "football-data.co.uk",
            "upstream_source": BASE,
            "seasons": wanted,
        }, indent=2), encoding="utf-8")
        return paths
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError):
        for p in paths:
            p.unlink(missing_ok=True)
        return _download_history_mirror(out_dir, wanted, division)

def download_fixtures(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = fetch_bytes(FIXTURES_URL)
    decode_csv(payload)
    path.write_bytes(payload)
    return path
