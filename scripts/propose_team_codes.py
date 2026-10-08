#!/usr/bin/env python3
"""Prepare three-letter team-code proposals from the existing master seed.
Does not change canonical team IDs or call an API.
"""
import csv,re
from collections import defaultdict
from pathlib import Path
base=Path("data/master")
with (base/"teams.csv").open(encoding="utf-8",newline="") as f:teams=list(csv.DictReader(f))
used=defaultdict(set)
for t in teams:
 p=t["team_id"].split("-")
 if len(p)==2 and len(p[1])==3 and p[1].isalpha():used[t["country_id"]].add(p[1])
def proposals(name):
 words=re.findall(r"[A-Za-z]+",name.upper())
 skip={"FC","CF","AFC","SC","UNITED","CITY","TOWN","CLUB","FOOTBALL","THE"}
 meaningful=[w for w in words if w not in skip] or words
 out=[]
 if len(meaningful)>=2:out.append((meaningful[0][:2]+meaningful[1][:1])[:3])
 if meaningful:out.append(meaningful[0][:3])
 if len(meaningful)>=2:out.append((meaningful[0][:1]+meaningful[1][:2])[:3])
 letters="".join(meaningful)
 for a in range(len(letters)):
  for b in range(a+1,len(letters)):
   for c in range(b+1,len(letters)):
    out.append(letters[a]+letters[b]+letters[c])
 return [s for s in dict.fromkeys(out) if len(s)==3 and s.isalpha()]
rows=[]
for t in sorted(teams,key=lambda x:(x["country_id"],x["canonical_name"])):
 country=t["country_id"];old=t["team_id"]
 if old.split("-")[-1] in used[country] and len(old.split("-")[-1])==3:
  rows.append([old,country,t["canonical_name"],old,"EXISTING_3LETTER_ID"]);continue
 code=next((c for c in proposals(t["canonical_name"]) if c not in used[country]),"")
 if code:used[country].add(code)
 rows.append([old,country,t["canonical_name"],country+"-"+code if code else "","PROPOSED_REVIEW" if code else "MANUAL_REVIEW"])
out=base/"team_code_proposals.csv"
with out.open("w",encoding="utf-8",newline="") as f:
 w=csv.writer(f);w.writerow(["legacy_team_id","country_id","team_name","proposed_team_id","status"]);w.writerows(rows)
print("PROPOSALS",len(rows),"NEED_MANUAL",sum(not r[3] for r in rows))
