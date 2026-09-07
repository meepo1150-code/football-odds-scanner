from __future__ import annotations
import csv, io, time, urllib.error, urllib.request
from pathlib import Path

BASE = "https://www.football-data.co.uk"
FIXTURES_URL = f"{BASE}/matches/resources/fixtures.csv"
SEASONS = ["1617","1718","1819","1920","2021","2122","2223","2324","2425","2526"]

def season_url(code: str, division: str = "E0") -> str:
    return f"{BASE}/mmz4281/{code}/{division}.csv"

def fetch_bytes(url: str, timeout: int = 30, attempts: int = 5) -> bytes:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/152 Safari/537.36",
        "Accept": "text/csv,text/plain,*/*",
        "Referer": f"{BASE}/",
        "Cache-Control": "no-cache",
    }
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

def download_history(out_dir: Path, seasons: list[str] | None = None, division: str = "E0") -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths=[]
    for s in seasons or SEASONS:
        p=out_dir / f"{division}_{s}.csv"
        payload = fetch_bytes(season_url(s, division))
        rows = decode_csv(payload)
        if not rows or "HomeTeam" not in rows[0] or "AwayTeam" not in rows[0]:
            raise ValueError(f"Unexpected Football-Data schema for season {s}")
        p.write_bytes(payload)
        paths.append(p)
    return paths

def download_fixtures(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = fetch_bytes(FIXTURES_URL)
    decode_csv(payload)
    path.write_bytes(payload)
    return path
