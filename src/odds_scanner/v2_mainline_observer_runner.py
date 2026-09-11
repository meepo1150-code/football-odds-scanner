from __future__ import annotations

import json
import time
from collections.abc import Callable

from . import v2_mainline_observer as observer
from .oddspapi_provider import _get as raw_get

ODDS_BATCH_MIN_COOLDOWN_SECONDS = 1.25


def make_paced_get(
    delegate: Callable,
    *,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    minimum_cooldown_seconds: float = ODDS_BATCH_MIN_COOLDOWN_SECONDS,
):
    """Pace repeated /odds-by-tournaments calls after the previous call completes.

    OddsPapi documents a 1000ms endpoint cooldown.  We use 1.25s to leave a
    deterministic safety margin without adding any request or retry.
    """
    last_finished: float | None = None

    def paced(path: str, key: str, params: dict | None = None, timeout: int = 20):
        nonlocal last_finished
        if path == "/odds-by-tournaments" and last_finished is not None:
            remaining = minimum_cooldown_seconds - (clock() - last_finished)
            if remaining > 0:
                sleeper(remaining)
        try:
            return delegate(path, key, params, timeout)
        finally:
            if path == "/odds-by-tournaments":
                last_finished = clock()

    return paced


def observe_with_rate_limit_safety():
    original = observer._get
    observer._get = make_paced_get(raw_get)
    try:
        report = observer.observe_from_env()
        if isinstance(report, dict):
            report["odds_batch_min_cooldown_seconds"] = ODDS_BATCH_MIN_COOLDOWN_SECONDS
            report["odds_batch_rate_limit_policy"] = "WAIT_AFTER_PREVIOUS_ODDS_BY_TOURNAMENTS_COMPLETES_NO_AUTOMATIC_RETRY"
            path = observer.REPORT_PATH
            if path.exists():
                path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        observer._get = original


if __name__ == "__main__":
    print(json.dumps(observe_with_rate_limit_safety(), ensure_ascii=False))
