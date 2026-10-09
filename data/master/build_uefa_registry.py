#!/usr/bin/env python3
"""Build the offline master from reviewed source rosters; never fetch providers.

The assignment ledger reserves every issued ID. Name normalization is ONLY for
initial master identity reconciliation, never for joining matches/results.
"""
import csv
import itertools
import json
import re
import string
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows, fields):
    with (ROOT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def norm(s):
    s = s.casefold().translate(str.maketrans({"ø": "o", "ł": "l", "đ": "d", "ð": "d", "þ": "th", "ı": "i", "æ": "ae", "ß": "ss"}))
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(fc|fk|sc|ac|afc|cf|rc|cd|ud|us|ss|sp|nk|hnk|sk|bk|if|ik|ssc|acf|as|cfc|calcio|1907)\b", " ", s)
    return "".join(s.split())


def main():
    rosters = json.loads((ROOT / "research/rosters.json").read_text())
    overrides = json.loads((ROOT / "research/identity_overrides.json").read_text())
    clubs = read("uefa_clubs_canonical.csv")
    original = {r["club_id"]: r for r in clubs}
    reservation_path = ROOT / "research/existing_club_ids.csv"
    if not reservation_path.exists():
        write("research/existing_club_ids.csv", [{k: r[k] for k in ("club_id", "country_id", "canonical_name")} for r in clubs], ["club_id", "country_id", "canonical_name"])
    reserved = {r["club_id"] for r in read("research/existing_club_ids.csv")}
    assignments_path = ROOT / "research/club_assignments.csv"
    assignments = read("research/club_assignments.csv") if assignments_path.exists() else []
    ledger = {(r["association_id"], r["source_name"]): r for r in assignments}
    used = set(original)

    def allocate(country, name):
        letters = re.sub("[^A-Z]", "", norm(name).upper())
        seed = (letters + "XXX")[:3]
        candidates = itertools.chain([seed], (seed[:2] + c for c in string.ascii_uppercase), ("".join(cs) for cs in itertools.product(string.ascii_uppercase, repeat=3)))
        for suffix in candidates:
            cid = country + "-" + suffix
            if cid not in used:
                used.add(cid)
                return cid
        raise ValueError("Three-letter code space exhausted: " + country)

    scope = read("uefa_55_division_scope.csv")
    catalog = read("uefa_domestic_league_catalog.csv")
    by_league = {(r["country_id"], int(r["league_level"])): r for r in catalog}
    memberships, coverage = [], []
    for roster in rosters:
        country, level = roster["country_id"], roster["division"]
        competition = f"{country}-{level:04d}"
        cat = by_league[(country, level)]
        for name in roster["names"]:
            key = (country, name)
            if key in ledger:
                cid = ledger[key]["club_id"]
            else:
                cid = overrides.get(country + "|" + name)
                if not cid:
                    candidates = [r["club_id"] for r in clubs if r["country_id"] == country and norm(r["canonical_name"]) == norm(name)]
                    if len(candidates) > 1:
                        raise ValueError(f"Ambiguous existing identity: {key}: {candidates}")
                    cid = candidates[0] if candidates else None
                if not cid:
                    # Newly registered cross-border club: retain its home code.
                    home = "AND" if key == ("ESP", "FC Andorra") else country
                    cid = allocate(home, name)
                    row = dict(club_id=cid, country_id=home, canonical_name=name)
                    clubs.append(row)
                    original[cid] = row
                ledger[key] = dict(association_id=country, source_name=name, club_id=cid, assignment_basis="REUSED_EXISTING" if cid in reserved else "NEW_RESERVED")
            if cid not in original:
                raise ValueError("Unknown club ID in assignment ledger: " + cid)
            memberships.append(dict(season=roster["season"], country_id=country, division=level, competition_id=competition, competition_name=cat["competition_name"], club_id=cid, source_name=name, source_url=roster["source_url"], verification_status=roster["verification_status"], checked_at=roster["checked_at"]))
        coverage.append(dict(country_id=country, division=level, competition_id=competition, competition_name=cat["competition_name"], season=roster["season"], expected_teams=roster.get("expected_teams", len(roster["names"])), recorded_teams=len(roster["names"]), verification_status=roster["verification_status"], source_url=roster["source_url"], checked_at=roster["checked_at"], blocked_reason=roster.get("official_confirmation_blocker", ""), notes=roster.get("notes", "")))
    active = {r["club_id"] for r in memberships}
    for row in clubs:
        row["season_membership_status"] = "SOURCE_VERIFIED_CURRENT" if row["club_id"] in active else "NOT_IN_CURRENT_SCOPED_ROSTERS"
        row["canonical_club_id"] = "GIB-FCB" if row["club_id"] == "GIB-BRU" else row["club_id"]
        if row["club_id"] == "GIB-BRU":
            row["season_membership_status"] = "RESERVED_DUPLICATE_ALIAS"
    write("uefa_clubs_canonical.csv", clubs, ["club_id", "country_id", "canonical_name", "season_membership_status", "canonical_club_id"])
    write("research/club_assignments.csv", sorted(ledger.values(), key=lambda r: (r["association_id"], r["source_name"])), ["association_id", "source_name", "club_id", "assignment_basis"])
    memberships.sort(key=lambda r: (r["country_id"], r["division"], r["club_id"]))
    write("uefa_verified_memberships_2026.csv", memberships, list(memberships[0]))
    # Keep the legacy three-column projection, with canonical (not numeric) IDs.
    scoped_keys = {(r["season"], r["competition_id"]) for r in memberships}
    exclusions = json.loads((ROOT / "research/user_excluded_divisions_2026_10_09.json").read_text())["excluded_competition_ids"]
    old = [r for r in read("memberships.csv") if (r["season"], r["competition_id"]) not in scoped_keys and not (r["season"] in {"2026", "2026-27"} and r["competition_id"] in exclusions)]
    projection = [dict(season=r["season"], competition_id=r["competition_id"], team_id=r["club_id"]) for r in memberships]
    write("memberships.csv", old + projection, ["season", "competition_id", "team_id"])
    coverage.sort(key=lambda r: (r["country_id"], r["division"]))
    write("uefa_league_coverage_2026.csv", coverage, list(coverage[0]))
    lookup = {(r["country_id"], r["division"]): r for r in coverage}
    for row in catalog:
        cv = lookup[(row["country_id"], int(row["league_level"]))]
        row.update(competition_status=cv["verification_status"], competition_id=cv["competition_id"], season=cv["season"])
    write("uefa_domestic_league_catalog.csv", catalog, list(catalog[0]))
    comps = read("competitions.csv")
    indexed = {r["competition_id"]: r for r in comps}
    for row in coverage:
        cid = row["competition_id"]
        if cid in indexed:
            indexed[cid]["status"] = row["verification_status"]
        else:
            comps.append(dict(competition_id=cid, country_id=row["country_id"], competition_name=row["competition_name"], status=row["verification_status"]))
    write("competitions.csv", comps, ["competition_id", "country_id", "competition_name", "status"])
    countries = read("countries.csv")
    indexed = {r["country_id"]: r for r in countries}
    for row in scope + [dict(country_id="LIE", country_name="Liechtenstein")]:
        cid = row["country_id"]
        if cid in indexed:
            indexed[cid]["status"] = "IN_SCOPE" if cid != "LIE" else "CROSS_BORDER_ONLY"
        else:
            countries.append(dict(country_id=cid, country_name=row["country_name"], status="IN_SCOPE" if cid != "LIE" else "CROSS_BORDER_ONLY"))
    write("countries.csv", countries, ["country_id", "country_name", "status"])
    write("country_scope.csv", [dict(country_id=r["country_id"], country_name=r["country_name"], domestic_scope="tiers " + r["division_levels"].replace("|", ","), priority=r["tier"], status="IN_SCOPE") for r in scope], ["country_id", "country_name", "domestic_scope", "priority", "status"])
    counts = Counter(r["country_id"] for r in memberships)
    write("uefa_55_club_coverage.csv", [dict(country_id=r["country_id"], country_name=r["country_name"], divisions=len(r["division_levels"].split("|")), current_memberships=counts[r["country_id"]], status="ALL_SCOPED_DIVISIONS_SOURCED") for r in scope], ["country_id", "country_name", "divisions", "current_memberships", "status"])
    print(json.dumps(dict(associations=len(scope), divisions=len(coverage), memberships=len(memberships), canonical_rows=len(clubs), reused=sum(r["assignment_basis"] == "REUSED_EXISTING" for r in ledger.values()), new=sum(r["assignment_basis"] == "NEW_RESERVED" for r in ledger.values()))))


if __name__ == "__main__":
    main()
