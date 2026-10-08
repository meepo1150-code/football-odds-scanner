#!/usr/bin/env python3
"""Network-free master integrity checks. Source retrieval is not re-run here."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent


def audit(root=ROOT):
    def rows(name):
        with (root / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    def unique(data, fields, label):
        counts = Counter(tuple(r[k] for k in fields) for r in data)
        check(not [k for k, n in counts.items() if n > 1], label + ": duplicate key")
    scope = rows("uefa_55_division_scope.csv")
    clubs = rows("uefa_clubs_canonical.csv")
    countries = rows("countries.csv")
    comps = rows("competitions.csv")
    members = rows("uefa_verified_memberships_2026.csv")
    coverage = rows("uefa_league_coverage_2026.csv")
    catalog = rows("uefa_domestic_league_catalog.csv")
    assignments = rows("research/club_assignments.csv")
    rosters = json.loads((root / "research/rosters.json").read_text())
    old = rows("research/existing_club_ids.csv")
    club_map = {r["club_id"]: r for r in clubs}
    comp_map = {r["competition_id"]: r for r in comps}
    country_ids = {r["country_id"] for r in countries}
    expected = {(r["country_id"], d) for r in scope for d in r["division_levels"].split("|")}
    check(len(scope) == 54 and len(expected) == 87, "Scope must be 54 associations / 87 divisions")
    unique(scope, ["country_id"], "Scope")
    unique(clubs, ["club_id"], "Clubs")
    unique(countries, ["country_id"], "Countries")
    unique(comps, ["competition_id"], "Competitions")
    unique(coverage, ["country_id", "division"], "Coverage")
    unique(catalog, ["country_id", "league_level"], "Catalog")
    unique(assignments, ["association_id", "source_name"], "Assignments")
    unique(members, ["season", "competition_id", "club_id"], "Memberships")
    unique(members, ["season", "club_id"], "Multiple domestic divisions for same club/season")
    unique(members, ["country_id", "source_name"], "Duplicate current source identity")
    for row in old:
        current = club_map.get(row["club_id"], {})
        check(all(current.get(k) == row[k] for k in row), "Existing ID/name changed: " + row["club_id"])
    for row in clubs:
        cid = row["club_id"]
        check(bool(re.fullmatch(r"[A-Z]{3}-[A-Z]{3}", cid)), "Invalid club code: " + cid)
        check(cid.startswith(row["country_id"] + "-"), "Club prefix mismatch: " + cid)
        check(row["country_id"] in country_ids, "Unknown club country: " + cid)
        target = club_map.get(row["canonical_club_id"])
        check(target is not None and target["canonical_club_id"] == target["club_id"], "Invalid/cyclic canonical redirect: " + cid)
    for row in comps:
        check(bool(re.fullmatch(r"[A-Z]{3}-[0-9]{4}", row["competition_id"])), "Invalid competition code")
        check(row["competition_id"].startswith(row["country_id"] + "-"), "Competition prefix mismatch")
        check(row["country_id"] in country_ids or row["country_id"] == "INT", "Unknown competition country")
    check({(r["country_id"], r["division"]) for r in coverage} == expected, "Coverage scope mismatch")
    check({(r["country_id"], r["league_level"]) for r in catalog} == expected, "Catalog scope mismatch")
    check(len(rosters) == 87 and {(r["country_id"], str(r["division"])) for r in rosters} == expected, "Source roster scope mismatch")
    ledger = {(r["association_id"], r["source_name"]): r["club_id"] for r in assignments}
    grouped = defaultdict(list)
    allowed = {"VERIFIED_OFFICIAL", "VERIFIED_SECONDARY", "BLOCKED"}
    for row in members:
        key = (row["country_id"], row["division"])
        grouped[key].append(row)
        check(key in expected, "Membership outside scope")
        club = club_map.get(row["club_id"], {})
        check(club.get("canonical_club_id") == row["club_id"], "Membership uses unknown/redirected club")
        check(comp_map.get(row["competition_id"], {}).get("country_id") == row["country_id"], "Competition foreign key mismatch")
        check(row["club_id"] == ledger.get((row["country_id"], row["source_name"])), "Assignment mismatch")
        check(row["season"] in {"2026", "2026-27"}, "Invalid current season")
        check(row["verification_status"] in allowed - {"BLOCKED"}, "Invalid accepted membership status")
        check(urlparse(row["source_url"]).scheme == "https" and bool(urlparse(row["source_url"]).netloc), "Invalid source URL")
        check(bool(re.fullmatch(r"2026-\d{2}-\d{2}", row["checked_at"])), "Missing checked date")
    cv_map = {(r["country_id"], r["division"]): r for r in coverage}
    for roster in rosters:
        key = (roster["country_id"], str(roster["division"]))
        actual = grouped[key]
        cv = cv_map.get(key, {})
        check(len(roster["names"]) == len(set(roster["names"])), "Duplicate source roster name: " + str(key))
        check(Counter(r["source_name"] for r in actual) == Counter(roster["names"]), "Source roster mismatch: " + str(key))
        check(str(len(actual)) == cv.get("recorded_teams") == cv.get("expected_teams"), "Team count mismatch: " + str(key))
        for row in actual:
            check(all(row[k] == roster[k] for k in ("season", "source_url", "verification_status", "checked_at")), "Source metadata mismatch: " + str(key))
        check(cv.get("verification_status") in allowed, "Invalid coverage status")
        if cv.get("verification_status") == "BLOCKED":
            check(bool(cv.get("blocked_reason")), "BLOCKED without reason")
    projection = {(r["season"], r["competition_id"], r["team_id"]) for r in rows("memberships.csv")}
    check(all((r["season"], r["competition_id"], r["club_id"]) in projection for r in members), "Membership projection incomplete")
    active = {r["club_id"] for r in members}
    check({r["club_id"] for r in clubs if r["season_membership_status"] == "SOURCE_VERIFIED_CURRENT"} == active, "Canonical season status mismatch")
    statuses = dict(Counter(r["verification_status"] for r in coverage))
    summary = dict(structural_status="PASS" if not errors else "FAIL", associations=len(scope), divisions=len(coverage), memberships=len(members), active_club_ids=len(active), canonical_rows=len(clubs), existing_ids_preserved=len(old), new_ids=len(clubs) - len(old), source_status_counts=statuses, blocked_divisions=statuses.get("BLOCKED", 0), errors=errors, limitations=["Source-verified means the named source supplied a season-specific roster; secondary sources are not official certification.", "Counts compare extracted source rosters to linked memberships, not an independent licensing audit.", "Offline QA does not re-fetch sources or certify future roster changes.", "Legacy numeric teams.csv is preserved and is not the authoritative current club table."])
    summary["input_sha256"] = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*.csv"))}
    summary["input_sha256"]["research/rosters.json"] = hashlib.sha256((root / "research/rosters.json").read_bytes()).hexdigest()
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.write_report:
        (ROOT / "QA_2026.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "input_sha256"}, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
