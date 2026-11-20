'use strict';
// Summaries are derived only from saved hotel visits; drafts are labelled explicitly.
const reportFilters={period:'',hotel:'',technician:'',status:'',search:''};
function workMatches(v,filter){
 if(filter==='done')return v.maintenance_completed===true;
 if(filter==='work_pending')return v.report?.work_status==='pending';
 if(filter==='review')return ['submitted','revision_requested'].includes(v.status);
 return !filter||v.status===filter;
}
function reportStatusOptions(){return [['','Semua status'],['assigned','Ditugaskan'],['in_progress','Dalam pengerjaan'],['submitted','Menunggu review'],['revision_requested','Perlu revisi'],['approved','Disetujui'],['done','Maintenance selesai'],['work_pending','Pekerjaan pending']];}
function savedWorkLabel(v){return v.report?.work_status==='completed'?'Selesai diperiksa':v.report?.work_status==='pending'?'Pending':'Belum diisi';}
function workCharts(visits,period){
 const statuses=[['assigned','Ditugaskan'],['in_progress','Dalam pengerjaan'],['submitted','Menunggu review'],['revision_requested','Perlu revisi'],['approved','Disetujui']];
 const selected=visits.filter(v=>v.planned_date?.startsWith(period));
 const counts=statuses.map(([key,label])=>({key,label,n:selected.filter(v=>v.status===key).length}));
 const max=Math.max(1,...counts.map(c=>c.n));
 const end=new Date(period+'-01T12:00:00');
 const months=Array.from({length:6},(_,i)=>{const d=new Date(end.getFullYear(),end.getMonth()-5+i,1);const value=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');return {value,n:visits.filter(v=>v.planned_date?.startsWith(value)).length};});
 const peak=Math.max(1,...months.map(m=>m.n));
 return `<div class="work-charts"><section class="card detail-content"><h3>Status laporan · ${esc(month(period+'-01'))}</h3><p class="muted small">Klik status untuk melihat laporan terkait.</p><div class="work-status-chart">${counts.map(c=>`<button type="button" data-results-filter="${c.key}" data-results-period="${esc(period)}" aria-label="${esc(c.label)}: ${c.n} laporan"><span>${esc(c.label)}</span><svg viewBox="0 0 100 12" preserveAspectRatio="none" aria-hidden="true"><rect class="chart-track" width="100" height="12" rx="6"></rect><rect class="chart-bar ${c.key}" width="${c.n/max*100}" height="12" rx="6"></rect></svg><strong>${c.n}</strong></button>`).join('')}</div></section><section class="card detail-content"><h3>Penugasan 6 bulan terakhir</h3><p class="muted small">Klik bulan untuk membuka hasil maintenance.</p><div class="work-month-chart">${months.map(m=>`<button type="button" data-results-month="${m.value}" aria-label="${esc(month(m.value+'-01'))}: ${m.n} penugasan"><strong>${m.n}</strong><svg viewBox="0 0 48 120" aria-hidden="true"><rect class="chart-bar" x="8" y="${120-m.n/peak*112}" width="32" height="${m.n/peak*112}" rx="5"></rect></svg><small>${esc(new Date(m.value+'-01T12:00:00').toLocaleDateString('id-ID',{month:'short'}))}<br>${m.value.slice(0,4)}</small></button>`).join('')}</div></section></div>`;
}
function workResults(){
 if(!supervisor())return empty('Halaman ini khusus supervisor.');
 const f=reportFilters;
 const all=state.data.hotelvisits||[];
 const scope=all.filter(v=>(!f.hotel||v.hotel_id===f.hotel)&&(!f.technician||v.technician_id===f.technician)&&`${visitHotel(v)} ${techName(v.technician_id)} ${v.report?.summary||''} ${v.report?.pending_reason||''}`.toLowerCase().includes(f.search.toLowerCase()));
 const visits=scope.filter(v=>(!f.period||v.planned_date?.startsWith(f.period))&&workMatches(v,f.status)).sort((a,b)=>b.planned_date.localeCompare(a.planned_date)||String(b.created_at).localeCompare(String(a.created_at)));
 const options=(list,current)=>list.map(([value,label])=>`<option value="${esc(value)}" ${value===current?'selected':''}>${esc(label)}</option>`).join('');
 const controls=`<section class="card detail-content"><div class="work-filters"><label>Periode maintenance<input id="results-period" type="month" value="${esc(f.period)}"></label><label>Hotel<select id="results-hotel">${options([['','Semua hotel'],...(state.data.hotels||[]).map(h=>[h.id,h.name])],f.hotel)}</select></label><label>Teknisi<select id="results-technician">${options([['','Semua teknisi'],...(state.data.users||[]).filter(u=>u.role==='technician').map(u=>[u.id,u.name])],f.technician)}</select></label><label>Status hasil<select id="results-status">${options(reportStatusOptions(),f.status)}</select></label><label>Cari hasil maintenance<input id="results-search" type="search" maxlength="200" value="${esc(f.search)}" placeholder="Hotel, teknisi, ringkasan…"></label><button class="secondary" type="button" data-results-reset>Reset filter</button></div><p class="muted small">${visits.length} dari ${all.length} laporan. Draf ditampilkan sebagai pekerjaan berjalan; selesai maintenance berarti sudah disetujui dengan status pekerjaan selesai.</p></section>`;
 const rows=visits.map(v=>`<tr><td><strong>${esc(visitHotel(v))}</strong><small>${esc(v.planned_date)}</small></td><td>${esc(techName(v.technician_id))}</td><td>${badge(v.status)}${['assigned','in_progress','revision_requested'].includes(v.status)?'<small>Draf teknisi</small>':''}</td><td><strong>${esc(savedWorkLabel(v))}</strong>${v.report?.work_status==='pending'?`<small>${esc(v.report.pending_reason||'Alasan belum diisi')}</small>`:''}</td><td class="work-summary">${esc(v.report?.summary||'Belum ada ringkasan pemeriksaan.')}</td><td><button type="button" class="primary" data-result-visit="${esc(v.id)}">Lihat hasil & PDF</button></td></tr>`);
 return heading('Hasil Maintenance','Laporan pekerjaan teknisi, status review, dokumentasi dan PDF.',`<button class="secondary" data-refresh>Muat ulang</button>`)+controls+(f.period?workCharts(scope,f.period):'')+`<section class="card"><div class="card-heading"><h3>Daftar hasil pekerjaan</h3></div>${rows.length?table(['Hotel / tanggal','Teknisi','Status laporan','Hasil pekerjaan','Ringkasan pemeriksaan','Tindakan'],rows):empty('Tidak ada laporan yang sesuai.','Ubah periode atau reset filter untuk melihat laporan lainnya.')}</section>`+footer();
}
async function openWorkResults(filter='',period=''){
 if(!supervisor())return;
 const current=state.page==='reports';
 Object.assign(reportFilters,{period,hotel:current?reportFilters.hotel:'',technician:current?reportFilters.technician:'',status:filter,search:current?reportFilters.search:''});
 await navigate('reports');
}
document.addEventListener('click',async event=>{
 const button=event.target.closest('button');if(!button||button.disabled)return;
 try{
 if(button.hasAttribute('data-results-filter'))await openWorkResults(button.dataset.resultsFilter,button.dataset.resultsPeriod||'');
 else if(button.dataset.resultsMonth)await openWorkResults('',button.dataset.resultsMonth);
 else if(button.hasAttribute('data-results-reset')){Object.assign(reportFilters,{period:'',hotel:'',technician:'',status:'',search:''});render();}
 else if(button.dataset.resultVisit){const id=button.dataset.resultVisit;await openHotelVisit(id);if(state.hotelVisit?.id!==id)return;state.page='reports';nav();setBreadcrumb([{label:'Hasil Maintenance',page:'reports'},{label:visitHotel(state.hotelVisit)}]);$('#page-content').insertAdjacentHTML('afterbegin','<button class="link-button back" data-page="reports">← Daftar hasil maintenance</button>');}
 }catch(error){notice(error.message,true);}
});
document.addEventListener('change',event=>{const fields={'results-period':'period','results-hotel':'hotel','results-technician':'technician','results-status':'status'};const key=fields[event.target.id];if(key){reportFilters[key]=event.target.value;render();}});
document.addEventListener('input',event=>{if(event.target.id!=='results-search')return;const pos=event.target.selectionStart;reportFilters.search=event.target.value;render();const input=$('#results-search');input.focus();input.setSelectionRange(pos,pos);});
