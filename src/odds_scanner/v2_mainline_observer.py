from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, SPORT_ID, _catalog, _get, _outcome_lookup, _player, _quarter

CATALOG_PATH = Path("data/normalized/oddspapi_market_catalog.json")
CANDIDATE_PATH = Path("reports/v2_research_candidates.json")
TARGETS_PATH = Path("reports/v2_target_tournaments.json")
SNAPSHOTS_PATH = Path("data/normalized/v2_mainline_snapshots.jsonl")
REPORT_PATH = Path("reports/v2_mainline_observer.json")

TARGETS = {
    "BIG5_AH": {
        "England": {"premier league", "premier-league"},
        "France": {"ligue 1", "ligue-1"},
        "Germany": {"bundesliga"},
        "Italy": {"serie a", "serie-a"},
        "Spain": {"laliga", "la liga", "la-liga"},
    },
    "THIRD_UNIVERSE_OU": {
        "Netherlands": {"eredivisie"},
        "Portugal": {"liga portugal", "liga-portugal", "primeira liga", "primeira-liga"},
        "Belgium": {"pro league", "pro-league", "jupiler pro league", "jupiler-pro-league"},
        "Turkey": {"super lig", "super-lig", "süper lig", "süper-lig"},
        "Scotland": {"premiership", "scottish premiership", "scottish-premiership"},
    },
}

BATCH_ORDER = ("BIG5_AH", "THIRD_UNIVERSE_OU")


def _norm(value) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", "-").split())


