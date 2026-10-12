(async function collectionHealth(){
  const card=document.createElement('section'); card.className='card';
  const container=document.querySelector('.w')||document.body;
  container.prepend(card);
  function line(tag,text){const node=document.createElement(tag);node.textContent=text;card.append(node);return node;}
  line('h2','สถานะการเก็บข้อมูลแต่ละรอบ');
  try{
    const response=await fetch('reports/research_v2_operational_audit.json?t='+Date.now(),{cache:'no-store'});
    if(!response.ok)throw new Error('HTTP '+response.status);
    const report=await response.json(),collection=report.collection;
    if(!collection||!Array.isArray(collection.canonical_slots))throw new Error('ยังไม่มีรายงาน canonical slots');
    const stale=Date.now()-Date.parse(report.generated_at)>30*60*1000;
    const title=line('p',stale?'STALE — รายงานเกิน 30 นาที กรุณาดูเวลาอัปเดต':report.status);
    title.style.color=stale||!report.collection_health_passed?'var(--r)':'var(--y)';
    line('p','Football day '+report.football_day+' · เวลารายงาน '+collection.bangkok_now);
    line('p','มีข้อมูล '+collection.observed_slots+'/'+collection.expected_elapsed_slots+' รอบที่ถึงเวลา · Observed coverage '+(collection.coverage_fraction===null?'ยังไม่ถึงรอบ':(collection.coverage_fraction*100).toFixed(1)+'%'));
    line('p','ON_TIME '+collection.on_time_slots+' · LATE '+collection.late_slots+' · On-time coverage '+(collection.on_time_coverage_fraction==null?'ยังไม่ถึงรอบ':(collection.on_time_coverage_fraction*100).toFixed(1)+'%'));
    line('p','Data integrity: '+(report.data_assertions_passed?'PASS':'FAIL')+' · Collection: '+collection.collection_state);
    const scroll=document.createElement('div');scroll.className='scroll';card.append(scroll);
    const table=document.createElement('table');scroll.append(table);
    const head=document.createElement('tr');table.append(head);
    ['รอบเป้าหมาย','สถานะ','Provider','เวลาที่เก็บจริง','ช้า (นาที)','Snapshots','Fixtures'].forEach(v=>{const th=document.createElement('th');th.textContent=v;head.append(th);});
    for(const slot of collection.canonical_slots){
      const tr=document.createElement('tr');table.append(tr);
      const target=Date.parse(slot.target_time);
      const state=stale&&target<=Date.now()&&slot.state==='UPCOMING'?'UNVERIFIED — รอรายงานใหม่':slot.state+' / '+(slot.observation_timing||'UNVERIFIED');
      [slot.target_time,state,slot.provider||'—',slot.observed_at||'—',slot.lag_minutes??'—',slot.valid_snapshot_count,slot.canonical_fixture_count].forEach(v=>{const td=document.createElement('td');td.textContent=String(v);tr.append(td);});
      if(/MISSING|MISSED|UNVERIFIED/.test(state))tr.style.color='var(--r)';
    }
    for(const [name,p] of Object.entries(report.providers||{}))line('p',name+' · '+p.status+' · '+(p.fresh===false?'STALE · ':'')+'audit '+(p.generated_at||'UNKNOWN')+' · '+(p.errors||[]).join('; '));
    const [e2e,hist]=await Promise.all(['research_v2_end_to_end_audit','oddspapi_history_audit'].map(async name=>{let r=await fetch('reports/'+name+'.json',{cache:'no-store'});return r.ok?r.json():null;}));
    if(e2e){const m=e2e.movement_evaluation;line('p','Movement: '+JSON.stringify(e2e.movement_classification_counts));line('p','Chronological viewed-data evaluation: '+m.unique_evaluated_fixtures+' groups / '+m.unique_eligible_fixtures+' comparable groups · '+m.status+' · research only');line('p','FT lifecycle: '+JSON.stringify(e2e.ft_triage_counts)+' · no raw deletion');const d=document.createElement('details');card.append(d);const summary=document.createElement('summary');summary.textContent='FT ค้าง แยก provider / country / canonical competition';d.append(summary);const pre=document.createElement('pre');pre.style.whiteSpace='pre-wrap';pre.textContent=JSON.stringify(e2e.ft_triage_groups.filter(r=>r.lifecycle==='ACTIVE_OVERDUE'),null,2);d.append(pre);}
    if(hist)line('p','Historical archive audit '+hist.source_archive_rows+' source rows · '+hist.generated_at+' · exploratory only');
    line('p','ราคาที่กู้ช้าใช้เวลาที่เก็บจริง ไม่ใช่ราคาย้อนหลัง ณ เวลาเป้าหมาย · PAPER RESEARCH ONLY');
  }catch(error){line('p','UNVERIFIED — '+error.message).style.color='var(--r)';}
})();
