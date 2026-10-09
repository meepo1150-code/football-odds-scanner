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
    source_review = json.loads((root / "research/official_roster_audit_2026_10_09.json").read_text())
    reviews = source_review["reviews"]
    cups = rows("cup_competition_registry_2026.csv")
    old = rows("research/existing_club_ids.csv")
    club_map = {r["club_id"]: r for r in clubs}
    comp_map = {r["competition_id"]: r for r in comps}
    country_ids = {r["country_id"] for r in countries}
    expected = {(r["country_id"], d) for r in scope for d in r["division_levels"].split("|")}
    exclusions = json.loads((root / "research/user_excluded_divisions_2026_10_09.json").read_text())
    excluded_ids = set(exclusions["excluded_competition_ids"])
    excluded_keys = {(r["country_id"], str(r["division"])) for r in exclusions["excluded_rosters"]}
    check(excluded_ids == {"AND-0001", "AZE-0001", "AZE-0002", "BLR-0001", "POL-0002", "RUS-0001"}, "User exclusion scope mismatch")
    check(len(scope) == 50 and len(expected) == 81, "Scope must be 50 associations / 81 divisions")
    check(not expected & excluded_keys, "User-excluded division restored to active scope")
    check(all(comp_map.get(cid, {}).get("status") == "EXCLUDED_USER" for cid in excluded_ids), "Excluded competition identity not reserved")
    unique(scope, ["country_id"], "Scope")
    unique(clubs, ["club_id"], "Clubs")
    unique(countries, ["country_id"], "Countries")
    unique(comps, ["competition_id"], "Competitions")
    unique(coverage, ["country_id", "division"], "Coverage")
    unique(catalog, ["country_id", "league_level"], "Catalog")
    unique(assignments, ["association_id", "source_name"], "Assignments")
    unique(reviews, ["competition_id"], "Official reviews")
    unique(cups, ["competition_id"], "Cup registry")
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
    check(len(rosters) == 81 and {(r["country_id"], str(r["division"])) for r in rosters} == expected, "Source roster scope mismatch")
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
    review_map = {r["competition_id"]: r for r in reviews}
    check(len(reviews) == 66, "Official review scope must contain all 66 baseline secondary divisions")
    check(all((r["country_id"], str(r["division"])) in expected | excluded_keys for r in reviews), "Official review outside scope")
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
        check(all(cv.get(k) == roster[k] for k in ("season", "source_url", "verification_status", "checked_at")), "Coverage metadata mismatch: " + str(key))
        cid = f'{roster["country_id"]}-{roster["division"]:04d}'
        review = review_map.get(cid)
        if review:
            complete = review.get("review_status") == "OFFICIAL_ROSTER_MATCH"
            check(complete == (roster["verification_status"] == "VERIFIED_OFFICIAL"), "Official status/evidence mismatch: " + cid)
            check(review.get("season") == roster["season"], "Official evidence season mismatch: " + cid)
            if complete:
                comparisons = review.get("comparisons", [])
                check(roster.get("evidence_id") == cid, "Missing official evidence ID: " + cid)
                check(Counter(p["source_name"] for p in comparisons) == Counter(roster["names"]), "Official evidence roster mismatch: " + cid)
                check(Counter(p["official_name"] for p in comparisons) == Counter(review.get("official_names", [])), "Official evidence names mismatch: " + cid)
                unique(comparisons, ["official_name"], "Official names " + cid)
                unique(comparisons, ["club_id"], "Official club IDs " + cid)
                check(all(p.get("result") == "MATCH_PRESERVED_ID" for p in comparisons), "Unconfirmed official comparison: " + cid)
                check(review.get("expected_teams") == roster.get("expected_teams") == len(actual), "Independent official team count mismatch: " + cid)
                check(review.get("source_url") == roster["source_url"] and review.get("checked_at") == roster["checked_at"], "Official evidence metadata mismatch: " + cid)
                check(bool(review.get("season_basis")), "Missing official season basis: " + cid)
                for p in comparisons:
                    check(p.get("club_id") == ledger.get((roster["country_id"], p["source_name"])), "Official evidence club ID mismatch: " + cid)
                removed = review.get("removed_current_memberships", [])
                check(set(review.get("baseline_names", [])) - set(roster["names"]) == {p["source_name"] for p in removed}, "Undocumented membership removal: " + cid)
                for p in removed:
                    check(p.get("club_id") in club_map and bool(p.get("decision_url")), "Removed club ID/evidence missing: " + cid)
            else:
                check(bool(review.get("blocked_reason")), "Incomplete official review without reason: " + cid)
        if cv.get("verification_status") == "BLOCKED":
            check(bool(cv.get("blocked_reason")), "BLOCKED without reason")
    projection = {(r["season"], r["competition_id"], r["team_id"]) for r in rows("memberships.csv")}
    check({(r["season"], r["competition_id"], r["club_id"]) for r in members} == projection, "Membership projection incomplete or contains stale rows")
    active = {r["club_id"] for r in members}
    check({r["club_id"] for r in clubs if r["season_membership_status"] == "SOURCE_VERIFIED_CURRENT"} == active, "Canonical season status mismatch")
    statuses = dict(Counter(r["verification_status"] for r in coverage))
    required_cups = {"ENG-0008", "ENG-0009", "ITA-0003", "ESP-0003", "DEU-0004", "FRA-0003", "NLD-0003", "PRT-0003", "INT-0001", "INT-0002", "INT-0004"}
    check({r["competition_id"] for r in cups} == required_cups, "Cup registry scope mismatch")
    for cup in cups:
        cid = cup["competition_id"]
        comp = comp_map.get(cid, {})
        check(all(comp.get(k) == cup[k] for k in ("country_id", "competition_name")), "Cup competition foreign key mismatch: " + cid)
        check(cup["competition_type"] in {"DOMESTIC_CUP", "UEFA_CLUB_COMPETITION"}, "Invalid cup type")
        check(cup["participant_status"] == "NOT_IMPORTED", "Cup entrants require separate reviewed source")
        check(not any(r["competition_id"] == cid for r in members), "Cup leaked into league membership")
        check(urlparse(cup["source_url"]).scheme == "https", "Missing official cup identity source")
        if cup["season_status"] == "BLOCKED":
            check(bool(cup["blocked_reason"]), "Cup season blocked without reason")
    mappings = rows("provider_mappings.csv")
    unique(mappings, ["entity_type", "provider", "provider_id"], "Provider external IDs")
    unique(mappings, ["entity_type", "internal_id", "provider"], "Provider internal IDs")
    for mapping in mappings:
        target = {"club": club_map, "competition": comp_map}.get(mapping["entity_type"], {})
        check(mapping["internal_id"] in target, "Provider mapping foreign key mismatch")
        check(bool(mapping["provider_id"]) and bool(mapping["provider"]), "Empty provider mapping")
    summary = dict(structural_status="PASS" if not errors else "FAIL", associations=len(scope), divisions=len(coverage), memberships=len(members), active_club_ids=len(active), canonical_rows=len(clubs), existing_ids_preserved=len(old), new_ids=len(clubs) - len(old), source_status_counts=statuses, blocked_divisions=statuses.get("BLOCKED", 0), errors=errors, limitations=["Source-verified means the named source supplied a season-specific roster; secondary sources are not official certification.", "Counts compare extracted source rosters to linked memberships, not an independent licensing audit.", "Offline QA does not re-fetch sources or certify future roster changes.", "Legacy numeric teams.csv is preserved and is not the authoritative current club table."])
    summary["input_sha256"] = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*.csv"))}
    summary["input_sha256"]["research/rosters.json"] = hashlib.sha256((root / "research/rosters.json").read_bytes()).hexdigest()
    summary["official_review"] = dict(baseline_secondary=len(reviews), completed=sum(r["review_status"] == "OFFICIAL_ROSTER_MATCH" for r in reviews), blocked=sum(r["review_status"] != "OFFICIAL_ROSTER_MATCH" and r["competition_id"] not in excluded_ids for r in reviews), excluded_by_user=len(excluded_ids))
    summary["cup_registry"] = dict(competitions=len(cups), participants_imported=0, blocked_seasons=sum(r["season_status"] == "BLOCKED" for r in cups))
    summary["provider_mapping_rows"] = len(mappings)
    summary["limitations"][1] = f"{summary['official_review']['completed']} baseline-secondary divisions were crosschecked against independent official season rosters; six remaining divisions were excluded by the user. Promotion/relegation legal history is not independently certified for every club."
    summary["input_sha256"]["research/official_roster_audit_2026_10_09.json"] = hashlib.sha256((root / "research/official_roster_audit_2026_10_09.json").read_bytes()).hexdigest()
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