def _utc(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def select_target_tournaments(rows: list[dict]) -> list[dict]:
    selected: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for universe, countries in TARGETS.items():
        for country, aliases in countries.items():
            matches = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                provider_country = str(row.get("categoryName") or "")
                accepted_countries = {country}
                if country == "Turkey":
                    accepted_countries.add("Turkiye")
                if provider_country not in accepted_countries:
                    continue
                name = _norm(row.get("tournamentName"))
                slug = _norm(row.get("tournamentSlug"))
                if name in aliases or slug in aliases:
                    matches.append(row)
            if len(matches) != 1 or matches[0].get("tournamentId") is None:
                continue
            row = matches[0]
            key = (universe, country)
            if key in seen:
                continue
            seen.add(key)
            selected.append({
                "universe": universe,
                "country": country,
                "provider_category": row.get("categoryName"),
                "tournament_id": int(row["tournamentId"]),
                "tournament_name": row.get("tournamentName"),
                "tournament_slug": row.get("tournamentSlug"),
            })
    selected.sort(key=lambda x: (x["universe"], x["country"]))
    return selected


def targets_complete(selected: list[dict]) -> bool:
    expected = {(u, c) for u, countries in TARGETS.items() for c in countries}
    actual = {(str(x.get("universe")), str(x.get("country"))) for x in selected}
    return actual == expected


def split_target_batches(selected: list[dict]) -> list[tuple[str, list[dict]]]:
    batches: list[tuple[str, list[dict]]] = []
    for universe in BATCH_ORDER:
        rows = [x for x in selected if x.get("universe") == universe]
        rows.sort(key=lambda x: str(x.get("country") or ""))
        if len(rows) != 5:
            raise ValueError(f"{universe} requires exactly 5 locked tournaments; found {len(rows)}")
        batches.append((universe, rows))
    return batches


def _active_player(outcome: dict | None) -> dict | None:
    if not isinstance(outcome, dict):
        return None
    p = _player(outcome)
    return p if p and p.get("active") is True else None


def _market_selections(meta: dict, market_data: dict) -> dict[str, dict]:
    names = _outcome_lookup(meta)
    selections: dict[str, dict] = {}
    for outcome_id, outcome in (market_data.get("outcomes") or {}).items():
        p = _active_player(outcome)
        label = names.get(str(outcome_id), "").strip().lower()
        if p and label:
            selections[label] = p
    return selections


def _fair_1x2(home: float, draw: float, away: float) -> tuple[float, float, float]:
    inv = (1.0 / home, 1.0 / draw, 1.0 / away)
    total = sum(inv)
    return tuple(x / total for x in inv)  # type: ignore[return-value]


def mainline_shape(fixture: dict, markets_catalog: list[dict], *, bookmaker: str = "bet365") -> dict:
    """Describe current full-time AH/O/U mainLine cardinality without choosing a line."""
    book = (fixture.get("bookmakerOdds") or {}).get(bookmaker)
    if not isinstance(book, dict):
        return {"ah_main_count": 0, "ou_main_count": 0, "ah_lines": [], "ou_lines": []}
    catalog = _catalog(markets_catalog)
    ah_lines: list[float] = []
    ou_lines: list[float] = []
    for market_id, market_data in (book.get("markets") or {}).items():
        meta = catalog.get(str(market_id))
        if not isinstance(meta, dict) or not isinstance(market_data, dict) or market_data.get("marketActive") is not True:
            continue
        selections = _market_selections(meta, market_data)
        mname = str(meta.get("marketName") or "").lower()
        mtype = str(meta.get("marketType") or "").lower()
        line = _quarter(meta.get("handicap"))
        if line is None:
            continue
        if "asian handicap" in mname:
            hp = selections.get("home") or selections.get("1")
            ap = selections.get("away") or selections.get("2")
            if hp and ap and hp.get("mainLine") is True and ap.get("mainLine") is True:
                ah_lines.append(float(line))
            continue
        if mname == "over under full time" or (mtype == "totals" and str(meta.get("period") or "").lower() == "fulltime" and "team" not in mname and "corner" not in mname):
            op, up = selections.get("over"), selections.get("under")
            if op and up and op.get("mainLine") is True and up.get("mainLine") is True:
                ou_lines.append(float(line))
    return {
        "ah_main_count": len(ah_lines),
        "ou_main_count": len(ou_lines),
        "ah_lines": sorted(ah_lines),
        "ou_lines": sorted(ou_lines),
    }


def extract_mainline_snapshot(
    fixture: dict,
    markets_catalog: list[dict],
    *,
    observed_at: datetime,
    tournament_meta: dict | None = None,
    bookmaker: str = "bet365",
) -> tuple[dict | None, str]:
    if int(fixture.get("statusId", -1)) != 0 or fixture.get("hasOdds") is not True:
        return None, "NOT_PREMATCH_WITH_ODDS"
    kickoff = _utc(fixture.get("startTime"))
    if kickoff is None or kickoff <= observed_at.astimezone(timezone.utc):
        return None, "KICKOFF_NOT_FUTURE"

    book = (fixture.get("bookmakerOdds") or {}).get(bookmaker)
    if not isinstance(book, dict) or book.get("bookmakerIsActive") is not True or book.get("suspended") is not False:
        return None, "BOOKMAKER_NOT_ACTIVE"

    catalog = _catalog(markets_catalog)
    one_x_two: list[dict] = []
    ah_main: list[dict] = []
    ou_main: list[dict] = []
    for market_id, market_data in (book.get("markets") or {}).items():
        meta = catalog.get(str(market_id))
        if not isinstance(meta, dict) or not isinstance(market_data, dict) or market_data.get("marketActive") is not True:
            continue
        selections = _market_selections(meta, market_data)
        mname = str(meta.get("marketName") or "").lower()
        mtype = str(meta.get("marketType") or "").lower()
        if mtype == "1x2" and {"1", "x", "2"}.issubset(selections):
            one_x_two.append({"home": selections["1"], "draw": selections["x"], "away": selections["2"]})
            continue
        line = _quarter(meta.get("handicap"))
        if line is None:
            continue
        if "asian handicap" in mname:
            hp = selections.get("home") or selections.get("1")
            ap = selections.get("away") or selections.get("2")
            if hp and ap and hp.get("mainLine") is True and ap.get("mainLine") is True:
                ah_main.append({"line": line, "home": hp, "away": ap})
            continue
        if mname == "over under full time" or (mtype == "totals" and str(meta.get("period") or "").lower() == "fulltime" and "team" not in mname and "corner" not in mname):
            op, up = selections.get("over"), selections.get("under")
            if op and up and op.get("mainLine") is True and up.get("mainLine") is True:
                ou_main.append({"line": line, "over": op, "under": up})

    if len(one_x_two) != 1:
        return None, "AMBIGUOUS_OR_MISSING_1X2"
    if len(ah_main) != 1:
        return None, "AMBIGUOUS_OR_MISSING_MAIN_AH"
    if len(ou_main) != 1:
        return None, "AMBIGUOUS_OR_MISSING_MAIN_OU"

    one, ah, ou = one_x_two[0], ah_main[0], ou_main[0]
    hp, dp, ap = float(one["home"]["price"]), float(one["draw"]["price"]), float(one["away"]["price"])
    fh, fd, fa = _fair_1x2(hp, dp, ap)
    favorite_side = "H" if fh >= fa else "A"
    favorite_probability = fh if favorite_side == "H" else fa
    selected_ah_line = float(ah["line"]) if favorite_side == "H" else -float(ah["line"])
    selected_ah_price = float(ah["home"]["price"]) if favorite_side == "H" else float(ah["away"]["price"])
    selected_ah_opposite_price = float(ah["away"]["price"]) if favorite_side == "H" else float(ah["home"]["price"])

    tmeta = tournament_meta or {}
    return {
        "fixture_id": fixture.get("fixtureId"),
        "tournament_id": fixture.get("tournamentId"),
        "universe": tmeta.get("universe"),
        "league": tmeta.get("tournament_name") or fixture.get("tournamentName") or fixture.get("tournamentSlug"),
        "country": tmeta.get("country"),
        "kickoff": kickoff.isoformat(),
        "home": fixture.get("participant1Name"),
        "away": fixture.get("participant2Name"),
        "bookmaker": bookmaker,
        "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
        "source_semantics": "CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED",
        "mainline_verified": True,
        "favorite_side": favorite_side,
        "favorite_fair_probability": round(favorite_probability, 8),
        "one_x_two": {"home": hp, "draw": dp, "away": ap, "fair_home": round(fh, 8), "fair_draw": round(fd, 8), "fair_away": round(fa, 8)},
        "ah": {
            "home_line": float(ah["line"]),
            "home_price": float(ah["home"]["price"]),
            "away_line": -float(ah["line"]),
            "away_price": float(ah["away"]["price"]),
            "selected_side_line": selected_ah_line,
            "selected_side_price": selected_ah_price,
            "opposite_side_price": selected_ah_opposite_price,
        },
        "ou": {"line": float(ou["line"]), "over_price": float(ou["over"]["price"]), "under_price": float(ou["under"]["price"])},
        "promotion_eligible": False,
    }, "OK"


def _in_band(value: float, band) -> bool:
    return isinstance(band, list) and len(band) == 2 and float(band[0]) <= value < float(band[1])


def match_candidates(snapshot: dict, candidates: list[dict]) -> list[str]:
    matches: list[str] = []
    for candidate in candidates:
        if candidate.get("universe") != snapshot.get("universe"):
            continue
        key = candidate.get("pattern_key") or {}
        if snapshot.get("favorite_side") != key.get("favorite_side"):
            continue
        if not _in_band(float(snapshot["favorite_fair_probability"]), key.get("favorite_probability_band")):
            continue
        ah = snapshot["ah"]
        if abs(float(ah["selected_side_line"]) - float(key.get("ah_line"))) > 1e-9:
            continue
        if candidate.get("market") == "AH":
            if not _in_band(float(ah["selected_side_price"]), key.get("ah_price_band")):
                continue
        elif candidate.get("market") == "OU":
            ou = snapshot["ou"]
            if abs(float(ou["line"]) - float(key.get("ou_line"))) > 1e-9:
                continue
            side = key.get("ou_side")
            price = float(ou["over_price"] if side == "O" else ou["under_price"])
            if not _in_band(price, key.get("ou_price_band")):
                continue
        else:
            continue
        matches.append(str(candidate["pattern_id"]))
    return matches


def _merge_snapshots(path: Path, new_rows: list[dict]) -> int:
    rows: dict[tuple[str, str], dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows[(str(row.get("fixture_id")), str(row.get("observed_at")))] = row
    for row in new_rows:
        rows[(str(row.get("fixture_id")), str(row.get("observed_at")))] = row
    ordered = sorted(rows.values(), key=lambda r: (str(r.get("observed_at")), str(r.get("fixture_id"))))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in ordered), encoding="utf-8")
    return len(ordered)


