'use strict';
let samplingView=null;
let samplingWrites=Promise.resolve();
let samplingUrls=[];
const samplingCategories=['Foto Access Point','Foto perangkat jaringan','Foto area sampling','Foto temuan/kerusakan'];
function clearSampling(){samplingView=null;for(const url of samplingUrls)URL.revokeObjectURL(url);samplingUrls=[];const preview=$('#sampling-photo-dialog');if(preview){preview.close();preview.remove();}}
function samplingEditable(v){return state.user?.role==='technician'&&state.user.id===v.visit.technician_id&&['in_progress','revision_requested'].includes(v.visit.status);}
function samplingScope(visit){return `user:${state.user.id}:visit:${visit.id}:`;}
function samplingDraftKey(v,id){return v.scope+'draft:'+id;}
function samplingMessage(message,error=false){const el=$('#sampling-feedback');if(el){el.textContent=message;el.classList.toggle('sampling-error',error);el.setAttribute('role',error?'alert':'status');}const badge=$('#sampling-sync-label');if(badge)badge.textContent=error?'Gagal menyimpan perubahan':message.includes('Menyimpan')?'Menyimpan draf…':'Perubahan belum disinkronkan';}
function samplingQueue(task,view){
 view.pending=(view.pending||0)+1;
 const write=samplingWrites.catch(()=>{}).then(task);samplingWrites=write;
 write.then(()=>{view.pending--;if(samplingView===view){view.storageError=null;samplingMessage(view.pending?'Menyimpan draf lokal…':'Draf tersimpan di perangkat ini · belum tersinkron ke server');}},error=>{view.pending--;if(samplingView===view){view.storageError=error.message;samplingMessage(error.message,true);}});
 return write;
}
async function openSampling(visitId){
 clearSampling();if(typeof hotelDetailView!=='undefined')hotelDetailView=null;state.visit=null;state.page='hotelvisits';nav();
 const userId=state.user?.id;if(!userId)return;
 const loading=document.createElement('div');loading.className='sampling-app';loading.innerHTML='<p role="status">Memuat dashboard sampling…</p>';
 $('#page-content').replaceChildren(loading);
 try{
  let visit;
  if(!navigator.onLine&&state.hotelVisit?.id===visitId)visit=state.hotelVisit;
  else visit=await api('/hotel-visits/'+visitId);
  if(state.user?.id!==userId||!loading.isConnected)return;
  const view={visit,scope:samplingScope(visit),configKey:`user:${userId}:hotel:${visit.hotel_id}:sampling-floors`,configuration:[],drafts:{},photos:[],floor:null,point:null,tab:'analyzer',band:'band_24',storageError:null};
  try{
   const [config,drafts,photos,outbox]=await Promise.all([SamplingStore.get(view.configKey),SamplingStore.list(view.scope+'draft:'),SamplingStore.list(view.scope+'photo:'),SamplingStore.list(view.scope+'observation-outbox:')]);
   view.configuration=config||[];view.drafts=Object.fromEntries(drafts.map(row=>[row.pointId,row]));view.photos=photos;
   view.noteConflicts=Object.fromEntries(outbox.filter(row=>row.conflict).map(row=>[row.key.slice((view.scope+'observation-outbox:').length),true]));
  }catch(error){view.storageError=error.message;}
  if(state.user?.id!==userId||!loading.isConnected)return;
  await samplingLoadCoverage(view);
  if(state.user?.id!==userId||!loading.isConnected)return;
  state.hotelVisit=visit;samplingView=view;renderSampling();
 }catch(error){if(loading.isConnected){loading.innerHTML=`<p role="alert">${esc(error.message)}</p><button type="button" data-sampling-retry="${esc(visitId)}">Coba lagi</button><button type="button" data-sampling-report="${esc(visitId)}">Kembali ke laporan</button>`;}}
}
function samplingPoints(v){
 if(v.coverage)return v.coverage.floors.map(f=>({id:f.id,name:f.name,target:f.target_count,
  points:f.points.map(session=>({id:session.id,name:session.name,session}))}));
 return samplingFloors(v.visit,v.configuration,v.drafts);
}
function samplingFindPoint(v){return samplingPoints(v).flatMap(f=>f.points).find(p=>p.id===v.point);}
function samplingCounts(points,v){return {done:points.filter(p=>samplingStatus(p,v.drafts[p.id])!=='untested').length,findings:points.filter(p=>['attention','problem'].includes(samplingStatus(p,v.drafts[p.id]))).length};}
function samplingPill(point,v){const status=samplingStatus(point,v.drafts[point.id]);return `<span class="sampling-pill ${esc(status)}">${esc(samplingStatusLabels[status])}${v.drafts[point.id]?.status?' · lokal':''}</span>`;}
function samplingNumber(value,unit){return value==null?'Belum diuji':`${esc(value)} <small>${esc(unit)}</small>`;}
function samplingNetwork(){
 const fields=['SSID','BSSID','Nama AP','Band','Frequency (MHz)','Channel','RSSI (dBm)','Link speed','IP address lokal','Gateway','Connection status'];
 return `<section class="sampling-card"><div class="sampling-card-title"><div><p class="sampling-kicker">CONNECTED NETWORK</p><h3>Jaringan Wi-Fi aktif</h3></div><span class="sampling-pill untested">Belum tersedia</span></div><p class="sampling-explanation">Informasi koneksi HP memerlukan plugin Android native. AP belum teridentifikasi; nama inventaris pada titik ini bukan bukti HP terhubung ke AP tersebut.</p><dl class="sampling-network">${fields.map(name=>`<div><dt>${name}</dt><dd>Belum tersedia</dd></div>`).join('')}</dl><details><summary>Izin Wi-Fi & lokasi</summary><p>Di aplikasi Android nanti, izinkan Nearby Wi-Fi dan lokasi sesuai versi Android, serta aktifkan layanan lokasi bila diminta sistem. Jika izin ditolak, buka Setelan → Aplikasi → Izin. Browser ini tidak mempunyai akses radio Wi-Fi; izin lokasi browser tidak mengaktifkan fitur scan.</p></details></section>`;
}
function samplingAnalyzer(v,point){
 const b=point.item?.result?.[v.band];
 return `<section class="sampling-card"><div class="sampling-card-title"><div><p class="sampling-kicker">WIFI ANALYZER</p><h3>Lingkungan radio</h3></div><span class="sampling-pill untested">Belum tersedia</span></div><div class="sampling-band" role="group" aria-label="Band analyzer">${[['band_24','2.4 GHz'],['band_5','5 GHz']].map(([key,label])=>`<button type="button" data-sampling-band="${key}" aria-pressed="${v.band===key}">${label}</button>`).join('')}</div><div class="sampling-empty"><span class="sampling-empty-symbol" aria-hidden="true">⌁</span><h4>Belum ada hasil scan radio</h4><p>Jumlah jaringan, SSID/BSSID, RSSI, channel, frequency dan security belum tersedia.</p><p>Scan terakhir: belum tersedia. Tidak ada hasil scan baru maupun cache OS yang diterima.</p></div><p class="sampling-explanation">${v.band==='band_24'?'Visualisasi overlap channel akan dibuat dari scan aktual 2.4 GHz.':'Kepadatan channel 5 GHz nanti merupakan estimasi berdasarkan scan, bukan pengukuran interferensi radio yang pasti.'} Android dapat membatasi frekuensi scan; hasil cache harus ditandai waktu dan sumbernya.</p><div class="sampling-actions"><button type="button" disabled>Pindai Wi-Fi · belum tersedia</button><button type="button" disabled>Simpan scan ke titik · belum tersedia</button></div>${b?.status==='measured'?`<div class="sampling-historical"><h4>Hasil tersimpan · input manual</h4><p>${esc(b.signal_dbm??'—')} dBm · Channel ${esc(b.channel??'—')} · ${esc(b.ssid||'SSID belum dicatat')} · ${esc(b.bssid||'BSSID belum dicatat')}</p><p>Data laporan terdahulu ini bukan hasil scan atau koneksi aktif.</p></div>`:''}</section>`;
}
function samplingSpeed(v,point){
 const records=(point.item?.speedtests||[]).slice().reverse();
 return `<section class="sampling-card"><div class="sampling-card-title"><div><p class="sampling-kicker">LIBRESPEED</p><h3>Uji koneksi titik sampling</h3></div><span class="sampling-pill">${records.length?'Riwayat tersedia':'Belum diuji'}</span></div><p class="sampling-explanation">Pengujian nyata memakai server aplikasi yang sudah dikonfigurasi. Dialog menampilkan progress dan menyimpan hasil ke AP terpilih. Akses tunnel/lokal hanya diagnostik. Browser belum dapat memastikan trafik terikat ke Wi-Fi hotel; hasil Wi-Fi memerlukan konfirmasi dan konteks yang diterima server.</p><div class="sampling-measurements">${[['DOWNLOAD','Mbps'],['UPLOAD','Mbps'],['PING','ms'],['JITTER','ms']].map(([label,unit])=>`<div><span>${label}</span><strong>—</strong><small>${unit}</small></div>`).join('')}</div><p>Angka pengukuran aktif ditampilkan dalam dialog saat pengujian dimulai.</p>${point.item&&samplingEditable(v)?`<button type="button" data-sampling-speed="${esc(point.item.id)}" ${!navigator.onLine?'disabled':''}>Mulai Speedtest</button>`:'<p class="sampling-explanation">'+(point.item?'Pengujian hanya tersedia bagi teknisi pada kunjungan yang dapat diedit.':'Pilih AP inventaris melalui “Pilih AP sampling” di laporan untuk menghubungkan titik ke server sebelum menguji.')+'</p>'}<p class="sampling-explanation">Jaringan seluler, koneksi tidak diketahui dan diagnostik tidak boleh dianggap hasil Wi-Fi lapangan. Pengujian menangani timeout dan perubahan jaringan yang dapat dideteksi browser; verifikasi native menyusul Phase C.</p><div class="sampling-run-list">${records.length?records.map(run=>{
 const m=run.status==='completed'?run.metrics:null;const duration=run.finished_at&&run.created_at?(new Date(run.finished_at)-new Date(run.created_at))/1000:null;
 return `<article class="sampling-run"><div class="sampling-card-title"><strong>${esc(samplingBand(run.band))}</strong><span class="sampling-pill">${esc(({completed:'Selesai',failed:'Gagal',aborted:'Dibatalkan',running:'Sedang diuji'})[run.status]||run.status)}</span></div><p>${esc(date(run.finished_at||run.created_at))} · ${run.context?.transport==='direct_https'?'HTTPS langsung':'Diagnostik tunnel/lokal'}</p><div class="sampling-measurements">${[['Download',m?.download_mbps,'Mbps'],['Upload',m?.upload_mbps,'Mbps'],['Ping',m?.ping_ms,'ms'],['Jitter',m?.jitter_ms,'ms']].map(([name,value,unit])=>`<div><span>${name}</span><strong>${samplingNumber(value,unit)}</strong></div>`).join('')}</div><p>Server: ${esc(run.context?.endpoint_origin||'Belum tersedia')} · Durasi sesi: ${duration!=null&&Number.isFinite(duration)?esc(Math.max(0,duration).toFixed(1))+' detik':'Belum tersedia'}</p>${run.error?`<p class="sampling-error">${esc(run.error)}</p>`:''}</article>`;
 }).join(''):'<div class="sampling-empty"><h4>Belum diuji</h4><p>Belum ada hasil speedtest tersimpan pada titik ini.</p></div>'}</div></section>`;
}
function samplingNotes(v,point){
 const saved=point.session?.observation;
 const draft=v.drafts[point.id]||(saved?{...saved.notes,status:saved.notes.condition}:{}),locked=!samplingEditable(v)||v.observationBusy;
 const local=v.photos.filter(photo=>photo.pointId===point.id),remote=point.item?.photos||[];
 return `<section class="sampling-card"><p class="sampling-kicker">DOKUMENTASI</p><h3>Foto & Catatan</h3><p class="sampling-explanation">Foto dan catatan disimpan sebagai draf lokal. Catatan sesi dapat dikirim dengan tombol simpan ketika fitur tersedia. Foto lokal belum memenuhi kewajiban foto checkout.</p><fieldset class="sampling-note-fields" ${locked?'disabled':''}><legend>Catatan titik sampling</legend><label>Lokasi sampling<input data-sampling-note="location" ${point.session?'disabled':''} maxlength="200" value="${esc(draft.location||point.name)}"></label><label>Status titik<select data-sampling-note="status">${['untested','good','attention','problem'].map(status=>`<option value="${status}" ${(draft.status||samplingStatus(point,null))===status?'selected':''}>${samplingStatusLabels[status]}</option>`).join('')}</select></label>${[['notes','Catatan Teknisi'],['findings','Deskripsi temuan'],['action','Tindakan teknisi'],['recommendation','Rekomendasi tindak lanjut']].map(([key,label])=>`<label>${label}<textarea data-sampling-note="${key}" maxlength="5000" rows="3">${esc(draft[key]||'')}</textarea></label>`).join('')}<div class="sampling-photo-controls"><label>Kategori dokumentasi<select id="sampling-photo-category">${samplingCategories.map(category=>`<option>${category}</option>`).join('')}</select></label><label>Keterangan foto (opsional)<input id="sampling-photo-caption" maxlength="500"></label><label class="sampling-upload">Ambil / pilih foto<input id="sampling-photo-file" type="file" accept="image/jpeg,image/png,image/webp" capture="environment"></label></div></fieldset><div class="sampling-photo-grid">${local.map(photo=>`<article><button type="button" class="sampling-photo-preview" data-sampling-photo="${esc(photo.id)}"><img data-sampling-image="${esc(photo.id)}" alt="${esc(photo.category)}"><span>Lihat foto ukuran penuh</span></button><strong>${esc(photo.category)}</strong><small>${esc(date(photo.createdAt))} · Draf lokal, belum disinkronkan</small><p>${esc(photo.caption||'')}</p>${!locked?`<button type="button" class="sampling-delete" data-sampling-delete="${esc(photo.id)}">Hapus foto lokal</button>`:''}</article>`).join('')}${remote.map(photo=>`<article><button type="button" class="sampling-photo-preview" data-sampling-remote="${esc(photo.id)}"><img data-sampling-server-image="${esc(photo.id)}" alt="Foto AP tersimpan di server"><span>Lihat foto ukuran penuh</span></button><strong>Foto server · kategori belum tersedia</strong><small>${esc(date(photo.created_at))} · Tersinkron</small></article>`).join('')}</div>${!local.length&&!remote.length?'<div class="sampling-empty"><h4>Belum ada foto</h4><p>Dokumentasikan AP dan kondisi titik sampling.</p></div>':''}</section>`;
}
function samplingSyncNotice(v){
 const local=v.configuration.length||Object.keys(v.drafts).length||v.photos.length;
 return `<div class="sampling-sync"><details><summary><span id="sampling-sync-label" class="v2-chip attention">${v.storageError?'Gagal menyimpan perubahan':local?'Perubahan belum disinkronkan':'Penyimpanan lokal'}</span> <span class="sync-detail-label">Detail</span></summary><p>Konfigurasi lokal lama dan foto baru belum disinkronkan. Catatan sesi bisa dikirim melalui tombol simpan jika tersedia.</p><p>Draf lokal tidak dihitung sebagai pemeriksaan selesai dan foto lokal belum memenuhi kewajiban laporan.</p></details><p id="sampling-feedback" class="sampling-feedback ${v.storageError?'sampling-error':''}" role="${v.storageError?'alert':'status'}">${esc(v.storageError||'')}</p></div>`;
}
function renderSampling(){
 const v=samplingView;if(!v||!state.user)return;
 for(const url of samplingUrls)URL.revokeObjectURL(url);samplingUrls=[];
 const floors=samplingPoints(v),floor=floors.find(f=>f.id===v.floor),point=floor?.points.find(p=>p.id===v.point);
 const all=floors.flatMap(f=>f.points),counts=samplingCounts(all,v),percent=all.length?Math.round(counts.done/all.length*100):0;
 const site=v.visit.site?.name||visitHotel(v.visit),editable=samplingEditable(v);
 nav();setBreadcrumb([{label:'Maintenance Hotel',page:'hotelvisits'},{label:site,hotel:v.visit.hotel_id},...(floor?[{label:'Lantai '+floor.name}]:[]),...(point?[{label:v.drafts[point.id]?.location||point.name}]:[])]);
 let content='';
 if(!floor){
  content=v2SamplingDashboard(v,floors);
 }else if(!point){
  const c=samplingCounts(floor.points,v);
  content=`<section class="sampling-card"><div class="sampling-card-title"><div><p class="sampling-kicker">DETAIL LANTAI</p><h3>${esc(floor.name)}</h3></div><span class="sampling-pill">${c.done}/${floor.points.length} dicatat</span></div><button type="button" data-site-detail="${esc(v.visit.hotel_id)}" data-return-tab="floors">Atur lantai di Data Hotel →</button></section><div class="sampling-floor-grid">${floor.points.map(p=>{
 const d=v.drafts[p.id],m=samplingMetrics(p.item);
 return `<article class="sampling-card"><div class="sampling-card-title"><h3>${esc(d?.location||p.name)}</h3>${samplingPill(p,v)}</div><p>${p.session?esc(p.session.device?.name||'AP belum dihubungkan'):p.item?esc(p.item.device.name):'Belum dihubungkan ke AP inventaris'}</p><div class="sampling-point-metrics"><div><span>RSSI terakhir</span><strong>${samplingNumber(m.signal,'dBm')}</strong></div><div><span>Download terakhir</span><strong>${samplingNumber(m.download,'Mbps')}</strong></div><div><span>Band terakhir</span><strong>${esc(m.band||'Belum diuji')}</strong></div><div><span>Waktu pemeriksaan</span><strong>${esc(date(d?.updatedAt||m.time))}</strong></div></div><p class="sampling-explanation">${esc(m.source||'Belum ada hasil pengukuran')}${d?.updatedAt?' · ada draf lokal':''}</p><button type="button" data-sampling-point="${esc(p.id)}">Detail titik sampling →</button></article>`;
 }).join('')}</div>`;
 }else{
  const draft=v.drafts[point.id];
  content=`<section class="sampling-point-heading"><div><p class="sampling-kicker">DETAIL TITIK SAMPLING</p><h2>${esc(draft?.location||point.name)}</h2><p>${esc(site)} · Lantai ${esc(floor.name)} · ${point.session?esc(point.session.device?.name||'AP belum dihubungkan'):point.item?esc(point.item.device.name):'AP belum dipilih'}</p><p>Waktu pemeriksaan: ${esc(date(draft?.updatedAt||samplingMetrics(point.item).time))}</p></div>${samplingPill(point,v)}</section>${samplingNetwork()}<div class="sampling-tabs" role="tablist" aria-label="Pengujian sampling">${[['analyzer','Wi-Fi Analyzer'],['speed','Speedtest'],['notes','Foto & Catatan']].map(([key,label])=>`<button type="button" id="sampling-tab-${key}" role="tab" data-sampling-tab="${key}" aria-selected="${v.tab===key}" aria-controls="sampling-panel" tabindex="${v.tab===key?'0':'-1'}">${label}</button>`).join('')}</div><div role="tabpanel" id="sampling-panel" aria-labelledby="sampling-tab-${v.tab}">${v.tab==='analyzer'?samplingAnalyzer(v,point):v.tab==='speed'?samplingSpeed(v,point):samplingObservationPanel(v,point)+samplingNotes(v,point)}</div>`;
 }
 $('#page-content').innerHTML=`<div class="sampling-app"><div class="sampling-toolbar"><button type="button" class="sampling-back" data-sampling-back>${floor?'← '+(point?'Detail lantai':'Pilih lantai'):'← Maintenance Hotel'}</button><span id="sampling-connectivity" class="sampling-pill ${navigator.onLine?'':'attention'}">${navigator.onLine?'Online':'Offline · draf lokal'}</span></div>${!point?`<header class="sampling-header"><p class="sampling-kicker">HOTEL NETWORK / SAMPLING</p><h2>${esc(site)}</h2><p>Periode kunjungan ${esc(v.visit.planned_date)} · ${esc(title(v.visit.status))}</p></header>`:''}${samplingSyncNotice(v)}<div class="sampling-actions"><button type="button" data-sampling-report="${esc(v.visit.id)}">Laporan utama${v.visit.status==='assigned'?' / mulai pemeriksaan':''}</button><button type="button" data-site-detail="${esc(v.visit.hotel_id)}">Detail Hotel</button></div>${!editable?'<p class="sampling-feedback">Mode baca: penugasan ini belum dimulai, sudah dikirim, atau bukan milik akun teknisi ini.</p>':''}${samplingCoveragePanel(v)}${content}</div>`;
 if(point&&v.tab==='notes')loadSamplingPhotos(v,point);
}
async function loadSamplingPhotos(v,point){
 for(const photo of v.photos.filter(p=>p.pointId===point.id)){
  const img=$(`[data-sampling-image="${photo.id}"]`);if(img){const url=URL.createObjectURL(photo.blob);samplingUrls.push(url);img.src=url;}
 }
 for(const photo of point.item?.photos||[]){
  const img=$(`[data-sampling-server-image="${photo.id}"]`);
  try{
   const response=await fetch(photo.url,{headers:{Authorization:`Bearer ${state.token}`},cache:'no-store'});if(!response.ok)throw new Error();
   const blob=await response.blob();if(!img?.isConnected||samplingView!==v)continue;
   const url=URL.createObjectURL(blob);samplingUrls.push(url);img.src=url;
  }catch{if(img?.isConnected)img.alt='Foto belum dapat dimuat. Periksa koneksi dan buka ulang tab.';}
 }
}
function previewSamplingPhoto(img){
 if(!img?.getAttribute('src')){samplingMessage('Foto belum dapat dimuat.',true);return;}
 let modal=$('#sampling-photo-dialog');if(!modal){modal=document.createElement('dialog');modal.id='sampling-photo-dialog';document.body.append(modal);}
 modal.innerHTML=`<button type="button" aria-label="Tutup foto" data-sampling-close-photo>Tutup foto ×</button><img src="${esc(img.src)}" alt="${esc(img.alt)}">`;modal.showModal();
}
document.addEventListener('input',event=>{
 const control=event.target.closest('[data-sampling-note]'),v=samplingView;if(!control||!v||!samplingEditable(v))return;
 const point=samplingFindPoint(v);if(!point)return;
 const previous=v.drafts[point.id]||(point.session?.observation?{...point.session.observation.notes,status:point.session.observation.notes.condition}:{});
 const draft={...previous,baseVisitVersion:previous.baseVisitVersion??v.visit.version,baseSessionVersion:previous.baseSessionVersion??point.session?.version,pointId:point.id,updatedAt:new Date().toISOString(),[control.dataset.samplingNote]:control.value};v.drafts[point.id]=draft;
 samplingMessage('Menyimpan draf lokal…');samplingQueue(()=>SamplingStore.put(samplingDraftKey(v,point.id),draft),v);
});
document.addEventListener('change',async event=>{
 if(event.target.id!=='sampling-photo-file')return;
 const v=samplingView,point=v&&samplingFindPoint(v),file=event.target.files?.[0];
 if(!file||!point||!samplingEditable(v))return;
 if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>10*1024*1024){samplingMessage('Pilih foto JPEG, PNG atau WebP maksimal 10 MiB.',true);event.target.value='';return;}
 if(v.photos.filter(p=>p.pointId===point.id).length>=10){samplingMessage('Maksimal 10 foto lokal per titik.',true);return;}
 const photo={id:samplingId(),pointId:point.id,category:$('#sampling-photo-category').value,caption:$('#sampling-photo-caption').value.trim(),createdAt:new Date().toISOString(),syncStatus:'local',blob:file};
 const key=v.scope+'photo:'+photo.id;
 try{await samplingQueue(()=>SamplingStore.put(key,photo),v);v.photos.push({...photo,key});if(samplingView===v)renderSampling();}catch{}
});
document.addEventListener('submit',async event=>{
 if(!['sampling-add-floor','sampling-target'].includes(event.target.id))return;
 event.preventDefault();const v=samplingView;if(!v||!samplingEditable(v))return;
 const data=new FormData(event.target),target=Number(data.get('target'));
 if(!Number.isInteger(target)||target<1||target>100){samplingMessage('Target titik harus antara 1 dan 100.',true);return;}
 const floors=samplingPoints(v);let configuration;
 if(event.target.id==='sampling-add-floor'){
  const name=String(data.get('floor')||'').trim();if(!name){samplingMessage('Isi nama lantai.',true);return;}
  if(floors.some(f=>f.name.toLocaleLowerCase()===name.toLocaleLowerCase())){samplingMessage('Lantai sudah ada. Atur target melalui Detail Lantai.',true);return;}
  configuration=[...v.configuration,{id:samplingId(),name,target}];
 }else{
  const floor=floors.find(f=>f.id===v.floor);if(!floor)return;
  configuration=[...v.configuration.filter(f=>f.id!==floor.id),{id:floor.id,name:floor.name,target}];
 }
 try{await samplingQueue(()=>SamplingStore.put(v.configKey,configuration),v);v.configuration=configuration;if(samplingView===v)renderSampling();}catch{}
});
document.addEventListener('click',async event=>{
 const button=event.target.closest('button');if(!button)return;
 if(button.hasAttribute('data-sampling-open')){await samplingWrites.catch(()=>{});await openSampling(state.hotelVisit.id);return;}
 if(button.dataset.samplingRetry){await openSampling(button.dataset.samplingRetry);return;}
 if(button.dataset.samplingReport){const id=button.dataset.samplingReport;clearSampling();await openHotelVisit(id);return;}
 if(button.hasAttribute('data-sampling-close-photo')){$('#sampling-photo-dialog')?.close();return;}
 const v=samplingView;if(!v)return;
 if(button.hasAttribute('data-sampling-back')){
  await samplingWrites.catch(()=>{});
  if(v.point){v.point=null;renderSampling();}else if(v.floor){v.floor=null;renderSampling();}else{const hotelId=v.visit.hotel_id;clearSampling();await selectMaintenanceHotel(hotelId);}return;
 }
 if(button.dataset.samplingFloor){v.floor=button.dataset.samplingFloor;v.point=null;renderSampling();return;}
 if(button.dataset.samplingPoint){v.point=button.dataset.samplingPoint;v.tab='analyzer';renderSampling();return;}
 if(button.dataset.samplingTab){v.tab=button.dataset.samplingTab;renderSampling();$(`[data-sampling-tab="${v.tab}"]`)?.focus();return;}
 if(button.dataset.samplingBand){v.band=button.dataset.samplingBand;renderSampling();return;}
 if(button.dataset.samplingSpeed&&samplingEditable(v)){if(navigator.onLine){speedDialog(button.dataset.samplingSpeed);$('#speed-dialog').addEventListener('close',()=>{if(samplingView===v&&state.hotelVisit?.id===v.visit.id){v.visit=state.hotelVisit;renderSampling();}},{once:true});}return;}
 if(button.dataset.samplingPhoto){previewSamplingPhoto($(`[data-sampling-image="${button.dataset.samplingPhoto}"]`));return;}
 if(button.dataset.samplingRemote){previewSamplingPhoto($(`[data-sampling-server-image="${button.dataset.samplingRemote}"]`));return;}
 if(button.dataset.samplingDelete&&samplingEditable(v)){
  const photo=v.photos.find(p=>p.id===button.dataset.samplingDelete);if(!photo||photo.pointId!==v.point)return;
  if(!window.confirm('Hapus foto draf lokal ini? Foto belum pernah dikirim ke server.'))return;
  try{await samplingQueue(()=>SamplingStore.remove(photo.key),v);v.photos=v.photos.filter(p=>p.id!==photo.id);if(samplingView===v)renderSampling();}catch{}
 }
});
document.addEventListener('keydown',event=>{
 const tab=event.target.closest('[data-sampling-tab]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 event.preventDefault();const tabs=['analyzer','speed','notes'];let index=tabs.indexOf(tab.dataset.samplingTab);
 index=event.key==='Home'?0:event.key==='End'?2:(index+(event.key==='ArrowRight'?1:2))%3;
 samplingView.tab=tabs[index];renderSampling();$(`[data-sampling-tab="${tabs[index]}"]`).focus();
});
for(const name of ['online','offline'])window.addEventListener(name,()=>{
 const v=samplingView;if(!v)return;const el=$('#sampling-connectivity');
 if(el){el.textContent=navigator.onLine?'Online':'Offline · draf lokal';el.classList.toggle('attention',!navigator.onLine);}
 const start=$('[data-sampling-speed]');if(start)start.disabled=!navigator.onLine;
});

window.addEventListener('beforeunload',event=>{
 if(samplingView?.pending){event.preventDefault();event.returnValue='';}
});
