from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .asian_settlement import settle_asian_handicap
from .settlement_ev import settlement_distribution

SEASONS = ("1920", "2021", "2122", "2223", "2324", "2425", "2526")
TRAIN = {"1920", "2021", "2122", "2223"}
VALIDATION = {"2324", "2425"}
HOLDOUT = {"2526"}
LEAGUES = {
    "Premier League": "premier-league",
    "Bundesliga": "bundesliga",
    "Serie A": "serie-a",
    "LaLiga": "la-liga",
    "Ligue 1": "ligue-1",
}
MIN_N = {"train": 150, "validation": 80, "holdout": 40}
FDR_Q = 0.10
MIN_CROSS_LEAGUES = 3
MIN_POSITIVE_LEAGUE_SHARE = 0.60
PRICE_WIDTH = 0.20
PROB_WIDTH = 0.10
DATA_PATH = Path("data/normalized/football_data_multiseason_ah.jsonl")
REPORT_PATH = Path("reports/football_data_multiseason_validation.json")
REGISTRY_PATH = Path("reports/pattern_registry.json")
PREREG_PATH = Path("reports/multiseason_preregistration.json")


def _float(row: dict, key: str) -> float | None:
    try:
        value = float(str(row.get(key, "")).strip())
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _int(row: dict, key: str) -> int | None:
    try:
        return int(float(str(row.get(key, "")).strip()))
    except (TypeError, ValueError):
        return None


def _band(v: float, width: float) -> tuple[float, float]:
    lo = math.floor((v + 1e-12) / width) * width
    return round(lo, 4), round(lo + width, 4)


def _fair_1x2(h: float, d: float, a: float) -> tuple[float, float, float]:
    inv = [1 / h, 1 / d, 1 / a]
    s = sum(inv)
    return inv[0] / s, inv[1] / s, inv[2] / s


def _on_quarter_grid(line: float) -> bool:
    return abs(line * 4 - round(line * 4)) < 1e-8


def normalize_row(row: dict, *, season: str, league: str) -> dict | None:
    hg, ag = _int(row, "FTHG"), _int(row, "FTAG")
    h, d, a = _float(row, "AvgH"), _float(row, "AvgD"), _float(row, "AvgA")
    ah_home = _float(row, "AHh")
    ahh, aha = _float(row, "AvgAHH"), _float(row, "AvgAHA")
    close_ah_home = _float(row, "AHCh")
    close_ahh, close_aha = _float(row, "AvgCAHH"), _float(row, "AvgCAHA")
    ch, cd, ca = _float(row, "AvgCH"), _float(row, "AvgCD"), _float(row, "AvgCA")
    required = (hg, ag, h, d, a, ah_home, ahh, aha, close_ah_home, close_ahh, close_aha, ch, cd, ca)
    if any(x is None for x in required):
        return None
    assert hg is not None and ag is not None and h is not None and d is not None and a is not None
    assert ah_home is not None and ahh is not None and aha is not None
    assert close_ah_home is not None and close_ahh is not None and close_aha is not None
    if min(h, d, a, ahh, aha, close_ahh, close_aha, ch, cd, ca) <= 1.0:
        return None
    if not _on_quarter_grid(ah_home) or not _on_quarter_grid(close_ah_home):
        return None
    fh, _, fa = _fair_1x2(h, d, a)
    favorite_side = "H" if fh >= fa else "A"
    favorite_p = fh if favorite_side == "H" else fa
    selected_line = ah_home if favorite_side == "H" else -ah_home
    selected_price = ahh if favorite_side == "H" else aha
    opposite_price = aha if favorite_side == "H" else ahh
    selected_close_line = close_ah_home if favorite_side == "H" else -close_ah_home
    selected_close_price = close_ahh if favorite_side == "H" else close_aha
    try:
        settled = settle_asian_handicap(hg, ag, selected_line, selected_price, favorite_side)
    except ValueError:
        return None
    price_band = _band(selected_price, PRICE_WIDTH)
    probability_band = _band(favorite_p, PROB_WIDTH)
    return {
        "season": season,
        "league": league,
        "date": (row.get("Date") or "").strip(),
        "home": (row.get("HomeTeam") or "").strip(),
        "away": (row.get("AwayTeam") or "").strip(),
        "ft_home_goals": hg,
        "ft_away_goals": ag,
        "favorite_side": favorite_side,
        "favorite_probability": round(favorite_p, 8),
        "favorite_probability_band": list(probability_band),
        "ah_line": selected_line,
        "ah_price": selected_price,
        "ah_opposite_price": opposite_price,
        "ah_price_band": list(price_band),
        "closing_ah_line": selected_close_line,
        "closing_ah_price": selected_close_price,
        "line_move": round(selected_close_line - selected_line, 4),
        "price_move": round(selected_close_price - selected_price, 6),
        "settlement": settled.settlement.value,
        "profit_units": round(settled.profit_units, 8),
        "source_semantics": "FOOTBALL_DATA_FIRST_COLLECTED_AFTER_MARKET_OPENING_NOT_TRUE_OPEN",
        "promotion_eligible": False,
    }


