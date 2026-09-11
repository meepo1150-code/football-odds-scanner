from __future__ import annotations

import json, os, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, _catalog, _get, _outcome_lookup, _player
from .oddspapi_quota_health import summarize_account
from .v2_mainline_observer import CATALOG_PATH, CANDIDATE_PATH, _load_json, extract_mainline_snapshot, mainline_shape, _in_band

TARGET_PATH = Path('reports/europe_discovery_tournaments.json')
SNAPSHOT_PATH = Path('data/normalized/europe_discovery_snapshots.jsonl')
REPORT_PATH = Path('reports/europe_discovery_status.json')
TARGETS = {
 'England': [('championship',), ('league one','league-one')], 'Germany': [('2. bundesliga','2-bundesliga','bundesliga 2')],
 'Italy': [('serie b','serie-b')], 'Spain': [('laliga 2','la liga 2','laliga-2','segunda division','segunda-division')],
 'France': [('ligue 2','ligue-2')], 'Austria': [('bundesliga','austrian bundesliga')], 'Switzerland': [('super league','super-league')],
 'Denmark': [('superliga','superligaen')], 'Norway': [('eliteserien',)], 'Sweden': [('allsvenskan',)],
 'Greece': [('super league','super-league')], 'Czech Republic': [('1. liga','first league','1-liga')],
 'Poland': [('ekstraklasa',)], 'Romania': [('superliga','liga i','liga-1')],
}
EXPECTED = 15
COOLDOWN = 1.25
CORE_QUOTA_RESERVE = 30

def norm(v): return ' '.join(str(v or '').strip().lower().replace('_','-').split())

def resolve(rows):
 out=[]
 for country, groups in TARGETS.items():
  accepted={country}; accepted.update({'Czechia'} if country=='Czech Republic' else set())
  for aliases in groups:
   aliases={norm(x) for x in aliases}; hits=[r for r in rows if isinstance(r,dict) and str(r.get('categoryName') or '') in accepted and (norm(r.get('tournamentName')) in aliases or norm(r.get('tournamentSlug')) in aliases)]
   if len(hits)==1 and hits[0].get('tournamentId') is not None:
    r=hits[0]; out.append({'country':country,'tournament_id':int(r['tournamentId']),'tournament_name':r.get('tournamentName'),'tournament_slug':r.get('tournamentSlug')})
 return sorted(out,key=lambda x:(x['country'],x['tournament_name'] or ''))

def quota_allows_discovery(summary: dict, *, reserve: int = CORE_QUOTA_RESERVE) -> bool:
 if summary.get('status') != 'QUOTA_AVAILABLE': return False
 try: return int(summary.get('request_remaining')) > reserve
 except (TypeError, ValueError): return False

def candidate_like(snapshot,candidates):
 matches=[]
 for c in candidates:
  k=c.get('pattern_key') or {}
  if snapshot.get('favorite_side')!=k.get('favorite_side') or not _in_band(float(snapshot['favorite_fair_probability']),k.get('favorite_probability_band')): continue
  ah=snapshot['ah']
  if abs(float(ah['selected_side_line'])-float(k.get('ah_line')))>1e-9: continue
  if c.get('market')=='AH' and not _in_band(float(ah['selected_side_price']),k.get('ah_price_band')): continue
  if c.get('market')=='OU':
   ou=snapshot['ou']; px=float(ou['over_price'] if k.get('ou_side')=='O' else ou['under_price'])
   if abs(float(ou['line'])-float(k.get('ou_line')))>1e-9 or not _in_band(px,k.get('ou_price_band')): continue
  elif c.get('market')!='AH': continue
  matches.append(str(c.get('pattern_id')))
 return matches

