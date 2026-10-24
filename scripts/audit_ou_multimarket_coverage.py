"""Audit every retained Research V2 AH/OU snapshot without provider requests or data writes.

Run locally: PYTHONPATH=src python scripts/audit_ou_multimarket_coverage.py
The output distinguishes all snapshot rows, canonical fixtures, latest per fixture,
and source/quote/mainline quality. It does not assume all scheduled rounds succeeded.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from odds_scanner.research_population import in_scope
from odds_scanner.research_v2_integrity import trusted_snapshot
from odds_scanner.research_v2_fixture_identity import build_bridge, project
from odds_scanner.research_v2_pattern_stats import _prematch_order

ROOT = Path(".")
SNAPSHOTS = ROOT / "data/normalized/europe_pinnacle_research_v2_snapshots.jsonl"
OUTCOMES = ROOT / "data/normalized/research_v2_pattern_outcomes.jsonl"
SLOTS = ROOT / "data/normalized/research_v2_slot_ledger.jsonl"


def read_jsonl(path: Path):
    if not path.is_file():
        raise FileNotFoundError(str(path))
    rows = []
    for number, line in enumerate(path.open(encoding="utf-8"), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: not a JSON object")
        rows.append(value)
    return rows


def num(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def classify_ou(snap):
    ou = snap.get("ou") or snap.get("over_under_2_5") or snap.get("ou_2_5") or {}
    if not isinstance(ou, dict) or not ou:
        return ("MISSING_OU", None)
    line = num(ou.get("line"))
    over = num(ou.get("over_price", ou.get("over")))
    under = num(ou.get("under_price", ou.get("under")))
    if line is None or abs(line*4-round(line*4)) > 1e-8 or line < 0:
        return ("INVALID_LINE", line)
    if over is None or under is None or over <= 1 or under <= 1:
        return ("MISSING_OR_INVALID_TWO_SIDED_PRICE", line)
    return ("VALID_PAIRED_QUOTE", line)


def go():
    raw = read_jsonl(SNAPSHOTS)
    trusted = [r for r in raw if trusted_snapshot(r)]
    scoped = [r for r in trusted if in_scope(r)]
    mapping, _ = build_bridge(scoped)
    canonical = project(scoped, mapping)
    valid = [r for r in canonical if r.get("fixture_id") and _prematch_order(r) is not None]
    groups = defaultdict(list)
    for r in valid:
        groups[str(r["fixture_id"])].append(r)
    for snapshots in groups.values():
        snapshots.sort(key=_prematch_order)
    latest = [snapshots[-1] for snapshots in groups.values()]
    distinct = set()
    dedup = []
    for r in valid:
        k = (str(r.get("fixture_id")),str(r.get("source_fixture_id") or ""),str(r.get("observed_at")),str(r.get("provider") or ""),str(r.get("bookmaker") or ""),
             json.dumps(r.get("ah") or {},sort_keys=True),json.dumps(r.get("ou") or {},sort_keys=True))
        if k in distinct:
            continue
        distinct.add(k)
        dedup.append(r)
    groups_dedup = defaultdict(list)
    for row in dedup:
        groups_dedup[str(row["fixture_id"])].append(row)
    latest_dedup = [max(rows,key=_prematch_order) for rows in groups_dedup.values()]
    outcomes = read_jsonl(OUTCOMES)
    settled = {str(r.get("fixture_id")) for r in outcomes if r.get("ft_home_goals") is not None and r.get("ft_away_goals") is not None}
    slots = read_jsonl(SLOTS)

    def summary(rows):
        classes = Counter()
        per_line = Counter()
        p_line = defaultdict(set)
        providers = defaultdict(Counter)
        srcs = defaultdict(Counter)
        unverified_mainline = Counter()
        settled_status = Counter()
        sample = defaultdict(list)
        for snap in rows:
            status, line = classify_ou(snap)
            classes[status] += 1
            prov = str(snap.get("provider") or "UNKNOWN")
            providers[prov][status] += 1
            semantic = str(snap.get("source_semantics") or "UNKNOWN")
            srcs[semantic][status] += 1
            if status == "VALID_PAIRED_QUOTE":
                lk = format(line, ".15g")
                per_line[lk] += 1
                p_line[lk].add(str(snap.get("fixture_id")))
                if snap.get("mainline_verified") is not True:
                    unverified_mainline[prov] += 1
            if str(snap.get("fixture_id")) in settled:
                settled_status[status] += 1
            if len(sample[status]) < 2:
                sample[status].append({
                    "fixture_id":snap.get("fixture_id"),"provider":prov,
                    "bookmaker":snap.get("bookmaker"),
                    "source_semantics":semantic,
                    "observed_at":snap.get("observed_at"),
                    "ah":snap.get("ah"),
                    "ou":snap.get("ou"),
                })
        return {"n":len(rows),"ou_status":dict(classes),
                "ou_lines_rows":dict(sorted(per_line.items(),key=lambda x:float(x[0]))),
                "ou_lines_unique_fixtures":{k:len(v) for k,v in sorted(p_line.items(),key=lambda x:float(x[0]))},
                "provider_status":{p:dict(v) for p,v in sorted(providers.items())},
                "source_semantics_status":{p:dict(v) for p,v in sorted(srcs.items())},
                "valid_ou_but_mainline_not_verified_by_provider":dict(unverified_mainline),
                "settled_fixture_snapshots_status":dict(settled_status),
                "examples":dict(sample)}

    per_fixture = Counter()
    per_fixture_provider = defaultdict(Counter)
    per_fixture_failures = []
    for fid, rows in groups_dedup.items():
        statuses = [classify_ou(r)[0] for r in rows]
        valid_count = statuses.count("VALID_PAIRED_QUOTE")
        if valid_count == len(rows):
            status = "ALL_OBSERVED_SNAPSHOTS_HAVE_PAIRED_OU"
        elif valid_count:
            status = "SOME_OBSERVED_SNAPSHOTS_HAVE_PAIRED_OU"
        else:
            status = "NO_OBSERVED_SNAPSHOT_HAS_PAIRED_OU"
        per_fixture[status] += 1
        prov = str(rows[-1].get("provider") or "UNKNOWN")
        per_fixture_provider[prov][status] += 1
        if status != "ALL_OBSERVED_SNAPSHOTS_HAVE_PAIRED_OU" and len(per_fixture_failures) < 12:
            per_fixture_failures.append({"fixture_id":fid,"n":len(rows),"ou_valid":valid_count,
                                          "provider":prov,"home":rows[-1].get("home"),"away":rows[-1].get("away")})
    slot_states = Counter((str(r.get("state") or r.get("status") or "UNKNOWN")) for r in slots)
    report = {
        "source":"retained Research V2 raw snapshot archive; no API queries",
        "snapshot_rows":{"raw":len(raw),"trusted":len(trusted),"trusted_in_scope":len(scoped),
                         "valid_prematch_ah":len(valid),"unique_observations_without_exact_duplicates":len(dedup)},
        "fixture_counts":{"valid_prematch_ah_canonical":len(groups),"settled_outcome_file":len(settled),
                          "prematch_ah_with_settled_outcome":sum(fid in settled for fid in groups),
                          "snapshot_counts_per_fixture_histogram":dict(Counter(len(v) for v in groups_dedup.values()))},
        "every_observed_snapshot":summary(valid),
        "every_unique_observation":summary(dedup),
        "latest_valid_ah_snapshot_per_canonical_fixture":summary(latest_dedup),
        "canonical_fixtures_with_ou_in_every_or_some_observation":dict(per_fixture),
        "canonical_fixtures_by_last_observed_provider":{p:dict(v) for p,v in per_fixture_provider.items()},
        "examples_of_ou_gaps":per_fixture_failures,
        "scan_slot_ledger":{"rows":len(slots),"states":dict(slot_states),
                            "note":"Not every planned/elapsed slot means fixture quote was observed; above counts reflect retained rows only."},
        "limitations":["Observed OHLC sampling is not always the bookmaker opening quote.",
                       "One pair of prices per row does not imply all alternate O/U lines were retained.",
                       "Only prices with matching bookmaker/provider and observation timestamp should be jointly analyzed.",
                       "Mainline_verified must be checked per provider; valid O/U quote alone does not prove official mainline.",
                       "Settled outcome count and snapshot count are distinct universes."],
    }
    print("OU_AUDIT_RESULT="+json.dumps(report,ensure_ascii=False,separators=(",",":")))


if __name__ == "__main__":
    go()
