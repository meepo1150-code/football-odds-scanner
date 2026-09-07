from __future__ import annotations
import csv, io, urllib.request
from pathlib import Path

BASE = "https://www.football-data.co.uk"
FIXTURES_URL = f"{BASE}/matches/resources/fixtures.csv"
SEASONS = ["1617","1718","1819","1920","2021","2122","2223","2324","2425","2526"]

def season_url(code: str, division: str = "E0") -> str:
    return f"{BASE}/mmz4281/{code}/{division}.csv"

def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "football-odds-scanner/0.1 personal research"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def decode_csv(raw: bytes) -> list[dict[str,str]]:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Unable to decode CSV")
    return list(csv.DictReader(io.StringIO(text)))

def download_history(out_dir: Path, seasons: list[str] | None = None, division: str = "E0") -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths=[]
    for s in seasons or SEASONS:
        p=out_dir / f"{division}_{s}.csv"
        p.write_bytes(fetch_bytes(season_url(s, division)))
        paths.append(p)
    return paths

def download_fixtures(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(fetch_bytes(FIXTURES_URL))
    return path
