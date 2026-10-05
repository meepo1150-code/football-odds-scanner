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
    line('p','ครบ '+collection.observed_slots+'/'+collection.expected_elapsed_slots+' รอบที่ถึงเวลา · Coverage '+(collection.coverage_fraction===null?'ยังไม่ถึงรอบ':(collection.coverage_fraction*100).toFixed(1)+'%'));
    line('p','Data integrity: '+(report.data_assertions_passed?'PASS':'FAIL')+' · Collection: '+collection.collection_state);
    const scroll=document.createElement('div');scroll.className='scroll';card.append(scroll);
    const table=document.createElement('table');scroll.append(table);
    const head=document.createElement('tr');table.append(head);
    ['รอบเป้าหมาย','สถานะ','Provider','เวลาที่เก็บจริง','ช้า (นาที)','Snapshots','Fixtures'].forEach(v=>{const th=document.createElement('th');th.textContent=v;head.append(th);});
    for(const slot of collection.canonical_slots){
      const tr=document.createElement('tr');table.append(tr);
      const target=Date.parse(slot.target_time);
      const state=stale&&target<=Date.now()&&slot.state==='UPCOMING'?'UNVERIFIED — รอรายงานใหม่':slot.state+(slot.recovered?' (LATE RECOVERY)':'');
      [slot.target_time,state,slot.provider||'—',slot.observed_at||'—',slot.lag_minutes??'—',slot.valid_snapshot_count,slot.canonical_fixture_count].forEach(v=>{const td=document.createElement('td');td.textContent=String(v);tr.append(td);});
      if(/MISSING|MISSED|UNVERIFIED/.test(state))tr.style.color='var(--r)';
    }
    line('p','ราคาที่กู้ช้าใช้เวลาที่เก็บจริง ไม่ใช่ราคาย้อนหลัง ณ เวลาเป้าหมาย · PAPER RESEARCH ONLY');
  }catch(error){line('p','UNVERIFIED — '+error.message).style.color='var(--r)';}
})();
