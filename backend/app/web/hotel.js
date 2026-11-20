'use strict';
let hotelWorking=false;
let hotelPhotoUrls=[];
function clearHotelPhotos(){for(const url of hotelPhotoUrls)URL.revokeObjectURL(url);hotelPhotoUrls=[];}
function hotelList(){
 const selected=state.maintenanceHotelId,period=state.maintenanceMonth??`${new Date().getFullYear()}-${String(new Date().getMonth()+1).padStart(2,'0')}`;
 const visits=(state.data.hotelvisits||[]).filter(v=>(!selected||v.hotel_id===selected)&&(!period||v.planned_date?.startsWith(period)));
 const hotels=(state.data.hotels||[]).filter(h=>(!selected||h.id===selected)&&`${h.name} ${h.address||''}`.toLowerCase().includes(state.filter.toLowerCase()));
 const actions=supervisor()?'<button class="primary" data-hotel-create>＋ Jadwalkan PM hotel</button>':'';
 const controls=`<section class="card"><div class="card-heading"><div><h3>PM bulanan berdasarkan hotel</h3><p>Pilih hotel, lalu penugasan untuk membuka lantai dan area sampling.</p></div><div class="toolbar"><input id="search" aria-label="Cari data" placeholder="Cari hotel…" value="${esc(state.filter)}"><label>Periode PM<input id="maintenance-month" type="month" value="${esc(period)}"></label><button class="secondary" data-refresh>↻</button></div></div></section>`;
 const content=selected?hotels.map(h=>`<section class="card"><div class="card-heading"><h3>${esc(h.name)}</h3><button class="link-button" data-site-detail="${h.id}">Detail Hotel →</button></div>${table(['Periode / tanggal','Teknisi','Status','Tindakan'],visits.map(v=>`<tr><td>${esc(month(v.planned_date.slice(0,7)+'-01'))}<small>${esc(v.planned_date)}</small></td><td>${esc(techName(v.technician_id))}</td><td>${badge(v.status)}</td><td><div class="table-actions"><button class="link-button" data-maintenance-visit="${v.id}">Pilih lantai →</button><button class="link-button" data-hotel-visit="${v.id}">Laporan utama</button></div></td></tr>`))}</section>`).join(''):`<div class="hotel-grid">${hotels.map(h=>{const assigned=visits.filter(v=>v.hotel_id===h.id);return `<section class="card"><div class="detail-content"><p class="eyebrow">MAINTENANCE HOTEL</p><h3>${esc(h.name)}</h3><p class="muted">${esc(h.address||'Alamat belum diisi')}</p><p>${assigned.length} penugasan${period?' pada periode ini':''}</p><button class="primary" data-maintenance-hotel="${h.id}">Pilih hotel →</button></div></section>`;}).join('')}</div>`;
 if(selected)setBreadcrumb([{label:'Maintenance Hotel',page:'hotelvisits'},{label:find('hotels',selected)?.name||'Hotel'}]);
 return (selected?'<button class="link-button back" data-maintenance-all>← Pilih hotel lain</button>':'')+heading('Maintenance Hotel','Pemeriksaan hotel → lantai → area sampling.',actions)+controls+(content||empty('Hotel tidak ditemukan.','Ubah pencarian atau tambahkan Data Hotel.'))+footer();
}
function createHotelVisit(){
 const selected=state.maintenanceHotelId||(typeof hotelDetailView!=='undefined'?hotelDetailView?.hotel.id:null)||'';
 dialog('Jadwalkan PM hotel',field('hotel_id','Hotel','select',selected,options('hotels',x=>x.name))+field('technician_id','Teknisi','select','',options('users',x=>x.name,x=>x.role==='technician'&&x.active))+field('period','Periode PM bulanan','month',state.maintenanceMonth||new Date().toISOString().slice(0,7))+field('planned_date','Tanggal rencana','date')+'<p class="validation-hint">Satu penugasan berdasarkan hotel pada periode yang dipilih. Router dan switch inventaris tetap masuk cakupan; AP dipilih per area sampling. Jadwalkan setiap bulan sesuai kebutuhan.</p>',async form=>{
  const payload=Object.fromEntries(form);if(!payload.planned_date.startsWith(payload.period+'-'))throw new Error('Tanggal rencana harus berada dalam periode PM yang dipilih.');
  delete payload.period;await api('/hotel-visits',{method:'POST',body:JSON.stringify(payload)});
 },'Buat penugasan');
}
async function openHotelVisit(id){
 clearHotelPhotos();if(typeof clearSampling==='function')clearSampling();if(typeof hotelDetailView!=='undefined')hotelDetailView=null;state.visit=null;
 $('#page-content').innerHTML='<div class="loading">Memuat laporan hotel…</div>';
 try{
 const v=await api('/hotel-visits/'+id);const history=await collection(`/hotel-visits/${id}/history`);
 if(!state.token)return;
 state.hotelVisit=v;state.page='hotelvisits';nav();setBreadcrumb([{label:'Maintenance Hotel',page:'hotelvisits'},{label:visitHotel(v),hotel:v.hotel_id},{label:'Laporan utama'}]);
 const own=state.user.role==='technician'&&v.technician_id===state.user.id;
 const editable=own&&['in_progress','revision_requested'].includes(v.status);
 const r=v.report;
 let actions='';
 if(own&&v.status==='assigned')actions='<button class="primary" data-hotel-checkin>Mulai pemeriksaan hotel</button>';
 if(editable)actions='<button class="primary" data-hotel-report>Isi laporan utama</button><button class="secondary" data-hotel-sample>＋ Pilih AP sampling</button>'+(v.status==='in_progress'?'<button class="secondary" data-hotel-checkout>Check-out & kirim laporan</button>':'<button class="secondary" data-hotel-resubmit>Kirim ulang laporan</button>');
 if(supervisor()&&v.status==='submitted')actions='<button class="primary" data-hotel-review="approved">Setujui laporan hotel</button><button class="secondary" data-hotel-review="revision_requested">Minta revisi laporan hotel</button>';
 const devices=v.devices.map((item,n)=>`<article class="card"><div class="card-heading"><div><h3>${esc(item.device.name)}</h3><p>${esc(title(item.device.device_type))}${item.floor?' · Lantai '+esc(item.floor)+' / '+esc(item.point):' · '+esc(item.device.location||'Lokasi belum dicatat')}</p></div>${item.result.outcome?badge(item.result.outcome):'<span class="badge">Belum diperiksa</span>'}</div><div class="detail-content"><p class="small muted">${esc([item.device.brand,item.device.model,item.device.ip_address].filter(Boolean).join(' · '))}</p><p class="small">${esc(item.result.notes||'Belum ada catatan pemeriksaan.')}</p>${item.device.device_type==='ap'?bandSummary(item.result)+speedtestHistory(item,editable):''}<div class="photo-grid" id="photos-${item.id}">${item.photos.map(photo=>`<a class="photo-link" href="#" data-photo="${photo.id}"><img data-photo-id="${photo.id}" alt="Foto kondisi ${esc(item.device.name)}" loading="lazy"><span>${esc(date(photo.created_at))}</span></a>`).join('')}</div><p class="small ${item.photos.length?'muted':'error'}">${item.photos.length?'✓ '+item.photos.length+' foto tersimpan':'Foto kondisi wajib, belum diunggah'}</p>${editable?`<div class="actions"><button class="secondary" data-hotel-result="${item.id}">${item.device.device_type==='ap'?'Catat hasil & pengukuran AP':'Isi hasil pemeriksaan'}</button>${item.device.device_type==='ap'?`<button class="primary" data-speedtest="${item.id}">Jalankan speedtest</button>`:''}<label class="secondary photo-button">📷 Ambil / unggah foto<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" data-hotel-photo="${item.id}" hidden></label>${item.device.device_type==='ap'&&!item.photos.length&&!Object.keys(item.result).length&&v.status==='in_progress'?`<button class="link-button" data-hotel-unsample="${item.id}">Batalkan sampel</button>`:''}</div>`:''}</div></article>`).join('');
 $('#page-content').innerHTML='<button class="link-button back" data-page="hotelvisits">← Kembali ke Maintenance Hotel</button>'+heading(visitHotel(v),`${techName(v.technician_id)} · Rencana ${v.planned_date}`,badge(v.status))+`<div class="actions hotel-actions">${actions}<button class="secondary" data-sampling-open>Dashboard sampling</button><button class="secondary" data-refresh>↻ Muat ulang</button></div><div class="detail-grid"><div><section class="card"><div class="card-heading"><h3>Ringkasan laporan hotel</h3>${r.work_status?`<span class="badge ${esc(r.work_status)}">${r.work_status==='pending'?'Pending / tindak lanjut':'Selesai'}</span>`:''}</div><div class="detail-content"><dl class="key-values"><div><dt>Nama pelanggan</dt><dd>${esc(r.customer_company||v.site?.customer_name||v.site?.name||'—')}</dd></div><div><dt>Koneksi backbone</dt><dd>${esc(({fo_only:'Fiber optic',wireless_only:'Wireless',both:'FO + wireless',failover:'FO + wireless / failover',bonding:'FO + wireless / bonding'})[r.backbone_mode]||'Belum diisi')}</dd></div><div><dt>PIC</dt><dd>${esc(r.pic_name||'—')} ${esc(r.pic_contact||'')}</dd></div><div><dt>Check-in</dt><dd>${esc(date(v.checkin?.server_time))}</dd></div><div><dt>Check-out</dt><dd>${esc(date(v.checkout?.server_time))}</dd></div><div><dt>Hasil pekerjaan</dt><dd>${r.work_status?badge(r.work_status):'Belum diisi'}${r.pending_reason?'<p>'+esc(r.pending_reason)+'</p>':''}</dd></div></dl><p class="report-text">${esc(r.summary||'Teknisi belum menyimpan ringkasan.')}</p>${reportBackboneSummary(r)}<details class="report-details"><summary>Feedback, solusi dan catatan PIC</summary><dl class="key-values"><div><dt>Feedback pelanggan</dt><dd>${esc(r.customer_feedback||'Belum ada feedback')}</dd></div><div><dt>Solusi / tindak lanjut</dt><dd>${esc(r.solution||'Belum ada catatan')}</dd></div><div><dt>Pengecualian tanda tangan PIC</dt><dd>${esc(r.pic_exception_reason||'—')}</dd></div>${r.lan_notes?`<div><dt>Catatan LAN format lama</dt><dd>${esc(r.lan_notes)}</dd></div>`:''}</dl></details>${v.status==='approved'&&!v.maintenance_completed?'<p class="detail-note">Laporan disetujui, pekerjaan masih pending. Jadwalkan tindak lanjut sesuai keputusan supervisor.</p>':''}<p class="detail-note">Network Test setiap area mengikuti koneksi Wi-Fi HP teknisi. Hasil Wi-Fi Analyzer, speedtest, foto, review PIC dan PDF tersedia di bagian Review area & PDF.</p></div></section><h3 class="section-label">Perangkat & sampling AP (${v.devices.length})</h3>${devices}</div><aside><section class="card"><div class="card-heading"><h3>Riwayat pengajuan</h3></div><div class="detail-content">${history.length?history.map(e=>`<article class="history-event"><strong>${esc(title(e.action==='resubmitted'?'submitted':e.action))}</strong><small>${esc(date(e.created_at))} · versi ${e.version}</small><p>${esc(e.reason||'Bukti laporan tersimpan.')}</p><details><summary>Snapshot laporan</summary><pre>${esc(JSON.stringify(e.snapshot,null,2))}</pre></details></article>`).join(''):empty('Belum ada pengajuan.','Simpan hasil dan foto sebelum mengirim.')}</div></section><section class="card"><div class="detail-content"><h3>Cakupan kunjungan</h3><p class="small muted">Router/switch diambil dari inventaris saat penugasan. AP dipilih sebagai sampel; AP lainnya tidak dianggap sudah diperiksa.</p><p class="small muted">Minimal satu foto per perangkat. JPEG/PNG/WebP hingga 10 MiB dan 20 megapiksel, maksimal 10 foto per perangkat.</p></div></section></aside></div>`+footer();
 await appendMaintenanceReview(v);
 await Promise.all(v.devices.flatMap(item=>item.photos.map(async photo=>{
  try{const response=await fetch(photo.url,{headers:{Authorization:`Bearer ${state.token}`},cache:'no-store'});if(!response.ok)throw new Error();const url=URL.createObjectURL(await response.blob());if(state.hotelVisit?.id!==id){URL.revokeObjectURL(url);return;}hotelPhotoUrls.push(url);const img=$(`[data-photo-id="${photo.id}"]`);if(img){img.src=url;img.closest('a').href=url;img.closest('a').target='_blank';img.closest('a').rel='noopener';}}catch{const img=$(`[data-photo-id="${photo.id}"]`);if(img)img.alt='Foto belum dapat dimuat. Muat ulang untuk mencoba lagi.';}
 })));
 }catch(error){notice(error.message,true);render();}
}
function bandSummary(result){return `<div class="band-summary">${[['band_24','2,4 GHz'],['band_5','5 GHz (5,8 pada PDF)']].map(([key,label])=>{const b=result[key];return `<div><strong>${label}</strong><p>${b?.status==='measured'?`${esc(b.signal_dbm)} dBm · channel ${esc(b.channel)} · ${esc(b.bandwidth_mbps)} Mbps`:'Belum diukur / tidak tersedia'}${b?.reason?' · '+esc(b.reason):''}</p></div>`;}).join('')}</div>`;}
function pickSample(){
 const v=state.hotelVisit;const selected=new Set(v.devices.map(i=>i.device_id));
 const opts=options('devices',d=>`${d.name} · ${d.location||'lokasi belum diisi'}`,d=>d.hotel_id===v.hotel_id&&d.device_type==='ap'&&!selected.has(d.id));
 dialog('Pilih AP sampling',field('device_id','Access point','select','',opts)+field('floor','Lantai','text')+field('point','Kamar / koridor / area AP','text')+'<p class="validation-hint">Satu baris untuk satu AP yang benar-benar diuji. Jumlah sampel mengikuti kondisi hotel, bukan kuota tetap. Daftarkan AP melalui inventaris bila belum tersedia.</p>',async form=>api(`/hotel-visits/${v.id}/samples`,{method:'POST',body:JSON.stringify({expected_version:v.version,...Object.fromEntries(form)})}),'Tambahkan sampel');
}
function optionalNumber(form,key){const value=form.get(key);return value===null||value===''?null:Number(value);}
function bandFields(key,label,b={},index=0){
 const status=field(key+'_status','Status','select',b.status||'not_tested',[['not_tested','Belum diuji'],['unavailable','Band tidak tersedia'],['measured','Sudah diukur']]);
 const notes=field(key+'_reason','Keterangan','textarea',b.reason||'',[],false);
 return `<fieldset class="maintenance-category"><legend>${esc(checklistCategory(label,index))}</legend>`+maintenanceItem('band-'+key,'Hasil Pengukuran',0,status,notes)+`<div class="form-grid maintenance-metrics">`+field(key+'_signal','Sinyal (dBm)','number',b.signal_dbm??'',[],false)+field(key+'_channel','Channel','number',b.channel??'',[],false)+field(key+'_speed','Bandwidth test (Mbps)','number',b.bandwidth_mbps??'',[],false)+field(key+'_ssid','SSID (opsional)','text',b.ssid||'',[],false)+field(key+'_bssid','BSSID (opsional)','text',b.bssid||'',[],false)+`</div><p class="validation-hint">Jelaskan pada keterangan jika band tidak diuji atau tidak tersedia.</p></fieldset>`;
}
function editHotelDevice(itemId){
 const v=state.hotelVisit,item=v.devices.find(i=>i.id===itemId),r=item.result;
 let html=maintenanceItem('device-'+itemId,item.device.name,0,field('outcome','Status','select',r.outcome||'',[['pass','Baik'],['fail','Bermasalah'],['not_applicable','Tidak berlaku']]),field('notes','Keterangan','textarea',r.notes||'',[],false),{level:3});
 if(item.device.device_type==='ap')html+='<p class="validation-hint">Masukkan hasil yang benar-benar dibaca dari alat. Pastikan speedtest memakai Wi-Fi hotel/AP yang diperiksa. Sinyal/channel otomatis belum tersedia di web. Gunakan tombol Jalankan speedtest untuk mengukur kecepatan.</p>'+[['b24','Band 2,4 GHz',r.band_24],['b5','Band 5 GHz (5,8 pada PDF)',r.band_5]].map(([key,label,value],index)=>bandFields(key,label,value,index)).join('');
 dialog('Checklist perangkat',html,async form=>{
 const result={outcome:form.get('outcome'),notes:form.get('notes')||null};
 if(result.outcome!=='pass'&&!result.notes?.trim())throw new Error('Isi catatan tindakan atau alasan.');
 if(item.device.device_type==='ap')for(const [key,name]of[['b24','band_24'],['b5','band_5']]){
 const status=form.get(key+'_status');result[name]={status,reason:form.get(key+'_reason')||null,source:'manual'};
 if(status==='measured')Object.assign(result[name],{signal_dbm:optionalNumber(form,key+'_signal'),channel:optionalNumber(form,key+'_channel'),bandwidth_mbps:optionalNumber(form,key+'_speed'),ssid:form.get(key+'_ssid')||null,bssid:form.get(key+'_bssid')||null});
 }
 await api(`/hotel-visits/${v.id}/devices/${itemId}/result`,{method:'PUT',body:JSON.stringify({expected_version:v.version,result})});
 });
}
function conformityView(download,upload,service,percent){
 if(percent==null||service?.download_mbps==null||service?.upload_mbps==null)return {label:'Belum dapat dinilai — profil bandwidth / batas minimum site belum lengkap',kind:'unknown'};
 if(download===null||upload===null)return {label:'Menunggu hasil download dan upload',kind:'unknown'};
 const minDl=service.download_mbps*percent/100,minUl=service.upload_mbps*percent/100;
 const enough=(value,min)=>value+Number.EPSILON*Math.max(1,Math.abs(min))*4>=min;
 return {label:enough(download,minDl)&&enough(upload,minUl)?'Sesuai':'Tidak sesuai',kind:enough(download,minDl)&&enough(upload,minUl)?'pass':'fail'};
}
function backboneFields(key,label,value,profile,index){
 const b=value||{},service=profile[key]||{},percent=profile.minimum_percent;
 return `<fieldset data-backbone="${key}"><legend>${esc(checklistCategory(label,index))}</legend><dl class="service-values"><div><dt>Download layanan</dt><dd>${esc(service.download_mbps??'Belum diatur')} ${service.download_mbps!=null?'Mbps':''}</dd></div><div><dt>Upload layanan</dt><dd>${esc(service.upload_mbps??'Belum diatur')} ${service.upload_mbps!=null?'Mbps':''}</dd></div><div><dt>Batas kesesuaian</dt><dd>${percent==null?'Belum ditentukan':esc(percent)+'% dari layanan'}</dd></div></dl><div class="form-grid">`+field(key+'_download','Hasil speedtest download (Mbps)','number',b.download_mbps??'',[],false)+field(key+'_upload','Hasil speedtest upload (Mbps)','number',b.upload_mbps??'',[],false)+`</div><p class="comparison-row">Kesesuaian hasil: <output id="${key}-comparison" aria-live="polite"></output></p>`+(b.speedtest_mbps!=null?`<p class="validation-hint">Data lama: ${esc(b.speedtest_mbps)} Mbps tanpa arah download/upload. Nilai lama tetap disimpan; isi hasil dua arah yang benar.</p>`:'')+(key==='wireless'?field('wireless_linktest','Hasil link test radio','textarea',b.link_test_radio||'',[],false)+field('wireless_signal','Signal strength (dBm)','number',b.signal_dbm??'',[],false):'')+field(key+'_notes','Keterangan','textarea',b.notes||'',[],false)+'</fieldset>';
}
function lanCheck(key,label,value,note,choices,index){
 return maintenanceItem('report-form-'+key,label,index,field(key,'Status','select',value??'',choices),field(key+'_notes','Keterangan','textarea',note||''),{level:5});
}
function reportLanFields(r,normal){
 const groups=[{title:'LAN',items:[['router_connector','Koneksi LAN Router',normal],['switch_connector','LAN ke Switch',normal]]},
 {title:'Wireless dan Hotspot',items:[['signal_test','Signal Test',[['poor','Poor'],['good','Good'],['not_applicable','Tidak dapat diuji / tidak berlaku']]],['blank_spot','Blank Spot',[['false','Tidak ada'],['true','Ada']]],['hotspot','Hotspot',[['false','Tidak ada'],['true','Ada']]]]}];
 return groups.map((group,categoryIndex)=>`<section class="maintenance-category-section"><h4 class="maintenance-category-title">${esc(checklistCategory(group.title,categoryIndex))}</h4>${group.items.map(([key,label,choices],index)=>lanCheck(key,label,typeof r[key]==='boolean'?String(r[key]):r[key],r[key+'_notes'],choices,index)).join('')}</section>`).join('');
}
function editHotelReport(){
 const v=state.hotelVisit,r=v.report,site=v.site||find('hotels',v.hotel_id)||{},profile=site.maintenance_profile||{};
 const normal=[['normal','Normal'],['abnormal','Tidak normal'],['not_applicable','Tidak ada / tidak berlaku']];
 let html=`<section class="report-section"><h3>Informasi site</h3><dl class="key-values"><div><dt>Nama pelanggan (otomatis dari site)</dt><dd id="report-customer-name">${esc(site.customer_name||site.name||'—')}</dd></div><div><dt>Hotel / site</dt><dd>${esc(site.name||'—')}</dd></div></dl><div class="form-grid">`+field('pic_name','Nama PIC','text',r.pic_name||'')+field('pic_contact','Kontak PIC (opsional)','text',r.pic_contact||'',[],false)+`</div></section><section class="report-section"><h3>BACKBONE</h3>`+field('backbone_mode','Koneksi yang diperiksa','select',r.backbone_mode||'',[['fo_only','FO saja'],['wireless_only','Wireless saja'],['both','FO + wireless'],['failover','FO + wireless / failover'],['bonding','FO + wireless / bonding']])+[['fo','FO'],['wireless','Backup wireless']].map(([key,label],index)=>backboneFields(key,label,r[key],profile,index)).join('')+`<p class="validation-hint">Bandwidth layanan dan batas kesesuaian berasal dari profil site yang dikelola supervisor. Penilaian dihitung otomatis untuk kedua arah; tidak ada pilihan kesesuaian manual.</p></section><section class="report-section"><h3>LOCAL AREA NETWORK</h3>`+reportLanFields(r,normal)+`${r.lan_notes?'<p class="validation-hint">Catatan LAN lama: '+esc(r.lan_notes)+'</p>':''}</section><section class="report-section"><h3>Hasil pekerjaan</h3>`+field('summary','Ringkasan / hasil pemeriksaan','textarea',r.summary||'')+field('work_status','Hasil pekerjaan','select',r.work_status||'',[['completed','Selesai'],['pending','Pending / perlu tindak lanjut']])+field('pending_reason','Alasan pekerjaan pending','textarea',r.pending_reason||'',[],false)+field('customer_feedback','Feedback pelanggan','textarea',r.customer_feedback||'',[],false)+field('solution','Solusi / tindak lanjut','textarea',r.solution||'',[],false)+field('pic_exception_reason','Alasan pengecualian tanda tangan PIC','textarea',r.pic_exception_reason||'')+`<p class="validation-hint">Tanda tangan PIC disimpan dari halaman Review di Android dan dicantumkan pada PDF.</p></section>`;
 html=foldMaintenanceReport(html);
 dialog('Laporan utama hotel',html,async form=>{
 const report={form_version:2,lan_notes:r.lan_notes||null};
 for(const key of ['pic_name','pic_contact','backbone_mode','router_connector','switch_connector','signal_test','summary','work_status','pending_reason','customer_feedback','solution','pic_exception_reason'])report[key]=form.get(key)||null;
 for(const key of ['router_connector','switch_connector','signal_test','blank_spot','hotspot'])report[key+'_notes']=form.get(key+'_notes')||null;
 for(const key of ['blank_spot','hotspot'])report[key]=form.get(key)===''?null:form.get(key)==='true';
 for(const key of ['fo','wireless']){
 const enabled=key==='fo'?report.backbone_mode!=='wireless_only':report.backbone_mode!=='fo_only';
 report[key]=enabled?{...(r[key]||{}),download_mbps:optionalNumber(form,key+'_download'),upload_mbps:optionalNumber(form,key+'_upload'),notes:form.get(key+'_notes')||null,source:'manual'}:null;
 if(enabled&&key==='wireless')Object.assign(report[key],{signal_dbm:optionalNumber(form,'wireless_signal'),link_test_radio:form.get('wireless_linktest')||null});
 }
 if(report.work_status==='pending'&&!report.pending_reason)throw new Error('Isi alasan pekerjaan pending.');
 await api(`/hotel-visits/${v.id}/report`,{method:'PUT',body:JSON.stringify({expected_version:v.version,report})});
 });
 $('#form-dialog').classList.add('report-wide');
 function update(){
  const mode=$('[name=backbone_mode]',$('#dialog-fields')).value;
  for(const key of ['fo','wireless']){
   const block=$(`[data-backbone="${key}"]`);
   const enabled=key==='fo'?mode!=='wireless_only':mode!=='fo_only';
   block.hidden=!enabled;for(const el of block.querySelectorAll('input,textarea'))el.disabled=!enabled;
   const down=$(`[name=${key}_download]`).value,up=$(`[name=${key}_upload]`).value;
   const result=conformityView(down===''?null:Number(down),up===''?null:Number(up),profile[key],profile.minimum_percent);
   const output=$('#'+key+'-comparison');output.textContent=result.label;output.className='badge '+result.kind;
  }
 }
 $('#dialog-fields').oninput=update;$('#dialog-fields').onchange=update;update();
}
function reportBackboneSummary(report){
 return `<div class="report-sections"><h4>BACKBONE</h4>${[['fo','FO'],['wireless','Backup wireless']].map(([key,label],index)=>[key,checklistCategory(label,index)]).filter(([key])=>report[key]).map(([key,label])=>{
 const b=report[key];const comparison=b.conformity==='conforming'?'Sesuai':b.conformity==='not_conforming'?'Tidak sesuai':'Belum dapat dinilai';
 return `<div class="report-subsection"><strong>${label}</strong><p>Download: ${esc(b.download_mbps??'Belum diukur')} Mbps · Upload: ${esc(b.upload_mbps??'Belum diukur')} Mbps</p><p>${report.form_version===2?'Kesesuaian otomatis':'Kesesuaian lama'}: ${esc(comparison)}${b.minimum_percent!=null?' · batas '+esc(b.minimum_percent)+'%':''}</p>${b.link_test_radio?`<p>Link test radio: ${esc(b.link_test_radio)}</p>`:''}${b.speedtest_mbps!=null?`<p class="muted">Data lama tanpa arah: ${esc(b.speedtest_mbps)} Mbps</p>`:''}<p>${esc(b.notes||'')}</p></div>`;
 }).join('')}<h4>LOCAL AREA NETWORK</h4>${[{title:'LAN',items:[['router_connector','Koneksi LAN Router'],['switch_connector','LAN ke Switch']]},{title:'Wireless dan Hotspot',items:[['signal_test','Signal Test'],['blank_spot','Blank Spot'],['hotspot','Hotspot']]}].map((group,categoryIndex)=>`<section class="maintenance-category-section"><h5 class="maintenance-category-title">${esc(checklistCategory(group.title,categoryIndex))}</h5>${group.items.map(([key,label],index)=>reportCheckSummary(report,key,label,index)).join('')}</section>`).join('')}</div>`;
}
function reportCheckSummary(report,key,label,index){const value=report[key];const text=typeof value==='boolean'?(value?'Ada':'Tidak ada'):({normal:'Normal',abnormal:'Tidak normal',not_applicable:'Tidak berlaku',good:'Good',poor:'Poor'})[value]||'Belum diperiksa';return maintenanceReadOnly('report-summary-'+key,label,index,esc(text),report[key+'_notes'],{level:6});}

async function hotelLocation(checkout=false){
 const v=state.hotelVisit;notice('Mencari lokasi perangkat…');const gps=await coordinates();$('#notice').hidden=true;
 dialog(checkout?'Kirim laporan hotel':'Mulai pemeriksaan hotel',`<p class="validation-hint">${checkout?'Foto wajib, hasil pemeriksaan dan laporan harus sudah disimpan.':'Waktu server dan lokasi akan dicatat.'}</p>`+(gps?`<p class="small">Lokasi diperoleh · akurasi ±${Math.round(gps.accuracy_m)} meter.</p>`:field('gps_exception_reason','Alasan GPS tidak tersedia','textarea')),async form=>api(`/hotel-visits/${v.id}/${checkout?'check-out':'check-in'}`,{method:'POST',body:JSON.stringify({expected_version:v.version,device_time:new Date().toISOString(),...(gps||{gps_exception_reason:form.get('gps_exception_reason')})})}),checkout?'Kirim untuk review':'Check-in');
}
document.addEventListener('click',async event=>{
 const el=event.target.closest('button');if(!el||![...el.attributes].some(a=>a.name.startsWith('data-hotel-'))||hotelWorking)return;
 hotelWorking=true;
 try{
 if(el.hasAttribute('data-hotel-create'))createHotelVisit();
 else if(el.dataset.hotelVisit){$('#notice').hidden=true;await openHotelVisit(el.dataset.hotelVisit);}
 else if(el.hasAttribute('data-hotel-pdf'))await downloadHotelPdf(el.dataset.hotelPdf==='preview');
 else if(el.hasAttribute('data-hotel-checkin'))await hotelLocation();
 else if(el.hasAttribute('data-hotel-checkout'))await hotelLocation(true);
 else if(el.hasAttribute('data-hotel-sample'))pickSample();
 else if(el.dataset.hotelResult)editHotelDevice(el.dataset.hotelResult);
 else if(el.hasAttribute('data-hotel-report'))editHotelReport();
 else if(el.dataset.hotelUnsample){if(confirm('Batalkan AP sampling yang belum diperiksa?')){const v=state.hotelVisit;await api(`/hotel-visits/${v.id}/samples/${el.dataset.hotelUnsample}?expected_version=${v.version}`,{method:'DELETE'});await openHotelVisit(v.id);}}
 else if(el.hasAttribute('data-hotel-resubmit')){const v=state.hotelVisit;dialog('Kirim ulang laporan hotel','<p class="small muted">Seluruh hasil dan foto wajib harus sudah tersimpan. Bukti check-out awal dipertahankan.</p>',async()=>api(`/hotel-visits/${v.id}/resubmit`,{method:'POST',body:JSON.stringify({expected_version:v.version})}),'Kirim ulang');}
 else if(el.dataset.hotelReview){const v=state.hotelVisit,decision=el.dataset.hotelReview;dialog(decision==='approved'?'Setujui laporan hotel':'Minta revisi laporan hotel','<p class="validation-hint">Tinjau semua perangkat, foto dan pengecualian. Approval laporan pending tidak menandai pekerjaan selesai.</p>'+field('reason','Catatan keputusan','textarea'),async form=>api(`/hotel-visits/${v.id}/review`,{method:'POST',body:JSON.stringify({expected_version:v.version,decision,reason:form.get('reason')})}),decision==='approved'?'Setujui laporan':'Minta revisi');}
 }catch(error){notice(error.message,true);}finally{hotelWorking=false;}
});
document.addEventListener('change',async event=>{
 const input=event.target;if(!input.matches('[data-hotel-photo]')||!input.files.length)return;
 const file=input.files[0],v=state.hotelVisit;
 if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>10*1024*1024){notice('Pilih foto JPEG/PNG/WebP maksimal 10 MiB.',true);input.value='';return;}
 if(hotelWorking){notice('Tunggu proses sebelumnya selesai.',true);input.value='';return;}
 hotelWorking=true;input.disabled=true;notice('Mengunggah foto. Tunggu konfirmasi server…');
 try{const response=await fetch(`/hotel-visits/${v.id}/devices/${input.dataset.hotelPhoto}/photos?expected_version=${v.version}`,{method:'POST',headers:{Authorization:`Bearer ${state.token}`,'Content-Type':file.type},body:file});const result=await response.json().catch(()=>({}));if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Foto tidak dapat disimpan. Muat ulang dan periksa status.');await openHotelVisit(v.id);notice('Foto berhasil tersimpan pada perangkat dan kunjungan ini.');}catch(error){notice(error.message||'Koneksi terputus; periksa status foto sebelum mencoba lagi.',true);}finally{hotelWorking=false;input.disabled=false;input.value='';}
});

async function appendMaintenanceReview(v){
 if(!v.sampling_coverage)return;
 const info=await api(`/hotel-visits/${v.id}/completion`);
 if(state.hotelVisit?.id!==v.id)return;
 const panel=document.createElement('section');panel.className='card';
 const points=v.sampling_coverage.floors.map(f=>`<h3>${esc(f.name)}</h3>${f.points.map(p=>{
  const o=p.observation||{},n=o.notes||{},c=o.wifi_connection||{};
  return `<article class="detail-content"><h4>${esc(p.name)}</h4><p>${esc(c.ssid||'SSID belum terbaca')} · ${esc(c.bssid||'—')} · ${esc(c.rssi_dbm??'—')} dBm · ${esc(c.frequency_mhz??'—')} MHz</p><p>Temuan dan Tindakan: ${esc([n.notes,n.findings?'Temuan: '+n.findings:'',n.action?'Tindakan: '+n.action:''].filter(Boolean).join('\n')||'—')}</p>${(p.speedtests||[]).map(a=>`<p>${esc(a.status)} · ${esc(a.created_at)} · ↓ ${esc(a.run?.metrics?.download_mbps??'—')} / ↑ ${esc(a.run?.metrics?.upload_mbps??'—')} Mbps · Ping ${esc(a.run?.metrics?.ping_ms??'—')} ms ${esc(a.error||'')}</p>`).join('')}</article>`;
 }).join('')}`).join('');
 panel.innerHTML=`<div class="detail-content"><h2>Review area, PIC & PDF</h2>${points}<p>${info.signature?'PIC: '+esc(info.signature.name)+' · '+esc(info.signature.position)+' · '+esc(date(info.signature.signed_at)):'Belum ada tanda tangan PIC terbaru.'}</p><ul>${info.errors.map(e=>`<li>${esc(e)}</li>`).join('')}</ul><button class="secondary" data-hotel-pdf="preview">Review Hasil PDF</button>${info.pdf_available?'<button class="primary" data-hotel-pdf="final">Unduh PDF bertanda tangan</button>':''}<div class="photo-grid">${(v.evidence||[]).map(p=>`<figure><img data-evidence-id="${esc(p.id)}" alt="${esc(p.caption||p.category)}"><figcaption>${esc(p.category)} · ${esc(p.caption)}</figcaption></figure>`).join('')}</div></div>`;
 $('#page-content').append(panel);
 await Promise.all((v.evidence||[]).map(async photo=>{try{const data=await api(`/hotel-visits/${v.id}/evidence/${photo.id}/thumbnail`);if(state.hotelVisit?.id!==v.id)return;const img=$(`[data-evidence-id="${photo.id}"]`);if(img)img.src='data:image/jpeg;base64,'+data.image_base64;}catch{/* Evidence remains available through authenticated PDF. */}}));
}
async function downloadHotelPdf(preview){
 const v=state.hotelVisit,data=await api(`/hotel-visits/${v.id}/${preview?'report-preview-download':'report-download'}`);
 const bytes=Uint8Array.from(atob(data.data_base64),c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'}));
 const link=document.createElement('a');link.href=url;link.download=data.filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
}

function foldMaintenanceReport(html){
 const root=document.createElement('template');root.innerHTML=html;
 for(const section of root.content.querySelectorAll('.report-section')){
  const title=section.querySelector(':scope>h3');
  if(title&&['Informasi site','LOCAL AREA NETWORK'].includes(title.textContent)){
   const details=document.createElement('details');details.className='report-section report-fold';const summary=document.createElement('summary');summary.textContent=title.textContent==='Informasi site'?'Informasi Pelanggan':'Local Area Network';title.remove();details.append(summary,...section.childNodes);section.replaceWith(details);
  }
 }
 for(const fieldset of root.content.querySelectorAll('[data-backbone]')){
  const details=document.createElement('details');details.className='report-fold';const summary=document.createElement('summary');summary.textContent=fieldset.dataset.backbone==='fo'?'Backbone Fiber Optic':'Wireless Backbone';fieldset.replaceWith(details);details.append(summary,fieldset);
 }
 return root.innerHTML;
}
document.querySelector('#editor-form').addEventListener('invalid',event=>{for(let el=event.target.parentElement;el;el=el.parentElement)if(el.tagName==='DETAILS')el.open=true;},true);
