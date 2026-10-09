#!/usr/bin/env python3
"""Build an API-independent club registry from existing curated master clubs.

No provider lookups. Preserves existing IDs and flags non-3-letter legacy IDs.
The registry is an initial seed, not verified season memberships.
"""
import csv
from collections import Counter
from pathlib import Path

base=Path("data/master")
with (base/"teams.csv").open(newline="",encoding="utf-8") as f:
    teams=list(csv.DictReader(f))
with (base/"uefa_55_division_scope.csv").open(newline="",encoding="utf-8") as f:
    scope=list(csv.DictReader(f))
codes={r["country_id"] for r in scope}
out=base/"uefa_clubs_seed.csv"
rows=[]
for t in teams:
    if t["country_id"] not in codes:continue
    code=t["team_id"].split("-",1)[-1]
    status="CODE_READY_ROSTER_UNVERIFIED" if len(code)==3 and code.isalpha() else "LEGACY_ID_NEEDS_3LETTER_CODE"
    rows.append([t["country_id"],t["team_id"],t["canonical_name"],status,"UNVERIFIED"])
rows.sort()
with out.open("w",newline="",encoding="utf-8") as f:
    w=csv.writer(f)
    w.writerow(["country_id","existing_team_id","club_name","code_status","season_membership_status"])
    w.writerows(rows)
count=Counter(r[0] for r in rows)
print("UEFA_ASSOCIATIONS",len(scope),"SEED_CLUBS",len(rows),"COUNTRIES_WITH_SEED_CLUBS",len(count))
for country,n in sorted(count.items()):print(country,n)
print("No API calls. No claims of complete 2026-27 rosters.")
