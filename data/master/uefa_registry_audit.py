#!/usr/bin/env python3
"""Audit completeness of UEFA club registry without guessing league membership."""
import csv
from collections import Counter
from pathlib import Path

root=Path(__file__).resolve().parent
def read(name):
    with (root/name).open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))
scope=read("uefa_55_division_scope.csv")
teams=read("teams.csv")
codes={r["country_id"] for r in scope}
ids=[r["team_id"] for r in teams]
dupes=[k for k,v in Counter(ids).items() if v>1]
bad_country=[r["team_id"] for r in teams if r["country_id"] not in codes]
bad_prefix=[r["team_id"] for r in teams if not r["team_id"].startswith(r["country_id"]+"-")]
legacy=[r["team_id"] for r in teams if len(r["team_id"].split("-",1)[-1])!=3 or not r["team_id"].split("-",1)[-1].isalpha()]
counts=Counter(r["country_id"] for r in teams)
print("UEFA associations:",len(scope))
print("Clubs seeded:",len(teams))
print("Associations with at least one club:",sum(counts[c]>0 for c in codes))
print("Duplicate IDs:",len(dupes))
print("Unknown country IDs:",len(bad_country))
print("Country prefix mismatches:",len(bad_prefix))
print("Non-three-letter IDs:",len(legacy))
print("IMPORTANT: presence of clubs is NOT proof of complete 2026/27 league rosters.")
for r in scope:
    print(f'{r["country_id"]}: {counts[r["country_id"]]:3} clubs; levels={r["division_levels"]}; cup={r["domestic_cup"]}; season roster=UNVERIFIED')
if dupes or bad_country or bad_prefix:
    raise SystemExit("Registry structural audit failed")
