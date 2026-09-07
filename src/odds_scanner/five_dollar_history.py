from __future__ import annotations

from datetime import datetime


def _f(value):
    if isinstance(value, (int, float)) and float(value) > 1.0:
        return float(value)
    raise ValueError("invalid decimal odds")


def _line(value):
    x = float(value)
    if abs(x * 4 - round(x * 4)) > 1e-9:
        raise ValueError("line is not on the Asian quarter grid")
    return x


def _devig_three(home: float, draw: float, away: float) -> tuple[float, float, float]:
    raw = [1.0 / home, 1.0 / draw, 1.0 / away]
    total = sum(raw)
    return raw[0] / total, raw[1] / total, raw[2] / total


def _season_code(kickoff_utc: str) -> str:
    dt = datetime.fromisoformat(kickoff_utc.replace("Z", "+00:00"))
    start = dt.year if dt.month >= 7 else dt.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def normalize_finished_snapshot(fixture: dict, odds_payload: dict, *, bookmaker: str = "bet365") -> dict:
    """Normalize a finished fixture's opening/closing snapshots without inventing tick history."""
    if fixture.get("status") != "finished":
        raise ValueError("historical normalization requires a finished fixture")
    goals = fixture.get("goals") or {}
    if not isinstance(goals.get("home"), (int, float)) or not isinstance(goals.get("away"), (int, float)):
        raise ValueError("finished fixture missing full-time goals")

    data = odds_payload.get("data") or {}
    books = data.get("bookmakers") or []
    book = next((b for b in books if str(b.get("slug", "")).lower() == bookmaker.lower()), None)
    if not isinstance(book, dict):
        raise ValueError("requested bookmaker missing")
    odds = book.get("odds") or {}

    x12 = odds.get("1x2") or {}
    ah = odds.get("asian_handicap") or {}
    ou = odds.get("goal_line") or {}
    x_open, x_close = x12.get("opening") or {}, x12.get("closing") or {}
    ah_open, ah_close = ah.get("opening") or {}, ah.get("closing") or {}
    ou_open, ou_close = ou.get("opening") or {}, ou.get("closing") or {}

    oh, od, oa = _f(x_open.get("home")), _f(x_open.get("draw")), _f(x_open.get("away"))
    ch, cd, ca = _f(x_close.get("home")), _f(x_close.get("draw")), _f(x_close.get("away"))
    fair_h, _, fair_a = _devig_three(oh, od, oa)
    favorite_side = "H" if fair_h >= fair_a else "A"
    favorite_prob = fair_h if favorite_side == "H" else fair_a

    open_home_line = _line(ah_open.get("line"))
    close_home_line = _line(ah_close.get("line"))
    open_home_ah, open_away_ah = _f(ah_open.get("home")), _f(ah_open.get("away"))
    close_home_ah, close_away_ah = _f(ah_close.get("home")), _f(ah_close.get("away"))
    open_ou_line, close_ou_line = _line(ou_open.get("line")), _line(ou_close.get("line"))
    open_over, open_under = _f(ou_open.get("over")), _f(ou_open.get("under"))
    close_over, close_under = _f(ou_close.get("over")), _f(ou_close.get("under"))

    if favorite_side == "H":
        favorite_open_ah_line = open_home_line
        favorite_close_ah_line = close_home_line
        favorite_open_ah_price = open_home_ah
        favorite_close_ah_price = close_home_ah
    else:
        favorite_open_ah_line = -open_home_line
        favorite_close_ah_line = -close_home_line
        favorite_open_ah_price = open_away_ah
        favorite_close_ah_price = close_away_ah

    league = fixture.get("league") or {}
    teams = fixture.get("teams") or {}
    kickoff = str(fixture.get("kickoff_utc") or "")
    return {
        "source": "5dollarfootballapi_snapshot",
        "bookmaker": bookmaker,
        "fixture_id": str(fixture.get("id")),
        "season": _season_code(kickoff),
        "division": str(league.get("name") or league.get("id") or ""),
        "date": datetime.fromisoformat(kickoff.replace("Z", "+00:00")).date().isoformat(),
        "home": str((teams.get("home") or {}).get("name") or ""),
        "away": str((teams.get("away") or {}).get("name") or ""),
        "home_goals": int(goals["home"]),
        "away_goals": int(goals["away"]),
        "favorite_side": favorite_side,
        "favorite_fair_probability": favorite_prob,
        "opening_1x2_home": oh,
        "opening_1x2_draw": od,
        "opening_1x2_away": oa,
        "closing_1x2_home": ch,
        "closing_1x2_draw": cd,
        "closing_1x2_away": ca,
        "favorite_ah_line": favorite_open_ah_line,
        "favorite_ah_price": favorite_open_ah_price,
        "closing_favorite_ah_line": favorite_close_ah_line,
        "closing_favorite_ah_price": favorite_close_ah_price,
        "ah_line_move": favorite_close_ah_line - favorite_open_ah_line,
        "ou_line": open_ou_line,
        "over_price": open_over,
        "under_price": open_under,
        "closing_ou_line": close_ou_line,
        "closing_over_price": close_over,
        "closing_under_price": close_under,
        "ou_line_move": close_ou_line - open_ou_line,
        "one_x_two_source": bookmaker,
        "ah_source": bookmaker,
        "ou_source": bookmaker,
        "snapshot_semantics": "OPENING_AND_LATEST_OR_FINAL_PREMATCH_ONLY_NO_TICKS",
    }