def ah_marker_diagnostic(fixture,catalog_rows,bookmaker='bet365'):
 book=(fixture.get('bookmakerOdds') or {}).get(bookmaker)
 if not isinstance(book,dict): return {'active_ah_markets':0,'marker_signatures':{},'market_state':'NO_BOOKMAKER'}
 catalog=_catalog(catalog_rows); signatures=Counter(); active=0
 for market_id,market_data in (book.get('markets') or {}).items():
  meta=catalog.get(str(market_id))
  if not isinstance(meta,dict) or not isinstance(market_data,dict) or market_data.get('marketActive') is not True: continue
  if 'asian handicap' not in str(meta.get('marketName') or '').lower(): continue
  names=_outcome_lookup(meta); selections={}
  for outcome_id,outcome in (market_data.get('outcomes') or {}).items():
   p=_player(outcome) if isinstance(outcome,dict) else None
   if not p or p.get('active') is not True: continue
   label=names.get(str(outcome_id),'').strip().lower()
   if label: selections[label]=p
  hp=selections.get('home') or selections.get('1'); ap=selections.get('away') or selections.get('2')
  if not hp or not ap: continue
  active+=1
  def marker(p):
   return 'TRUE' if p.get('mainLine') is True else ('FALSE' if p.get('mainLine') is False else 'MISSING')
  signatures[f"H_{marker(hp)}__A_{marker(ap)}"]+=1
 state='NO_ACTIVE_AH_MARKET' if active==0 else ('HAS_EXPLICIT_MAIN_AH' if signatures.get('H_TRUE__A_TRUE',0)>0 else 'AH_PRESENT_NO_EXPLICIT_MAIN')
 return {'active_ah_markets':active,'marker_signatures':dict(sorted(signatures.items())),'market_state':state}

def summarize_diagnostics(rows):
 overall_shapes=Counter(); overall_reasons=Counter(); marker_signatures=Counter(); market_states=Counter(); by_league=defaultdict(lambda:{'fixtures':0,'shape_counts':Counter(),'reason_counts':Counter(),'ah_marker_signatures':Counter(),'ah_market_states':Counter(),'active_ah_markets':0})
 for row in rows:
  key=f"{row.get('country') or ''} · {row.get('league') or '—'}"; shape=str(row.get('shape_key') or 'UNKNOWN'); reason=str(row.get('reason') or 'UNKNOWN')
  overall_shapes[shape]+=1; overall_reasons[reason]+=1; x=by_league[key]; x['fixtures']+=1; x['shape_counts'][shape]+=1; x['reason_counts'][reason]+=1
  md=row.get('ah_marker_diagnostic') or {}; state=str(md.get('market_state') or 'UNKNOWN'); market_states[state]+=1; x['ah_market_states'][state]+=1; n=int(md.get('active_ah_markets') or 0); x['active_ah_markets']+=n
  for sig,count in (md.get('marker_signatures') or {}).items(): marker_signatures[str(sig)]+=int(count); x['ah_marker_signatures'][str(sig)]+=int(count)
 return {'mainline_shape_counts':dict(sorted(overall_shapes.items())),'diagnostic_reason_counts':dict(sorted(overall_reasons.items())),'ah_market_marker_signatures':dict(sorted(marker_signatures.items())),'ah_fixture_market_states':dict(sorted(market_states.items())),'league_diagnostics':[{'league':k,'fixtures':x['fixtures'],'active_ah_markets':x['active_ah_markets'],'shape_counts':dict(sorted(x['shape_counts'].items())),'reason_counts':dict(sorted(x['reason_counts'].items())),'ah_marker_signatures':dict(sorted(x['ah_marker_signatures'].items())),'ah_market_states':dict(sorted(x['ah_market_states'].items()))} for k,x in sorted(by_league.items())],'diagnostic_policy':'Diagnostics only. Missing/false mainLine markers are observed, not repaired. No fallback AH line is selected; strict admissibility still requires exactly one explicit mainLine=true AH and one explicit mainLine=true full-time O/U.'}

def merge(rows):
 existing={}
 if SNAPSHOT_PATH.exists():
  for line in SNAPSHOT_PATH.read_text(encoding='utf-8').splitlines():
   try:r=json.loads(line)
   except json.JSONDecodeError: continue
   existing[(str(r.get('fixture_id')),str(r.get('observed_at')))]=r
 for r in rows: existing[(str(r.get('fixture_id')),str(r.get('observed_at')))]=r
 SNAPSHOT_PATH.parent.mkdir(parents=True,exist_ok=True)
 SNAPSHOT_PATH.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in sorted(existing.values(),key=lambda x:(str(x.get('observed_at')),str(x.get('fixture_id'))))),encoding='utf-8')

