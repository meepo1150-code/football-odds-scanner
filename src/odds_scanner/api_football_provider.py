from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ENV_KEY = "API_FOOTBALL_KEY"
BASE_URL = "https://v3.football.api-sports.io"
BANGKOK = ZoneInfo("Asia/Bangkok")
BIG5_LEAGUES = {39: "Premier League", 61: "Ligue 1", 78: "Bundesliga", 135: "Serie A", 140: "La Liga"}
FIXTURES_PATH = Path("data/normalized/api_football_fixtures.jsonl")
REPORT_PATH = Path("reports/api_football_shadow_health.json")


def _get(path: str, key: str, params: dict | None = None, timeout: int = 45) -> dict:
    query = f"?{urlencode(params)}" if params else ""
    request = Request(f"{BASE_URL}{path}{query}", headers={"x-apisports-key": key})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_fixture(item: dict, observed_at: str) -> dict | None:
    fixture = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    league = item.get("league") if isinstance(item.get("league"), dict) else {}
    teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
    goals = item.get("goals") if isinstance(item.get("goals"), dict) else {}
    status = fixture.get("status") if isinstance(fixture.get("status"), dict) else {}
    league_id = league.get("id")
    fixture_id = fixture.get("id")
    kickoff = fixture.get("date")
    if league_id not in BIG5_LEAGUES or fixture_id is None or not kickoff:
        return None
    short = str(status.get("short") or "")
    finished = short in {"FT", "AET", "PEN"} and goals.get("home") is not None and goals.get("away") is not None
    return {
        "provider": "api_football",
        "provider_fixture_id": str(fixture_id),
        "league_id": int(league_id),
        "league": str(league.get("name") or BIG5_LEAGUES[league_id]),
        "season": league.get("season"),
        "kickoff": str(kickoff),
        "home": str((teams.get("home") or {}).get("name") or ""),
        "away": str((teams.get("away") or {}).get("name") or ""),
        "status": short,
        "ft_home_goals": int(goals["home"]) if finished else None,
        "ft_away_goals": int(goals["away"]) if finished else None,
        "finished": finished,
        "observed_at": observed_at,
        "identity_semantics": "API_FOOTBALL_PROVIDER_FIXTURE_ID_EXACT",
        "research_only": True,
    }


def _read(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        fixture_id = str(row.get("provider_fixture_id") or "")
        if fixture_id:
            rows[fixture_id] = row
    return rows


def _write(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda row: (row.get("kickoff", ""), row.get("provider_fixture_id", "")))
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in ordered), encoding="utf-8")


def collect(root: Path = Path("."), *, key: str | None = None, today: date | None = None, get_fn=_get) -> dict:
    api_key = (key or os.getenv(ENV_KEY, "")).strip()
    now = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "provider": "api_football",
        "generated_at": now.isoformat(),
        "mode": "SHADOW_FIXTURE_RESULT_ONLY",
        "promotion_eligible": False,
        "odds_ingested": False,
    }
    report_path = root / REPORT_PATH
    if not api_key:
        report.update(status="API_KEY_NOT_CONFIGURED", requests_used=0)
    else:
        local_day = today or now.astimezone(BANGKOK).date()
        days = [local_day - timedelta(days=1), local_day]
        existing = _read(root / FIXTURES_PATH)
        selected: list[dict] = []
        errors: list[str] = []
        current = limit = None
        for day in days:
            try:
                payload = get_fn("/fixtures", api_key, {"date": day.isoformat(), "timezone": "Asia/Bangkok"})
                request_info = payload.get("results")
                response_rows = payload.get("response") if isinstance(payload.get("response"), list) else []
                api_errors = payload.get("errors")
                if api_errors:
                    errors.append(f"{day.isoformat()}:API_ERRORS:{api_errors}")
                for item in response_rows:
                    row = normalize_fixture(item, now.isoformat())
                    if row:
                        selected.append(row)
            except Exception as exc:
                errors.append(f"{day.isoformat()}:{type(exc).__name__}:{exc}")
        try:
            status_payload = get_fn("/status", api_key)
            account = status_payload.get("response") if isinstance(status_payload.get("response"), dict) else {}
            requests = account.get("requests") if isinstance(account.get("requests"), dict) else {}
            current, limit = requests.get("current"), requests.get("limit_day")
        except Exception as exc:
            errors.append(f"STATUS:{type(exc).__name__}:{exc}")
        for row in selected:
            existing[row["provider_fixture_id"]] = row
        _write(root / FIXTURES_PATH, existing)
        report.update(
            status="SHADOW_OK" if selected and not errors else ("SHADOW_PARTIAL" if selected else "SHADOW_FAILED"),
            requests_used=3,
            dates=[day.isoformat() for day in days],
            big5_rows_observed=len(selected),
            finished_rows_observed=sum(1 for row in selected if row["finished"]),
            persisted_rows=len(existing),
            request_count=current,
            request_limit_day=limit,
            request_remaining=(limit - current) if isinstance(limit, int) and isinstance(current, int) else None,
            errors=errors,
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(collect(), ensure_ascii=False))