def load_mirror(mirror_root: Path) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    files = []
    for season in SEASONS:
        for league, directory in LEAGUES.items():
            path = mirror_root / "data" / directory / f"season-{season}.csv"
            if not path.exists():
                files.append({"season": season, "league": league, "status": "MISSING", "path": str(path)})
                continue
            raw = path.read_bytes()
            sha256 = hashlib.sha256(raw).hexdigest()
            text = raw.decode("utf-8-sig", errors="replace")
            reader = csv.DictReader(text.splitlines())
            normalized = 0
            total = 0
            for source_row in reader:
                total += 1
                item = normalize_row(source_row, season=season, league=league)
                if item is not None:
                    rows.append(item)
                    normalized += 1
            files.append({"season": season, "league": league, "status": "OK", "rows": total, "normalized_rows": normalized, "sha256": sha256})
    try:
        mirror_commit = subprocess.check_output(["git", "-C", str(mirror_root), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        mirror_commit = None
    return rows, {"mirror_commit": mirror_commit, "files": files}


def _phase(season: str) -> str | None:
    if season in TRAIN: return "train"
    if season in VALIDATION: return "validation"
    if season in HOLDOUT: return "holdout"
    return None


def _key(row: dict) -> tuple:
    return (
        row["favorite_side"],
        float(row["ah_line"]),
        tuple(row["ah_price_band"]),
        tuple(row["favorite_probability_band"]),
    )


def _roi(rows: list[dict]) -> float:
    return sum(float(r["profit_units"]) for r in rows) / len(rows) if rows else 0.0


def _bootstrap_ci(rows: list[dict], *, seed: int, draws: int = 4000) -> tuple[float, float]:
    vals = [float(r["profit_units"]) for r in rows]
    if not vals: return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(vals)
    means = []
    for _ in range(draws):
        means.append(sum(vals[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return means[int(0.025 * (draws - 1))], means[int(0.975 * (draws - 1))]


def _sign_flip_p(rows: list[dict], *, seed: int, draws: int = 5000) -> float:
    vals = [float(r["profit_units"]) for r in rows]
    if not vals: return 1.0
    observed = sum(vals)
    if observed <= 0: return 1.0
    rng = random.Random(seed)
    exceed = 1
    for _ in range(draws):
        stat = sum(v if rng.random() < 0.5 else -v for v in vals)
        if stat >= observed - 1e-12:
            exceed += 1
    return exceed / (draws + 1)


def _bh(pairs: list[tuple[str, float]]) -> dict[str, float]:
    if not pairs: return {}
    ranked = sorted(pairs, key=lambda x: x[1])
    m = len(ranked)
    out: dict[str, float] = {}
    running = 1.0
    for rank in range(m, 0, -1):
        pid, p = ranked[rank - 1]
        running = min(running, p * m / rank)
        out[pid] = min(1.0, running)
    return out


def _pid(key: tuple) -> str:
    raw = json.dumps(key, sort_keys=True, separators=(",", ":"))
    return "FD_AH_" + hashlib.sha1(raw.encode()).hexdigest()[:12].upper()


def _phase_stats(rows: list[dict], seed: int) -> dict:
    ci = _bootstrap_ci(rows, seed=seed)
    return {
        "n": len(rows),
        "roi": round(_roi(rows), 6),
        "profit_units": round(sum(float(r["profit_units"]) for r in rows), 6),
        "bootstrap_roi_ci95": [round(ci[0], 6), round(ci[1], 6)],
        "settlement_distribution": settlement_distribution(r["settlement"] for r in rows),
    }


def validate(rows: list[dict]) -> tuple[dict, dict]:
    groups: dict[tuple, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        phase = _phase(str(row["season"]))
        if phase:
            groups[_key(row)][phase].append(row)

    tested = []
    pvalues = []
    for i, (key, phases) in enumerate(sorted(groups.items(), key=lambda kv: str(kv[0]))):
        train = phases.get("train", [])
        validation = phases.get("validation", [])
        holdout = phases.get("holdout", [])
        if len(train) < MIN_N["train"] or _roi(train) <= 0:
            continue
        pid = _pid(key)
        p = _sign_flip_p(validation, seed=88000 + i) if len(validation) >= MIN_N["validation"] else 1.0
        pvalues.append((pid, p))
        tested.append((pid, key, phases, p))
    qvals = _bh(pvalues)

    candidates = []
    registry_patterns = []
    for i, (pid, key, phases, p) in enumerate(tested):
        train = phases.get("train", [])
        validation = phases.get("validation", [])
        holdout = phases.get("holdout", [])
        q = qvals.get(pid, 1.0)
        all_eval = validation + holdout
        league_rois = {}
        for league in LEAGUES:
            lr = [r for r in all_eval if r["league"] == league]
            if lr:
                league_rois[league] = {"n": len(lr), "roi": round(_roi(lr), 6)}
        positive_leagues = sum(v["roi"] > 0 for v in league_rois.values())
        positive_share = positive_leagues / len(league_rois) if league_rois else 0.0
        season_rois = {}
        for season in sorted(VALIDATION | HOLDOUT):
            sr = [r for r in phases.get(_phase(season) or "", []) if r["season"] == season]
            if sr: season_rois[season] = round(_roi(sr), 6)
        gates = {
            "train_n": len(train) >= MIN_N["train"],
            "validation_n": len(validation) >= MIN_N["validation"],
            "holdout_n": len(holdout) >= MIN_N["holdout"],
            "train_roi_positive": _roi(train) > 0,
            "validation_roi_positive": _roi(validation) > 0 if validation else False,
            "holdout_roi_positive": _roi(holdout) > 0 if holdout else False,
            "validation_fdr": q <= FDR_Q,
            "cross_league_count": len(league_rois) >= MIN_CROSS_LEAGUES,
            "positive_league_share": positive_share >= MIN_POSITIVE_LEAGUE_SHARE,
            "validation_seasons_positive": all(v > 0 for s, v in season_rois.items() if s in VALIDATION) and len([s for s in season_rois if s in VALIDATION]) == len(VALIDATION),
            "holdout_season_positive": season_rois.get("2526", 0) > 0,
        }
        passed = all(gates.values())
        fav_side, ah_line, price_band, prob_band = key
        phase_stats = {
            "train": _phase_stats(train, 1000 + i),
            "validation": _phase_stats(validation, 2000 + i),
            "holdout": _phase_stats(holdout, 3000 + i),
        }
        candidate = {
            "pattern_id": pid,
            "status": "GLOBAL_ROBUST_RESEARCH_CANDIDATE" if passed else "REJECT",
            "pattern_key": {"favorite_side": fav_side, "ah_line": ah_line, "ah_price_band": list(price_band), "favorite_probability_band": list(prob_band)},
            "market": "AH",
            "train_n": len(train), "validation_n": len(validation), "holdout_n": len(holdout),
            "p_validation_sign_flip": round(p, 8), "q_validation_bh": round(q, 8),
            "phase_stats": phase_stats,
            "league_stats_validation_plus_holdout": league_rois,
            "positive_league_share": round(positive_share, 6),
            "season_rois": season_rois,
            "gates": gates,
        }
        candidates.append(candidate)
        if passed:
            registry_patterns.append({
                "pattern_id": pid,
                "pattern": f"AH favorite {fav_side} line {ah_line:+g} price {price_band[0]:.2f}-{price_band[1]:.2f} fair-p {prob_band[0]:.2f}-{prob_band[1]:.2f}",
                "market": "AH",
                "pattern_key": candidate["pattern_key"],
                "train_n": len(train), "validation_n": len(validation), "holdout_n": len(holdout),
                "q_validation_bh": round(q, 8),
                "settlement_distributions": {phase: phase_stats[phase]["settlement_distribution"] for phase in ("train", "validation", "holdout")},
                "status": "GLOBAL_ROBUST_RESEARCH_CANDIDATE",
                "source": "FOOTBALL_DATA_GITHUB_MIRROR_LOCKED_SNAPSHOT",
            })

    report = {
        "schema_version": "2.0",
        "classification": "MULTI_SEASON_AH_VALIDATION",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistered_split": {"train": sorted(TRAIN), "validation": sorted(VALIDATION), "holdout": sorted(HOLDOUT)},
        "holdout_policy": "2025/26 preregistered before pattern-performance inspection; do not tune after viewing holdout",
        "thresholds": {"min_n": MIN_N, "fdr_q": FDR_Q, "cross_league_min": MIN_CROSS_LEAGUES, "positive_league_share_min": MIN_POSITIVE_LEAGUE_SHARE, "price_bucket_width": PRICE_WIDTH, "favorite_probability_bucket_width": PROB_WIDTH},
        "normalized_rows": len(rows),
        "train_positive_patterns_entering_validation": len(tested),
        "promoted_patterns": len(registry_patterns),
        "candidates": candidates,
    }
    registry = {
        "schema_version": "1.2",
        "generated_at": report["generated_at"],
        "source": "football-data.co.uk via GitHub mirror; early odds are first collected after market opening, not true opening",
        "validation_split": report["preregistered_split"],
        "pattern_count": len(registry_patterns),
        "patterns": registry_patterns,
    }
    return report, registry


def write_all(root: Path, mirror_root: Path) -> dict:
    rows, provenance = load_mirror(mirror_root)
    report, registry = validate(rows)
    report["provenance"] = provenance
    for path in (root / DATA_PATH, root / REPORT_PATH, root / REGISTRY_PATH, root / PREREG_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
    (root / DATA_PATH).write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")
    (root / REPORT_PATH).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / REGISTRY_PATH).write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    prereg = {
        "schema_version": "1.0",
        "locked_before_holdout_evaluation": True,
        "train_seasons": sorted(TRAIN),
        "validation_seasons": sorted(VALIDATION),
        "holdout_seasons": sorted(HOLDOUT),
        "holdout": "2025/26",
        "rules": {"min_n": MIN_N, "fdr_q": FDR_Q, "cross_league_min": MIN_CROSS_LEAGUES, "positive_league_share_min": MIN_POSITIVE_LEAGUE_SHARE, "price_bucket_width": PRICE_WIDTH, "favorite_probability_bucket_width": PROB_WIDTH},
        "note": "Do not retune thresholds, buckets, or pattern definitions based on 2025/26 holdout results.",
    }
    (root / PREREG_PATH).write_text(json.dumps(prereg, indent=2), encoding="utf-8")
    return {"normalized_rows": len(rows), "tested": report["train_positive_patterns_entering_validation"], "promoted": report["promoted_patterns"], "mirror_commit": provenance.get("mirror_commit")}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mirror-root", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    args = p.parse_args()
    print(write_all(args.root, args.mirror_root))
