#!/usr/bin/env python3
"""Allocate persistent provisional IDs to exact normalized names seen in archived football scans.
No network requests, no destructive changes, no automatic provider-ID verification.
"""
import csv,json,re,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path("data/master"); ARCH=Path("data/normalized")
def clean(x):
    return x.strip() if isinstance(x,str) else ""
def name(row,*fields):
    for field in fields:
        v=row.get(field)
        if isinstance(v,dict):v=v.get("name")
        if clean(v):return clean(v)
    return ""
def key(s):
    return re.sub(r"[^a-z0-9]+"," ",s.casefold()).strip()
def read(path):
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def write(path,header,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=header);w.writeheader();w.writerows(rows)
countries=read(ROOT/"countries.csv")
competitions=read(ROOT/"competitions.csv")
teams=read(ROOT/"teams.csv")
country_by_name={key(r["country_name"]):r["country_id"] for r in countries}
existing_comp={(r["country_id"],key(r["competition_name"])) for r in competitions}
existing_team={key(r["canonical_name"]) for r in teams}
candidate_country=Counter();candidate_comp=Counter();candidate_team=Counter()
for path in sorted(ARCH.glob("*.jsonl")):
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:r=json.loads(line)
            except (ValueError,TypeError):continue
            if not isinstance(r,dict):continue
            c=name(r,"country","country_name","league_country")
            l=name(r,"league","league_name","competition_name")
            h=name(r,"home","home_team","home_team_name")
            a=name(r,"away","away_team","away_team_name")
            if c:candidate_country[c]+=1
            if c and l:candidate_comp[(c,l)]+=1
            if h:candidate_team[h]+=1
            if a:candidate_team[a]+=1
# IDs for unverified entities are deterministic and namespaced separately from verified canonical IDs.
# Hash collisions and ambiguous same-name clubs remain in review and are not promoted.
def provisional(prefix,label):
    return prefix+"-"+hashlib.sha256(key(label).encode()).hexdigest()[:12].upper()
review=ROOT/"provisional"
review.mkdir(exist_ok=True)
country_rows=[]
for c,n in sorted(candidate_country.items()):
    if key(c) not in country_by_name:
        country_rows.append([provisional("CTRY",c),c,n,"UNVERIFIED"])
comp_rows=[]
for (c,l),n in sorted(candidate_comp.items()):
    cid=country_by_name.get(key(c),"")
    if not cid or (cid,key(l)) not in existing_comp:
        comp_rows.append([provisional("COMP",c+"|"+l),cid,c,l,n,"UNVERIFIED"])
team_rows=[]
for t,n in sorted(candidate_team.items()):
    if key(t) not in existing_team:
        team_rows.append([provisional("TEAM",t),t,n,"UNVERIFIED_POSSIBLE_NAME_COLLISION"])
for filename,header,rows in [
    ("countries.csv",["provisional_id","country_name","observations","status"],country_rows),
    ("competitions.csv",["provisional_id","known_country_id","country_name","competition_name","observations","status"],comp_rows),
    ("teams.csv",["provisional_id","team_name","observations","status"],team_rows)]:
    with (review/filename).open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)
print("EXISTING_MASTER",len(countries),"countries",len(competitions),"competitions",len(teams),"teams")
print("PROVISIONAL_COUNTRIES",len(country_rows),"PROVISIONAL_COMPETITIONS",len(comp_rows),"PROVISIONAL_TEAM_NAMES",len(team_rows))
print("No API requests; no permanent purge; no auto-approval of provisional IDs")
