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
    const get=async name=>{const response=await fetch('reports/'+name+'.json?t='+Date.now(),{cache:'no-store'});return response.ok?response.json():null;};
    const [scan,prep]=await Promise.all([get('europe_pinnacle_research_v2_status'),get('daily_preparation_status')]);
    const [health,monitor]=await Promise.all([get('scan_health_latest'),get('scan_health_monitor')]);
    line('h2','Scan Health Report');
    if(health&&monitor){
      line('p','Monitor '+monitor.status+' · '+monitor.generated_at+' · Scan Missing '+monitor.scan_missing_count+' · FT Delay '+monitor.ft_delay_count+' · Unmatched candidates '+monitor.unmatched_count);
      line('p','Unmatched candidates คือ identity bridge ที่ยังยืนยันไม่ได้ ไม่ใช่จำนวน FT missing · เกมเลื่อนแสดงแยก '+monitor.verified_non_ft_lifecycle_count);
      const latest=health.latest_scan;
      line('p','Workflow SUCCESS หมายถึง job ทำงานจบ · Scan Health PASS/WARNING/FAIL ตรวจการเก็บข้อมูลแยกกัน');
      for(const provider of ['oddspapi','propline']){
        const receipt=health.recent_reports.find(r=>r.provider===provider);
        if(!receipt)continue;
        line('p',provider+' · Scan Health '+receipt.status+' · '+receipt.scan_status+' · '+(receipt.data_source_health||'')+' · '+receipt.generated_at+' · API errors '+receipt.api_error_count);
        if(receipt.workflow_run_url){const run=document.createElement('a');run.href=receipt.workflow_run_url;run.textContent=provider+' workflow';card.append(run);}
      }
      if(latest){
        line('p','Latest Scan '+latest.status+' · '+latest.provider+' · '+latest.generated_at+' · Football day '+latest.football_day+' · '+latest.provenance);
        line('p','พบ '+(latest.fixtures_found??'UNKNOWN')+' คู่ · ราคาถูกต้อง 1.80–2.20 '+latest.fixtures_with_valid_odds+' · ยังไม่มีราคาถูกต้อง '+(latest.fixtures_without_valid_odds??'UNKNOWN')+' · ยังไม่ได้ query '+latest.fixtures_unqueried+' · API errors '+latest.api_error_count);
        line('p','Report ID '+latest.report_id+' · '+latest.issues.join(', '));
      }
      const archive=document.createElement('details');card.append(archive);
      const heading=document.createElement('summary');heading.textContent='ประวัติ Scan Health ('+health.report_count+' reports)';archive.append(heading);
      const pre=document.createElement('pre');pre.style.whiteSpace='pre-wrap';pre.textContent=JSON.stringify(health.recent_reports,null,2);archive.append(pre);
      const link=document.createElement('a');link.href='data/normalized/scan_health_history.jsonl';link.textContent='ประวัติรายงานทั้งหมด';archive.append(link);
      const alert=document.createElement('details');card.append(alert);const title=document.createElement('summary');title.textContent='รายละเอียด Scan Missing / FT Delay / Unmatched';alert.append(title);
      const payload=document.createElement('pre');payload.style.whiteSpace='pre-wrap';payload.textContent=JSON.stringify({issues:monitor.issues,scan_missing:monitor.scan_missing,ft_delay:monitor.ft_delay,unmatched:monitor.unmatched},null,2);alert.append(payload);
    }else line('p','UNVERIFIED — ยังไม่มี Scan Health Report');
    line('h2','Coverage และการกู้ผล');
    line('p','Code health: offline assertions '+(report.data_assertions_passed?'PASS':'FAIL')+' · Collection health: '+collection.collection_state+' · Data quality: '+report.status+' · Workflow success ต้องตรวจแยกจาก data coverage');
    if(scan){
      line('p','Last scan status '+scan.status+' · Target '+scan.scheduled_target_at+' · Actual '+scan.actual_observed_at+' · Lag '+scan.schedule_lag_minutes+' นาที');
      line('p','พิจารณา '+(scan.master_competitions_considered??'—')+' ลีก · โปรแกรม '+(scan.scheduled_approved_fixtures??'—')+' คู่ · เก็บสะสม '+(scan.fixtures_captured_today??'—')+' คู่ · ยังไม่มีราคา '+(scan.scheduled_fixtures_without_snapshot??'—')+' คู่ · requests เพิ่มสำหรับลีกที่ถูกข้าม '+(scan.additional_market_requests_required??'—'));
      line('p','Quota ล่าสุดก่อนยิง '+(scan.quota_remaining_before??'UNKNOWN')+' · รอบนี้ใช้ '+(scan.requests_used??0)+' · '+(scan.coverage_complete?'พิจารณา scope ตาม receipt แล้ว':'COVERAGE GAPS REMAIN'));
      const detail=document.createElement('details');card.append(detail);const summary=document.createElement('summary');summary.textContent='Coverage report ทุกลีกที่อนุมัติ';detail.append(summary);
      const pre=document.createElement('pre');pre.style.whiteSpace='pre-wrap';pre.textContent=JSON.stringify(scan.competition_coverage||[],null,2);detail.append(pre);
    }
    if(prep){line('p','Daily preparation '+prep.status+' · '+prep.generated_at+' · Previous football day '+prep.previous_football_day+' · FT recovered '+prep.ft_recovered+' · unresolved '+prep.ft_unresolved+' · retired '+prep.retired_unresolved+' · Odds API สำหรับกู้ FT '+prep.odds_api_requests_used);}
    line('p','15:00 ทุกวันเริ่ม 13 ต.ค. 2026 · 18:00/21:00 คงเดิม · 00:00 ทุกวันปิดท้าย football day ก่อนหน้า · รอบใหม่รอหลักฐาน runtime ตามเวลาจริง');
    line('p','ราคาที่กู้ช้าใช้เวลาที่เก็บจริง ไม่ใช่ราคาย้อนหลัง ณ เวลาเป้าหมาย · PAPER RESEARCH ONLY');
  }catch(error){line('p','UNVERIFIED — '+error.message).style.color='var(--r)';}
})();
