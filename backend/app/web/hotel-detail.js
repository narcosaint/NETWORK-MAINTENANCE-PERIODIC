'use strict';
let hotelDetailView=null;
let hotelDetailRequest=0;
const hotelTabs={info:'Informasi Hotel',floors:'Lantai',points:'Area Sampling',history:'Riwayat Maintenance'};
function setBreadcrumb(items){
 $('#breadcrumb').innerHTML=items.map((item,index)=>`${index?'<span class="slash"> / </span>':''}${item.page?`<button class="link-button" data-page="${esc(item.page)}">${esc(item.label)}</button>`:item.hotel?`<button class="link-button" data-maintenance-hotel="${esc(item.hotel)}">${esc(item.label)}</button>`:`<span aria-current="location">${esc(item.label)}</span>`}`).join('');
}
async function openHotelDetail(id,tab='info'){
 const hotel=find('hotels',id);if(!hotel){notice('Hotel tidak tersedia untuk akun ini.',true);return;}
 const request=++hotelDetailRequest,userId=state.user.id;
 clearSampling();clearHotelPhotos();state.hotelVisit=null;state.visit=null;state.page='hotels';
 const view={hotel,tab:hotelTabs[tab]?tab:'floors',configuration:[],visits:[],error:null,storageError:null,configKey:`user:${userId}:hotel:${id}:sampling-floors`};
 hotelDetailView=view;nav();$('#page-content').innerHTML='<p class="loading" role="status">Memuat Detail Hotel…</p>';
 const visits=(state.data.hotelvisits||[]).filter(v=>v.hotel_id===id).sort((a,b)=>b.planned_date.localeCompare(a.planned_date)||String(b.created_at).localeCompare(String(a.created_at)));
 const [config,details]=await Promise.allSettled([SamplingStore.get(view.configKey),Promise.all(visits.map(v=>api('/hotel-visits/'+v.id))),samplingLoadHotelMaster(view)]);
 if(request!==hotelDetailRequest||hotelDetailView!==view||state.user?.id!==userId||state.page!=='hotels')return;
 if(config.status==='fulfilled')view.configuration=config.value||[];else view.storageError=config.reason.message;
 if(details.status==='fulfilled')view.visits=details.value;else view.error=details.reason.message;
 renderHotelDetail();
}
function hotelDetailFloors(v){
 const seen=new Set(),devices=[];
 for(const visit of v.visits)for(const item of visit.devices||[]){
  const key=JSON.stringify([item.device_id||item.device.id,item.floor,item.point]);
  if(item.device.device_type==='ap'&&!seen.has(key)){seen.add(key);devices.push({...item,visitId:visit.id});}
 }
 return samplingFloors({devices},v.configuration,{});
}
function hotelDetailTarget(floor){return `<form class="hotel-floor-target" data-floor-config="${esc(floor.id)}"><label>Target area sampling<input name="target" type="number" min="1" max="100" value="${floor.target}" required></label><button class="secondary" type="submit">Simpan target</button></form>`;}
function renderHotelDetail(){
 if(hotelDetailView?.tab==='devices')hotelDetailView.tab='info';
 const v=hotelDetailView;if(!v||state.page!=='hotels'||!state.user)return;
 nav();setBreadcrumb([{label:'Data Hotel',page:'hotels'},{label:v.hotel.name},{label:hotelTabs[v.tab]}]);
 const floors=hotelDetailFloors(v),inventory=(state.data.devices||[]).filter(d=>d.hotel_id===v.hotel.id);
 let content='';
 if(v.tab==='info')content=`<section class="card"><div class="card-heading"><h3>Informasi Hotel</h3>${supervisor()?`<button class="secondary" data-edit="hotels" data-id="${esc(v.hotel.id)}">Ubah informasi</button>`:''}</div><dl class="v2-info"><div><dt>Nama hotel</dt><dd>${esc(v.hotel.name)}</dd></div><div><dt>Pelanggan / perusahaan</dt><dd>${esc(v.hotel.customer_name||v.hotel.name)}</dd></div><div><dt>Alamat</dt><dd>${esc(v.hotel.address||'Belum tersedia')}</dd></div><div><dt>Inventaris perangkat</dt><dd>${inventory.length} perangkat</dd></div><div><dt>Profil layanan FO</dt><dd>${esc(v.hotel.maintenance_profile?.fo?.download_mbps??'Belum tersedia')} / ${esc(v.hotel.maintenance_profile?.fo?.upload_mbps??'Belum tersedia')} Mbps (download / upload)</dd></div><div><dt>Profil layanan wireless</dt><dd>${esc(v.hotel.maintenance_profile?.wireless?.download_mbps??'Belum tersedia')} / ${esc(v.hotel.maintenance_profile?.wireless?.upload_mbps??'Belum tersedia')} Mbps (download / upload)</dd></div></dl></section>`;

 if(v.tab==='devices')content=`<section class="card"><div class="card-heading"><div><h3>Inventaris perangkat</h3><p>${inventory.length} perangkat di hotel ini</p></div>${supervisor()?'<button class="primary" data-create="devices">＋ Tambah perangkat</button>':''}</div>${table(['Perangkat / model','Hotel','Jenis','Lokasi / IP','Serial / MAC','Tindakan'],resourceRows('devices',inventory))}</section>`;
 if(v.tab==='floors')content=`<p class="detail-note"><strong>Konfigurasi lokal · belum tersinkronisasi</strong><br>Disimpan untuk akun dan browser ini. Default 2 area per lantai.</p><div class="hotel-grid">${floors.map(f=>`<section class="card"><div class="detail-content"><h3>Lantai ${esc(f.name)}</h3><p>${f.points.length} area sampling · target ${f.target}</p><button class="link-button" data-site-floor="${esc(f.id)}">Lihat area sampling →</button>${hotelDetailTarget(f)}</div></section>`).join('')}</div>${!floors.length?empty('Belum ada lantai.','Tambahkan lantai hotel; target awal 2 area sampling.'):''}<section class="card"><div class="detail-content"><h3>Tambah lantai</h3><form id="hotel-add-floor" class="hotel-floor-target"><label>Nama lantai<input name="floor" maxlength="100" required></label><label>Target area sampling<input name="target" type="number" min="1" max="100" value="2" required></label><button class="primary" type="submit">Tambahkan lantai</button></form></div></section>`;
 if(v.tab==='points'){
  const selected=floors.find(f=>f.id===v.floor),visible=selected?[selected]:floors;
  content=(selected?`<button class="link-button back" data-site-tab="points">← Semua lantai</button>`:'')+visible.map(f=>`<section class="card"><div class="card-heading"><h3>Lantai ${esc(f.name)}</h3><span>${f.points.length} area</span></div>${table(['Area sampling','AP inventaris','Tindakan'],f.points.map(p=>`<tr><td>${esc(p.name)}</td><td>${esc(p.item?.device.name||'Belum dihubungkan')}</td><td>${p.item?`<button class="link-button" data-point-visit="${esc(p.item.visitId)}" data-point-id="${esc(p.id)}" data-floor-id="${esc(f.id)}">Buka pemeriksaan →</button>`:`<button class="link-button" data-maintenance-hotel="${esc(v.hotel.id)}">Pilih penugasan →</button>`}</td></tr>`))}</section>`).join('');
  if(!visible.length)content=empty('Belum ada area sampling.','Tambahkan lantai pada tab Lantai.');
 }
 if(['floors','points'].includes(v.tab)&&v.master)content=samplingMasterContent(v);
 if(v.masterError&&['floors','points'].includes(v.tab))content=`<p class="error" role="alert">Master server: ${esc(v.masterError)}. Muat ulang sebelum mengubah konfigurasi.</p>`;
 if(v.tab==='history'){
  const legacy=(state.data.visits||[]).filter(visit=>find('devices',visitSchedule(visit)?.device_id)?.hotel_id===v.hotel.id);
  content=`<section class="card"><div class="card-heading"><h3>Riwayat maintenance hotel</h3>${supervisor()?'<button class="primary" data-hotel-create>＋ Jadwalkan PM hotel</button>':''}</div>${table(['Hotel','Teknisi','Periode','Status','Tindakan'],visitRows(v.visits))}</section><details class="card legacy-history"><summary>Histori perangkat lama (${legacy.length})</summary>${table(['Hotel / perangkat','Teknisi','Periode','Status','Tindakan'],visitRows(legacy))}</details>`;
 }
 $('#page-content').innerHTML='<button class="link-button back" data-page="hotels">← Data Hotel</button>'+heading(v.hotel.name,v.hotel.address||'Detail Hotel',`<button class="primary" data-maintenance-hotel="${esc(v.hotel.id)}">Maintenance Hotel →</button>`)+`<div class="hotel-tabs" role="tablist" aria-label="Detail Hotel">${Object.entries(hotelTabs).map(([key,label])=>`<button class="secondary" role="tab" id="hotel-tab-${key}" data-site-tab="${key}" aria-selected="${v.tab===key}" aria-controls="hotel-detail-panel" tabindex="${v.tab===key?0:-1}">${label}</button>`).join('')}</div><p class="detail-note">${v.master?'Lantai dan area menggunakan master server. Histori kunjungan mempertahankan snapshot masing-masing.':'Lantai dan target area disimpan lokal untuk akun dan browser ini; belum disinkronkan antarperangkat. Inventaris dan histori diambil dari server.'}</p>${v.storageError?`<p class="error" role="alert">${esc(v.storageError)}</p>`:''}${v.error?`<p class="error" role="alert">${esc(v.error)}</p><button class="secondary" data-site-retry> Coba lagi</button>`:''}<div id="hotel-detail-panel" role="tabpanel" aria-labelledby="hotel-tab-${v.tab}">${content}</div>`+footer();
}
async function selectMaintenanceHotel(id){
 await navigate('hotelvisits');state.maintenanceHotelId=id;render();
}
document.addEventListener('click',async event=>{
 const b=event.target.closest('button');if(!b)return;
 try{
  if(b.dataset.siteDetail)await openHotelDetail(b.dataset.siteDetail,b.dataset.returnTab);
  else if(b.dataset.maintenanceHotel)await selectMaintenanceHotel(b.dataset.maintenanceHotel);
  else if(b.hasAttribute('data-maintenance-all')){state.maintenanceHotelId=null;render();}
  else if(b.dataset.maintenanceVisit){hotelDetailView=null;await openSampling(b.dataset.maintenanceVisit);}
  else if(b.dataset.pointVisit){hotelDetailView=null;await openSampling(b.dataset.pointVisit);if(samplingView){samplingView.floor=b.dataset.floorId;samplingView.point=b.dataset.pointId;renderSampling();}}
  else if(b.hasAttribute('data-site-retry')&&hotelDetailView)await openHotelDetail(hotelDetailView.hotel.id,hotelDetailView.tab);
  else if(b.dataset.siteTab&&hotelDetailView){hotelDetailView.tab=b.dataset.siteTab;hotelDetailView.floor=null;renderHotelDetail();$(`[data-site-tab="${hotelDetailView.tab}"]`).focus();}
  else if(b.dataset.siteFloor&&hotelDetailView){hotelDetailView.tab='points';hotelDetailView.floor=b.dataset.siteFloor;renderHotelDetail();}
 }catch(error){notice(error.message,true);}
});
document.addEventListener('change',event=>{if(event.target.id==='maintenance-month'){state.maintenanceMonth=event.target.value;render();}});
document.addEventListener('submit',async event=>{
 const form=event.target;if(form.id!=='hotel-add-floor'&&!form.dataset.floorConfig)return;
 event.preventDefault();const v=hotelDetailView;if(!v)return;
 const button=$('button',form);button.disabled=true;
 try{
  const data=new FormData(form),target=Number(data.get('target')),floors=hotelDetailFloors(v);
  if(!Number.isInteger(target)||target<1||target>100)throw new Error('Target area harus antara 1 dan 100.');
  let floor;
  if(form.id==='hotel-add-floor'){
   const name=String(data.get('floor')||'').trim();if(!name)throw new Error('Isi nama lantai.');
   if(floors.some(f=>f.name.toLocaleLowerCase()===name.toLocaleLowerCase()))throw new Error('Lantai sudah ada. Ubah target pada kartu lantai.');
   floor={id:samplingId(),name,target};
  }else{const existing=floors.find(f=>f.id===form.dataset.floorConfig);if(!existing)return;floor={id:existing.id,name:existing.name,target};}
  const configuration=[...v.configuration.filter(f=>f.id!==floor.id),floor];
  await SamplingStore.put(v.configKey,configuration);v.configuration=configuration;
  if(hotelDetailView===v){renderHotelDetail();notice('Konfigurasi lantai tersimpan lokal.');}
 }catch(error){notice(error.message,true);}finally{button.disabled=false;}
});
document.addEventListener('keydown',event=>{
 const tab=event.target.closest('[data-site-tab][role=tab]');if(!tab||!hotelDetailView||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 event.preventDefault();const tabs=Object.keys(hotelTabs),i=tabs.indexOf(tab.dataset.siteTab);
 hotelDetailView.tab=tabs[event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(event.key==='ArrowRight'?1:tabs.length-1))%tabs.length];hotelDetailView.floor=null;renderHotelDetail();$(`[data-site-tab="${hotelDetailView.tab}"]`).focus();
});
