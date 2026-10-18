/* Read-only, exact slot evidence. Never infer a missing quote from another slot. */
(async()=>{
 const card=document.createElement('section');card.className='card';
 const heading=document.createElement('h2');heading.textContent='Old Auto Scanner · Retired';card.append(heading);
 const status=document.createElement('p');status.textContent='Retired 18 Oct 2026. Scheduling, retries and automatic recovery are disabled. Records below are historical evidence.';card.append(status);
 const host=document.querySelector('main')||document.body;host.insertBefore(card,host.children[2]||null);
 try{
  const load=async p=>{const r=await fetch(p,{cache:'no-store'});if(r.status===404 && p.includes('automatic_scan_'))return [];if(!r.ok)throw Error(r.status);return(await r.text()).trim().split('\n').filter(Boolean).map(JSON.parse)};
  const [receipts,manifests,snapshots]=await Promise.all([load('data/normalized/automatic_scan_slots.jsonl'),load('data/normalized/automatic_scan_manifests.jsonl'),load('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')]);
  const days=[...new Set([...receipts,...manifests].map(r=>r.football_day))].sort().reverse();
  const select=document.createElement('select');days.forEach(d=>select.add(new Option(d,d)));card.append(select);
  const content=document.createElement('div');content.style.overflowX='auto';card.append(content);
  const render=()=>{content.replaceChildren();const day=select.value,manifest=manifests.find(r=>r.football_day===day);
   const note=document.createElement('p');note.textContent=manifest?`Fixture set: ${manifest.fixtures.length} · immutable 15:00 preparation`:'No validated 15:00 fixture manifest';content.append(note);
   const table=document.createElement('table');content.append(table);
   const add=cells=>{const row=table.insertRow();cells.forEach(s=>{const c=row.insertCell();c.textContent=s??'—'})};
   add(['Round','Target','Actual','Delay (min)','Fixtures','Priced','No price','Requests','API errors','Health','Recovery','Run']);
   for(const hour of ['15','18','21','00']){const id=`${day}/${hour}00`,records=receipts.filter(r=>r.slot_id===id),r=records.findLast(r=>r.complete)||records.at(-1);
    add(r?[hour+':00',r.target_at,r.actual_scan_time,r.delay_minutes,r.total_fixtures,r.priced_fixtures,r.no_price_fixtures,r.requests_used,r.api_errors,r.scan_health,r.recovery_status,r.run_url]:[hour+':00','—','Missing']);
   }
   if(!manifest)return;
   const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Fixture AH / OU and no-price reasons';details.append(summary);content.append(details);
   const fixtures=document.createElement('table');details.append(fixtures);
   const header=fixtures.insertRow();['Fixture','15:00','18:00','21:00','00:00'].forEach(v=>header.insertCell().textContent=v);
   for(const f of manifest.fixtures){const row=fixtures.insertRow();row.insertCell().textContent=`${f.home} – ${f.away}`;
    for(const hour of ['15','18','21','00']){const records=receipts.filter(r=>r.slot_id===`${day}/${hour}00`),r=records.findLast(r=>r.complete)||records.at(-1),item=r?.daily_cohort_fixtures?.find(x=>x.fixture_id===f.fixture_id);const quotes=snapshots.filter(q=>String(q.fixture_id)===f.fixture_id && q.scheduled_target_at===r?.target_at);const q=quotes.at(-1);row.insertCell().textContent=q?`AH H ${q.ah.home_line} @ ${q.ah.home_price} / A ${q.ah.away_line} @ ${q.ah.away_price} · OU ${q.ou.line} O ${q.ou.over_price} / U ${q.ou.under_price} · ${q.observed_at}`:(item?.reason||'MISSING');}
   }
  };select.onchange=render;render();
 }catch(e){const p=document.createElement('p');p.textContent='Awaiting automatic slot evidence. No successful scan inferred.';card.append(p)}
})();