def observe_from_env(root: Path = Path("."), *, horizon_days: int = 7) -> dict:
    generated_at = datetime.now(timezone.utc)
    key = os.getenv(ENV_KEY)
    if not key:
        return {"schema_version": "1.2", "status": "API_KEY_NOT_CONFIGURED", "generated_at": generated_at.isoformat(), "promotion_allowed": False}

    catalog = _load_json(root / CATALOG_PATH)
    candidates_payload = _load_json(root / CANDIDATE_PATH)
    if not isinstance(catalog, list) or not isinstance(candidates_payload, dict):
        return {"schema_version": "1.2", "status": "LOCAL_INPUT_UNAVAILABLE", "generated_at": generated_at.isoformat(), "promotion_allowed": False}
    candidates = candidates_payload.get("candidates") or []

    requests_attempted = 0
    selected_payload = _load_json(root / TARGETS_PATH)
    selected = (selected_payload or {}).get("tournaments") if isinstance(selected_payload, dict) else None
    if not isinstance(selected, list) or not targets_complete(selected):
        try:
            requests_attempted += 1
            tournaments = _rows(_get("/tournaments", key, {"sportId": SPORT_ID, "language": "en"}))
            selected = select_target_tournaments(tournaments)
        except Exception as exc:
            return {"schema_version": "1.2", "status": "TOURNAMENT_DISCOVERY_UNAVAILABLE", "generated_at": generated_at.isoformat(), "requests_attempted": requests_attempted, "errors": [f"{type(exc).__name__}: {exc}"], "promotion_allowed": False}
        target_report = {"schema_version": "1.1", "generated_at": generated_at.isoformat(), "complete": targets_complete(selected), "tournaments": selected}
        target_path = root / TARGETS_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(target_report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not targets_complete(selected):
        return {"schema_version": "1.2", "status": "TARGET_TOURNAMENTS_INCOMPLETE", "generated_at": generated_at.isoformat(), "requests_attempted": requests_attempted, "targets_found": len(selected), "targets_expected": sum(len(v) for v in TARGETS.values()), "promotion_allowed": False}

    try:
        batches = split_target_batches(selected)
    except ValueError as exc:
        return {"schema_version": "1.2", "status": "TARGET_BATCH_LAYOUT_INVALID", "generated_at": generated_at.isoformat(), "requests_attempted": requests_attempted, "errors": [str(exc)], "promotion_allowed": False}

    fixtures: list[dict] = []
    batch_reports: list[dict] = []
    for universe, batch_rows in batches:
        ids = ",".join(str(x["tournament_id"]) for x in batch_rows)
        try:
            requests_attempted += 1
            batch = _rows(_get("/odds-by-tournaments", key, {"tournamentIds": ids, "bookmakers": "bet365", "language": "en", "verbosity": 3}))
        except Exception as exc:
            return {
                "schema_version": "1.2",
                "status": "CURRENT_BATCH_UNAVAILABLE",
                "generated_at": generated_at.isoformat(),
                "requests_attempted": requests_attempted,
                "failed_universe": universe,
                "batch_reports": batch_reports,
                "errors": [f"{type(exc).__name__}: {exc}"],
                "promotion_allowed": False,
            }
        fixtures.extend(batch)
        batch_reports.append({"universe": universe, "tournament_count": len(batch_rows), "fixture_rows": len(batch)})
    observed_at = datetime.now(timezone.utc)

    by_tid = {int(x["tournament_id"]): x for x in selected}
    cutoff = observed_at + timedelta(days=horizon_days)
    snapshots: list[dict] = []
    reasons: Counter[str] = Counter()
    match_counts: Counter[str] = Counter()
    shape_counts: Counter[str] = Counter()
    shape_samples: list[dict] = []
    for fixture in fixtures:
        try:
            tid = int(fixture.get("tournamentId"))
        except (TypeError, ValueError):
            continue
        tmeta = by_tid.get(tid)
        if not tmeta:
            continue
        ko = _utc(fixture.get("startTime"))
        if ko is None or ko > cutoff:
            continue
        shape = mainline_shape(fixture, catalog)
        shape_key = f"AH{shape['ah_main_count']}_OU{shape['ou_main_count']}"
        shape_counts[shape_key] += 1
        if len(shape_samples) < 12:
            shape_samples.append({
                "fixture_id": fixture.get("fixtureId"),
                "universe": tmeta.get("universe"),
                "league": tmeta.get("tournament_name"),
                "ah_main_count": shape["ah_main_count"],
                "ou_main_count": shape["ou_main_count"],
                "ah_lines": shape["ah_lines"],
                "ou_lines": shape["ou_lines"],
            })
        snap, reason = extract_mainline_snapshot(fixture, catalog, observed_at=observed_at, tournament_meta=tmeta)
        reasons[reason] += 1
        if snap is None:
            continue
        matches = match_candidates(snap, candidates)
        snap["candidate_matches"] = matches
        snapshots.append(snap)
        for pid in matches:
            match_counts[pid] += 1

    total_stored = _merge_snapshots(root / SNAPSHOTS_PATH, snapshots)
    report = {
        "schema_version": "1.2",
        "classification": "V2_PROSPECTIVE_MAINLINE_OBSERVER",
        "status": "MAINLINE_SNAPSHOTS_OBSERVED" if snapshots else "NO_UNAMBIGUOUS_MAINLINE_SNAPSHOTS",
        "generated_at": generated_at.isoformat(),
        "observed_at": observed_at.isoformat(),
        "source_semantics": "CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED",
        "historical_mainline_reconstruction_allowed": False,
        "requests_attempted": requests_attempted,
        "scheduled_cadence_hours": 12,
        "batch_count": len(batch_reports),
        "batch_reports": batch_reports,
        "tournament_count": len(selected),
        "batch_fixture_rows": len(fixtures),
        "snapshots_this_run": len(snapshots),
        "snapshots_stored": total_stored,
        "candidate_matches_this_run": dict(sorted(match_counts.items())),
        "parse_reasons": dict(sorted(reasons.items())),
        "mainline_shape_counts": dict(sorted(shape_counts.items())),
        "mainline_shape_samples": shape_samples,
        "diagnostic_policy": "Cardinality diagnostics only; no alternative line is selected and admissibility remains exactly one main AH plus one main full-time O/U.",
        "promotion_allowed": False,
        "paper_research_only": True,
    }
    rp = root / REPORT_PATH
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(observe_from_env(), ensure_ascii=False))
