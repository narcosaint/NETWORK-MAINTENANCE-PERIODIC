'use strict';
// Read-only projections of existing visit evidence. Local drafts never count as completion.
function v2Evidence(point){
 const item=point.item,result=item?.result||{};
 const runs=(item?.speedtests||[]).slice().sort((a,b)=>new Date(b.finished_at||b.created_at)-new Date(a.finished_at||a.created_at));
 const run=runs[0];
 const accepted=run?.status==='completed'&&run.context?.transport==='direct_https'&&run.context?.network==='hotel_wifi'&&run.context?.wifi_confirmed===true&&run.metrics&&['download_mbps','upload_mbps','ping_ms'].every(k=>Number.isFinite(run.metrics[k]));
 const failed=run?.status==='failed'&&Boolean(run.error?.trim());
 const condition=point.session?.observation?.notes.condition;
 const problem=result.outcome==='fail'||failed||condition==='problem';
 const done=['pass','fail'].includes(result.outcome)&&(accepted||failed)&&Boolean(item?.photos?.length);
 return {done,problem,status:problem?'problem':done?'good':result.outcome||condition==='attention'?'attention':'untested',run,accepted};
}
function v2Progress(done,total,label){return `<progress value="${done}" max="${total||1}" aria-label="${esc(label)}"></progress>`;}
function v2FloorSummary(floor){
 const evidence=floor.points.map(v2Evidence),done=evidence.filter(e=>e.done).length;
 const status=evidence.some(e=>e.problem)?'problem':done===floor.points.length&&done?'good':evidence.some(e=>e.status==='attention'||e.done)?'attention':'untested';
 const signals=floor.points.flatMap(p=>['band_24','band_5'].map(b=>p.item?.result?.[b]).filter(b=>b?.status==='measured'&&Number.isFinite(b.signal_dbm)).map(b=>b.signal_dbm));
 const runs=evidence.filter(e=>e.accepted).map(e=>e.run.metrics);
 const mean=(values,unit)=>values.length?`${(values.reduce((a,b)=>a+b,0)/values.length).toFixed(1)} ${unit}`:'Belum tersedia';
 return {done,status,signal:mean(signals,'dBm'),download:mean(runs.map(m=>m.download_mbps),'Mbps'),upload:mean(runs.map(m=>m.upload_mbps),'Mbps')};
}
// These labels describe saved evidence, never approval or native measurements.
function v21Backbone(report,key){
 const b=report[key]||{},numeric=k=>Number.isFinite(b[k]);
 const measured=['download_mbps','upload_mbps','speedtest_mbps','signal_dbm','tx_mbps','rx_mbps','ccq_percent'].some(numeric);
 if(!measured)return {label:'Belum diperiksa',tone:'untested'};
 if(b.conformity==='not_conforming')return {label:'Tidak sesuai',tone:'problem'};
 if(b.conformity==='conforming')return {label:'Sesuai · tersimpan',tone:'good'};
 return {label:'Pengukuran tersimpan',tone:'attention'};
}
function v21InspectionCards(report,points){
 const fields=['router_connector','switch_connector','signal_test','blank_spot','hotspot'];
 const filled=fields.filter(k=>report[k]!==null&&report[k]!==undefined).length;
 const problem=report.router_connector==='abnormal'||report.switch_connector==='abnormal'||report.signal_test==='poor'||report.blank_spot===true||report.hotspot===false;
 const lan={label:!filled?'Belum diperiksa':problem?'Perlu perhatian':filled===fields.length?'Pemeriksaan tersimpan':'Sebagian diperiksa',tone:!filled?'untested':problem?'problem':filled===fields.length?'good':'attention'};
 const evidence=points.map(v2Evidence),done=evidence.filter(e=>e.done).length;
 const sampled=points.some(p=>p.item?.result?.outcome||p.item?.speedtests?.length);
 const sampling={label:!sampled?'Belum diperiksa':evidence.some(e=>e.problem)?'Perlu perhatian':done===points.length&&done?'Pemeriksaan lengkap':`${done}/${points.length} titik selesai`,tone:!sampled?'untested':evidence.some(e=>e.problem)?'problem':done===points.length?'good':'attention'};
 return `<section class="v21-inspections" aria-label="Ringkasan pemeriksaan">${[['Backbone Fiber Optic',v21Backbone(report,'fo')],['Wireless Backbone',v21Backbone(report,'wireless')],['Local Area Network',lan],['Sampling Wi-Fi',sampling]].map(([name,status])=>`<article class="card"><h3>${name}</h3><span class="v2-chip ${status.tone}">${esc(status.label)}</span></article>`).join('')}</section>`;
}
function v2SamplingDashboard(v,floors){
 const points=floors.flatMap(f=>f.points),evidence=points.map(v2Evidence);
 const done=evidence.filter(e=>e.done).length,findings=evidence.filter(e=>e.problem).length;
 const serverPoints=points.filter(p=>p.item||p.session).length;
 const local=!v.coverage&&(points.some(p=>!p.item)||v.configuration.length>0);
 const report=v.visit.report||{};
 return `<section class="v2-dashboard" aria-label="Dashboard Maintenance V2">
 <div class="v2-title"><div><p class="eyebrow">PREVENTIVE MAINTENANCE</p><h2>Maintenance Hotel</h2><p>${esc(v.visit.site?.name||visitHotel(v.visit))} · ${esc(techName(v.visit.technician_id))}</p></div><div><label>Hotel<select id="v2-hotel">${(state.data.hotels||[]).map(h=>`<option value="${esc(h.id)}" ${h.id===v.visit.hotel_id?'selected':''}>${esc(h.name)}</option>`).join('')}</select></label><p>Periode ${esc(month(v.visit.planned_date.slice(0,7)+'-01'))} · ${esc(title(v.visit.status))}</p><button class="link-button" data-maintenance-hotel="${esc(v.visit.hotel_id)}">Ganti periode / penugasan →</button></div></div>
 <section class="v2-progress card"><div><strong>Progress Preventive Maintenance</strong><span>${points.length?`${done}/${points.length} titik selesai`:'Belum tersedia'}</span></div>${v2Progress(done,points.length,'Progress keseluruhan sampling')}</section>
 <div class="v2-stats">${[['▱',floors.length||'Belum tersedia','Total lantai','mint'],['◎',points.length||'Belum tersedia','Titik sampling','blue'],['✓',serverPoints?done:'Belum tersedia','Sampling selesai','green'],['⚠',serverPoints?findings:'Belum tersedia','Total temuan','red']].map(([icon,value,label,tone])=>`<article class="v2-stat ${tone}"><span class="v2-stat-icon" aria-hidden="true">${icon}</span><div><strong>${value}</strong><p>${label}</p></div></article>`).join('')}</div>
 <details class="v2-source"><summary>Detail progress & sumber data</summary><p>${v.coverage?'Cakupan memakai snapshot server; pengukuran per sesi dan submit V2 belum tersedia.':local?'Cakupan mencakup target lokal yang belum tersinkron.':'Target default 4 per lantai.'} ${serverPoints} titik terhubung server. Selesai membutuhkan hasil pemeriksaan, speedtest Wi-Fi atau gagal beralasan, serta foto server. Draf lokal tidak dihitung selesai. Temuan menghitung titik bermasalah / gagal uji, bukan entri temuan terstruktur. Progress bukan persetujuan laporan.</p></details>
 ${v21InspectionCards(report,points)}
 <div class="v2-floors">${floors.map(f=>{const s=v2FloorSummary(f);return `<details class="v2-floor"><summary><span class="v2-floor-icon" aria-hidden="true">▱</span><span class="v2-floor-name"><strong>Lantai ${esc(f.name)}</strong><small>${s.done}/${f.points.length} titik selesai · target ${f.target}</small><span class="v2-chip ${s.status}">${samplingStatusLabels[s.status]}</span></span><span class="v2-chips">${f.points.map(p=>{const e=v2Evidence(p);return `<span class="v2-chip ${e.status}">${e.done?'✓ ':e.problem?'⚠ ':''}${esc(p.name)}</span>`;}).join('')}</span><span class="v2-floor-progress"><strong>${f.points.length?Math.round(s.done/f.points.length*100):0}%</strong>${v2Progress(s.done,f.points.length,'Progress lantai '+f.name)}</span><span class="v2-chevron" aria-hidden="true">⌄</span></summary><div class="v2-floor-body"><div class="v2-metrics"><div><small>Rata-rata sinyal · manual tersimpan</small><strong>${s.signal}</strong></div><div><small>Rata-rata download · Wi-Fi tersimpan</small><strong>${s.download}</strong></div><div><small>Rata-rata upload · Wi-Fi tersimpan</small><strong>${s.upload}</strong></div><div><small>Status lantai</small><span class="v2-chip ${s.status}">${samplingStatusLabels[s.status]}</span></div></div><div class="v2-point-list">${f.points.map(p=>{const e=v2Evidence(p);return `<div><span><strong>${esc(p.name)}</strong><small>${p.session?esc(p.session.device?.name||'AP belum dihubungkan'):p.item?esc(p.item.device.name):'Belum tersinkron · target lokal'}${v.drafts[p.id]?' · ada draf lokal':''}</small></span><span class="v2-chip ${e.status}">${samplingStatusLabels[e.status]}</span></div>`;}).join('')}</div><button type="button" data-sampling-floor="${esc(f.id)}">Lihat lantai →</button></div></details>`;}).join('')||'<section class="card detail-content"><h3>Belum ada lantai sampling</h3><p>Konfigurasi lantai tersedia di Detail Hotel. Default target 4 titik tanpa membuat record database.</p></section>'}</div>
 <section class="v2-report-state card"><div><small>Laporan utama</small><strong>${report.summary?'Data tersimpan · validasi saat submit':'Belum diisi'}</strong></div><div><small>Dokumentasi sampling</small><strong>${serverPoints?`${points.filter(p=>p.item?.photos?.length).length}/${serverPoints} AP memiliki foto server`:'Belum tersedia'}</strong></div><div><small>Persetujuan PIC</small><strong>Belum tersedia</strong></div></section></section>`;
}
document.addEventListener('change',event=>{if(event.target.id==='v2-hotel')selectMaintenanceHotel(event.target.value).catch(error=>notice(error.message,true));});