def write_report(report):
 REPORT_PATH.parent.mkdir(parents=True,exist_ok=True); REPORT_PATH.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); return report

def run():
 key=os.getenv(ENV_KEY,'').strip(); now=datetime.now(timezone.utc); requests=0
 report={'schema_version':'1.3','generated_at':now.isoformat(),'classification':'EUROPE_DISCOVERY_ONLY','production_promotion_allowed':False,'validation_gate_effect':'NONE','target_leagues':EXPECTED,'core_quota_reserve':CORE_QUOTA_RESERVE}
 if not key:
  report['status']='API_KEY_NOT_CONFIGURED'; return write_report(report)
 try:
  quota=summarize_account(_get('/account',key))
 except Exception as exc:
  report.update(status='SKIPPED_QUOTA_HEALTH_UNAVAILABLE',account_endpoint_metered=False,errors=[f'{type(exc).__name__}: {exc}']); return write_report(report)
 report.update(account_endpoint_metered=False,quota_remaining=quota.get('request_remaining'),quota_status=quota.get('status'))
 if not quota_allows_discovery(quota):
  report.update(status='SKIPPED_TO_PROTECT_CORE_QUOTA',requests_used=0,note='Discovery skipped before any billable request so the frozen core scanner keeps priority.'); return write_report(report)
 targets=_load_json(TARGET_PATH); selected=targets.get('tournaments',[]) if isinstance(targets,dict) else []
 if len(selected)!=EXPECTED:
  payload=_get('/tournaments',key,{'sportId':10,'language':'en'},20); requests+=1; selected=resolve(_rows(payload))
  TARGET_PATH.parent.mkdir(parents=True,exist_ok=True); TARGET_PATH.write_text(json.dumps({'schema_version':'1.0','resolved_at':now.isoformat(),'tournaments':selected},ensure_ascii=False,indent=2),encoding='utf-8')
 if len(selected)!=EXPECTED:
  report.update(status='TARGET_RESOLUTION_INCOMPLETE',resolved_leagues=len(selected),requests_used=requests); return write_report(report)
 catalog=_load_json(CATALOG_PATH) or []; candidates=(_load_json(CANDIDATE_PATH) or {}).get('candidates',[])
 strict=[]; fixture_count=0; reasons={}; diagnostic_rows=[]; last_finished=None
 for batch in [selected[i:i+5] for i in range(0,len(selected),5)]:
  if last_finished is not None:
   wait=COOLDOWN-(time.monotonic()-last_finished)
   if wait>0: time.sleep(wait)
  payload=_get('/odds-by-tournaments',key,{'tournamentIds':','.join(str(x['tournament_id']) for x in batch),'bookmakers':'bet365','language':'en','verbosity':3},30); requests+=1; last_finished=time.monotonic()
  meta={int(x['tournament_id']):x for x in batch}; fixtures=_rows(payload); fixture_count+=len(fixtures)
  for f in fixtures:
   tm={**(meta.get(int(f.get('tournamentId') or -1)) or {}),'universe':'EUROPE_DISCOVERY'}
   shape=mainline_shape(f,catalog); shape_key=f"AH{shape['ah_main_count']}_OU{shape['ou_main_count']}"; marker_diag=ah_marker_diagnostic(f,catalog)
   s,reason=extract_mainline_snapshot(f,catalog,observed_at=now,tournament_meta=tm); reasons[reason]=reasons.get(reason,0)+1
   diagnostic_rows.append({'country':tm.get('country'),'league':tm.get('tournament_name'),'shape_key':shape_key,'reason':reason,'ah_marker_diagnostic':marker_diag})
   if s: s['candidate_like_matches']=candidate_like(s,candidates); s['discovery_only']=True; strict.append(s)
 merge(strict)
 report.update(status='DISCOVERY_OBSERVED',resolved_leagues=len(selected),batches=3,requests_used=requests,fixtures_seen=fixture_count,strict_snapshots=len(strict),candidate_like_matches=sum(len(x['candidate_like_matches']) for x in strict),rejection_counts=reasons,odds_batch_min_cooldown_seconds=COOLDOWN,note='Candidate-like matches are expansion evidence only and never enter frozen forward validation.',**summarize_diagnostics(diagnostic_rows))
 return write_report(report)

if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False))
