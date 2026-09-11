from __future__ import annotations

import json, os, time
from datetime import datetime, timezone
from pathlib import Path

from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, _get
from .v2_mainline_observer import CATALOG_PATH, CANDIDATE_PATH, _load_json, extract_mainline_snapshot, _in_band

TARGET_PATH = Path('reports/europe_discovery_tournaments.json')
SNAPSHOT_PATH = Path('data/normalized/europe_discovery_snapshots.jsonl')
REPORT_PATH = Path('reports/europe_discovery_status.json')

# Deliberately separate from the frozen 10-league validation universe.
TARGETS = {
 'England': [('championship',), ('league one','league-one')],
 'Germany': [('2. bundesliga','2-bundesliga','bundesliga 2')],
 'Italy': [('serie b','serie-b')],
 'Spain': [('laliga 2','la liga 2','laliga-2','segunda division','segunda-division')],
 'France': [('ligue 2','ligue-2')],
 'Austria': [('bundesliga','austrian bundesliga')],
 'Switzerland': [('super league','super-league')],
 'Denmark': [('superliga','superligaen')],
 'Norway': [('eliteserien',)],
 'Sweden': [('allsvenskan',)],
 'Greece': [('super league','super-league')],
 'Czech Republic': [('1. liga','first league','1-liga')],
 'Poland': [('ekstraklasa',)],
 'Romania': [('superliga','liga i','liga-1')],
}
EXPECTED = 15
COOLDOWN = 1.25

def norm(v): return ' '.join(str(v or '').strip().lower().replace('_','-').split())

def resolve(rows):
 out=[]
 for country, league_alias_groups in TARGETS.items():
  accepted={country}
  if country=='Czech Republic': accepted.add('Czechia')
  for aliases in league_alias_groups:
   aliases={norm(x) for x in aliases}; hits=[]
   for r in rows:
    if not isinstance(r,dict) or str(r.get('categoryName') or '') not in accepted: continue
    if norm(r.get('tournamentName')) in aliases or norm(r.get('tournamentSlug')) in aliases: hits.append(r)
   if len(hits)==1 and hits[0].get('tournamentId') is not None:
    r=hits[0]; out.append({'country':country,'tournament_id':int(r['tournamentId']),'tournament_name':r.get('tournamentName'),'tournament_slug':r.get('tournamentSlug')})
 return sorted(out,key=lambda x:(x['country'],x['tournament_name'] or ''))

def candidate_like(snapshot,candidates):
 matches=[]
 for c in candidates:
  k=c.get('pattern_key') or {}
  if snapshot.get('favorite_side')!=k.get('favorite_side'): continue
  if not _in_band(float(snapshot['favorite_fair_probability']),k.get('favorite_probability_band')): continue
  ah=snapshot['ah']
  if abs(float(ah['selected_side_line'])-float(k.get('ah_line')))>1e-9: continue
  if c.get('market')=='AH':
   if not _in_band(float(ah['selected_side_price']),k.get('ah_price_band')): continue
  elif c.get('market')=='OU':
   ou=snapshot['ou']
   if abs(float(ou['line'])-float(k.get('ou_line')))>1e-9: continue
   px=float(ou['over_price'] if k.get('ou_side')=='O' else ou['under_price'])
   if not _in_band(px,k.get('ou_price_band')): continue
  else: continue
  matches.append(str(c.get('pattern_id')))
 return matches

def merge(rows):
 existing={}
 if SNAPSHOT_PATH.exists():
  for line in SNAPSHOT_PATH.read_text(encoding='utf-8').splitlines():
   try:r=json.loads(line)
   except:continue
   existing[(str(r.get('fixture_id')),str(r.get('observed_at')))]=r
 for r in rows: existing[(str(r.get('fixture_id')),str(r.get('observed_at')))]=r
 SNAPSHOT_PATH.parent.mkdir(parents=True,exist_ok=True)
 SNAPSHOT_PATH.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in sorted(existing.values(),key=lambda x:(str(x.get('observed_at')),str(x.get('fixture_id'))))),encoding='utf-8')

def run():
 key=os.getenv(ENV_KEY,'').strip(); now=datetime.now(timezone.utc); requests=0
 report={'schema_version':'1.0','generated_at':now.isoformat(),'classification':'EUROPE_DISCOVERY_ONLY','production_promotion_allowed':False,'validation_gate_effect':'NONE','target_leagues':EXPECTED}
 if not key:
  report['status']='API_KEY_NOT_CONFIGURED'; REPORT_PATH.write_text(json.dumps(report,indent=2),encoding='utf-8'); return report
 targets=_load_json(TARGET_PATH)
 selected=targets.get('tournaments',[]) if isinstance(targets,dict) else []
 if len(selected)!=EXPECTED:
  payload=_get('/tournaments',key,{'sportId':10,'language':'en'},20); requests+=1; selected=resolve(_rows(payload))
  TARGET_PATH.parent.mkdir(parents=True,exist_ok=True); TARGET_PATH.write_text(json.dumps({'schema_version':'1.0','resolved_at':now.isoformat(),'tournaments':selected},ensure_ascii=False,indent=2),encoding='utf-8')
 if len(selected)!=EXPECTED:
  report.update(status='TARGET_RESOLUTION_INCOMPLETE',resolved_leagues=len(selected),requests_used=requests); REPORT_PATH.write_text(json.dumps(report,indent=2),encoding='utf-8'); return report
 catalog=_load_json(CATALOG_PATH) or []; cand_doc=_load_json(CANDIDATE_PATH) or {}; candidates=cand_doc.get('candidates',[])
 strict=[]; fixture_count=0; reasons={}; batches=[selected[i:i+5] for i in range(0,len(selected),5)]
 last_finished=None
 for batch in batches:
  if last_finished is not None:
   wait=COOLDOWN-(time.monotonic()-last_finished)
   if wait>0: time.sleep(wait)
  ids=','.join(str(x['tournament_id']) for x in batch)
  payload=_get('/odds-by-tournaments',key,{'tournamentIds':ids,'bookmakers':'bet365','language':'en','verbosity':3},30); requests+=1; last_finished=time.monotonic()
  meta={int(x['tournament_id']):x for x in batch}
  fixtures=_rows(payload); fixture_count+=len(fixtures)
  for f in fixtures:
   m=meta.get(int(f.get('tournamentId') or -1)); tm={**(m or {}),'universe':'EUROPE_DISCOVERY'}
   s,reason=extract_mainline_snapshot(f,catalog,observed_at=now,tournament_meta=tm)
   reasons[reason]=reasons.get(reason,0)+1
   if s:
    s['candidate_like_matches']=candidate_like(s,candidates); s['discovery_only']=True; strict.append(s)
 merge(strict)
 report.update(status='DISCOVERY_OBSERVED',resolved_leagues=len(selected),batches=len(batches),requests_used=requests,fixtures_seen=fixture_count,strict_snapshots=len(strict),candidate_like_matches=sum(len(x['candidate_like_matches']) for x in strict),rejection_counts=reasons,odds_batch_min_cooldown_seconds=COOLDOWN,note='Candidate-like matches are expansion evidence only and never enter frozen forward validation.')
 REPORT_PATH.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); return report

if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False))
