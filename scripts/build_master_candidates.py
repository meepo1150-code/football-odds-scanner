#!/usr/bin/env python3
"""Build auditable master-entity candidates from existing archives; no API calls or destructive writes."""
import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path("data/normalized")
OUT=Path("reports/master_candidates")
OUT.mkdir(parents=True,exist_ok=True)
files=sorted(ROOT.glob("*.jsonl"))
def scalar(v):
    return v.strip() if isinstance(v,str) else ""
def val(r,*keys):
    for k in keys:
        x=r.get(k)
        if isinstance(x,dict):x=x.get("name")
        if scalar(x):return scalar(x)
    return ""
def write(name,header,rows):
    with (OUT/name).open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)
def norm(s):
    return re.sub(r"[^a-z0-9]+"," ",s.casefold()).strip()
countries=Counter(); leagues=Counter(); teams=Counter(); examples=defaultdict(set)
rows=0
for p in files:
    with p.open(encoding="utf-8") as f:
        for line in f:
            try:r=json.loads(line)
            except (ValueError,TypeError):continue
            if not isinstance(r,dict):continue
            rows+=1
            country=val(r,"country","country_name","league_country")
            league=val(r,"league","league_name","competition","competition_name")
            lid=str(r.get("tournament_id") or r.get("league_id") or "").strip()
            provider=val(r,"provider","source","bookmaker") or p.stem
            if country:countries[country]+=1
            if league:leagues[(country,league,provider,lid)]+=1
            for side in ("home","away"):
                team=val(r,side,side+"_team",side+"_team_name")
                tid=str(r.get(side+"_team_id") or "").strip()
                if team:
                    teams[(team,provider,tid)]+=1
                    if country:examples[(team,provider,tid)].add(country)
write("countries.csv",["country_name","observations","status"],[(c,n,"REVIEW") for c,n in countries.most_common()])
write("competitions.csv",["country_name","competition_name","provider","provider_competition_id","observations","status"],[(c,l,p,i,n,"REVIEW") for (c,l,p,i),n in sorted(leagues.items())])
write("teams.csv",["team_name","provider","provider_team_id","observed_countries","observations","status"],[(t,p,i,"|".join(sorted(examples[(t,p,i)])),n,"REVIEW") for (t,p,i),n in sorted(teams.items())])
print("ARCHIVE_FILES",len(files),"ROWS",rows,"COUNTRY_CANDIDATES",len(countries),"COMPETITION_CANDIDATES",len(leagues),"TEAM_CANDIDATES",len(teams))
print("No internal IDs assigned to ambiguous candidates. No API calls. No deletion.")
