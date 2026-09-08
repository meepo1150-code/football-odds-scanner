from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from .market_contract import CurrentMarket
from .oddspapi_big5 import _parse_dt, select_big5_tournaments
from .oddspapi_discovery import DEFAULT_REQUEST_SPACING_SECONDS, _rows
from .oddspapi_provider import ENV_KEY, SPORT_ID, _get, parse_fixture_markets


class OddsPapiCurrentProvider:
    """Quota-aware Bet365 Big-5 current execution provider.

    The production scanner calls this provider only after the validated-pattern
    registry has been loaded and found non-empty. A normal fetch uses exactly
    three provider requests: market catalog, tournament catalog, and one
    multi-tournament Bet365 current-odds batch.
    """

    provider_id = "oddspapi_free:bet365:big5_current"

    def __init__(
        self,
        *,
        horizon_days: int = 7,
        request_spacing_seconds: float = DEFAULT_REQUEST_SPACING_SECONDS,
        sleep_fn: Callable[[float], None] = time.sleep,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        if horizon_days < 1:
            raise ValueError("horizon_days must be >= 1")
        if request_spacing_seconds < 0:
            raise ValueError("request_spacing_seconds must be non-negative")
        self.horizon_days = horizon_days
        self.request_spacing_seconds = request_spacing_seconds
        self.sleep_fn = sleep_fn
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def fetch(self) -> list[CurrentMarket]:
        key = os.getenv(ENV_KEY)
        if not key:
            raise RuntimeError(f"GitHub secret {ENV_KEY} is required when validated patterns exist")

        now = self.now_fn()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        now = now.astimezone(timezone.utc)
        end = now + timedelta(days=self.horizon_days)

        first = True

        def paced_get(path: str, params: dict | None = None):
            nonlocal first
            if not first and self.request_spacing_seconds:
                self.sleep_fn(self.request_spacing_seconds)
            first = False
            return _get(path, key, params)

        catalog = _rows(paced_get("/markets", {"language": "en"}))
        tournaments = _rows(paced_get("/tournaments", {"sportId": SPORT_ID, "language": "en"}))
        selected = select_big5_tournaments(tournaments)
        if len(selected) != 5:
            found = sorted(str(r.get("categoryName") or "") for r in selected)
            raise RuntimeError(f"OddsPapi Big-5 tournament discovery incomplete: found={found}")

        ids = ",".join(str(r["tournamentId"]) for r in selected)
        batch = _rows(
            paced_get(
                "/odds-by-tournaments",
                {
                    "tournamentIds": ids,
                    "bookmakers": "bet365",
                    "language": "en",
                    "verbosity": 3,
                },
            )
        )

        eligible: list[dict] = []
        for fixture in batch:
            start = _parse_dt(fixture.get("startTime"))
            if start is None or start < now or start > end:
                continue
            if int(fixture.get("statusId", -1)) != 0 or fixture.get("hasOdds") is not True:
                continue
            eligible.append(fixture)
        eligible.sort(key=lambda f: str(f.get("startTime") or ""))

        normalized: list[CurrentMarket] = []
        for fixture in eligible:
            normalized.extend(parse_fixture_markets(fixture, fixture, catalog, now=now))
        return normalized
