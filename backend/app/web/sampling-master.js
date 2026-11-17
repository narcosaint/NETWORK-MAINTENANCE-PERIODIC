'use strict';
async function samplingCapabilities(){
 try{return await api('/sampling-capabilities');}
 catch(error){if(error.status===404)return {master_enabled:false,coverage_enabled:false};throw error;}
}
async function samplingMasterHotel(hotelId){
 const floors=await collection(`/hotels/${encodeURIComponent(hotelId)}/floors`);
 return Promise.all(floors.map(async floor=>({...floor,points:await collection(`/hotels/${encodeURIComponent(hotelId)}/floors/${encodeURIComponent(floor.id)}/sampling-points`)})));
}
function samplingAPOptions(v,id){
 return '<option value="">Belum dihubungkan</option>'+(state.data.devices||[]).filter(d=>d.hotel_id===v.hotel.id&&d.device_type==='ap').map(d=>`<option value="${esc(d.id)}" ${d.id===id?'selected':''}>${esc(d.name)}</option>`).join('');
}
function samplingPointFields(v,point={}){
 return `<label>Nama titik<input name="name" value="${esc(point.name||'')}" maxlength="200" required></label><label>Lokasi<input name="location" value="${esc(point.location||'')}" maxlength="4000"></label><label>Urutan<input name="position" type="number" min="0" value="${point.position??0}" required></label><label>AP inventaris<select name="device_id">${samplingAPOptions(v,point.device_id)}</select></label>`;
}
function samplingMasterContent(v){
 const edit=supervisor();
 return `<p class="detail-note"><strong>Master sampling server</strong><br>Dipakai bersama Web dan Android. Target awal 4 titik; isi lokasi nyata sebelum membekukan kunjungan.</p>${v.master.map(f=>`<section class="card"><div class="detail-content"><h3>${esc(f.name)}</h3><p>${f.points.length} titik nyata · target ${f.default_sampling_count}</p>${edit?`<details><summary>Ubah lantai</summary><form data-master-floor="${esc(f.id)}"><label>Nama lantai<input name="name" maxlength="100" value="${esc(f.name)}" required></label><label>Target titik<input name="target" type="number" min="1" value="${f.default_sampling_count}" required></label><label>Urutan<input name="position" type="number" min="0" value="${f.position}" required></label><label><input name="archive" type="checkbox"> Arsipkan lantai</label><button class="secondary">Simpan lantai</button></form></details>`:''}${f.points.map(p=>`<details><summary>${esc(p.name)} · ${esc((state.data.devices||[]).find(d=>d.id===p.device_id)?.name||'AP belum dihubungkan')}</summary>${edit?`<form data-master-point="${esc(p.id)}" data-master-floor-id="${esc(f.id)}">${samplingPointFields(v,p)}<label><input name="archive" type="checkbox"> Arsipkan titik</label><button class="secondary">Simpan titik</button></form>`:`<p>${esc(p.location||'Lokasi belum dicatat')}</p>`}</details>`).join('')}${edit?`<details><summary>Tambah titik sampling</summary><form data-master-point-create="${esc(f.id)}">${samplingPointFields(v)}<button class="primary">Tambah titik</button></form></details>`:''}</div></section>`).join('')}${edit?`<section class="card"><div class="detail-content"><h3>Tambah lantai</h3><form id="master-floor-create"><label>Nama lantai<input name="name" maxlength="100" required></label><label>Urutan<input name="position" type="number" min="0" value="${v.master.length}" required></label><button class="primary">Tambah lantai · target 4 titik</button></form></div></section>`:''}`;
}
async function samplingLoadHotelMaster(v){
 try{
  const capability=await samplingCapabilities();
  if(capability.master_enabled)v.master=await samplingMasterHotel(v.hotel.id);
 }catch(error){v.masterError=error.message;}
}
document.addEventListener('submit',async event=>{
 const form=event.target;
 if(!form.matches('#master-floor-create,[data-master-floor],[data-master-point],[data-master-point-create]'))return;
 event.preventDefault();const v=hotelDetailView;if(!v||!supervisor()||!v.master)return;
 const button=$('button',form);button.disabled=true;
 try{
  const data=new FormData(form),base=`/hotels/${encodeURIComponent(v.hotel.id)}/floors`;
  let path=base,method='POST',body;
  if(form.id==='master-floor-create')body={id:form.dataset.requestId||(form.dataset.requestId=crypto.randomUUID()),name:String(data.get('name')).trim(),position:Number(data.get('position'))};
  else if(form.dataset.masterFloor){
   const f=v.master.find(f=>f.id===form.dataset.masterFloor);path+='/'+encodeURIComponent(f.id);method='PATCH';
   body={expected_version:f.version,name:String(data.get('name')).trim(),position:Number(data.get('position')),default_sampling_count:Number(data.get('target')),archived:data.has('archive')};
  }else{
   const f=v.master.find(f=>f.id===(form.dataset.masterPointCreate||form.dataset.masterFloorId));
   path+='/'+encodeURIComponent(f.id)+'/sampling-points';
   body={name:String(data.get('name')).trim(),location:String(data.get('location')).trim()||null,position:Number(data.get('position')),device_id:data.get('device_id')||null};
   if(form.dataset.masterPoint){const p=f.points.find(p=>p.id===form.dataset.masterPoint);path+='/'+encodeURIComponent(p.id);method='PATCH';body.expected_version=p.version;body.archived=data.has('archive');}
   else body.id=form.dataset.requestId||(form.dataset.requestId=crypto.randomUUID());
  }
  await api(path,{method,body:JSON.stringify(body)});
  const fresh=await samplingMasterHotel(v.hotel.id);
  if(hotelDetailView===v){v.master=fresh;renderHotelDetail();notice('Master sampling tersimpan di server.');}
 }catch(error){notice(error.message,true);}finally{button.disabled=false;}
});

async function samplingLoadCoverage(v){
 if(v.visit.sampling_coverage){v.coverage=v.visit.sampling_coverage;v.coverageEnabled=true;return;}
 try{
  const capability=await samplingCapabilities();v.coverageEnabled=capability.coverage_enabled===true;
  if(!v.coverageEnabled)return;
  v.coverage=await api(`/hotel-visits/${v.visit.id}/sampling-coverage`);
  if(!v.coverage&&supervisor()&&v.visit.status==='assigned')v.coverageMaster=await samplingMasterHotel(v.visit.hotel_id);
 }catch(error){v.coverageError=error.message;}
}
const samplingPhotoLabels={ap:'Access Point',device:'Perangkat',area:'Area sampling',finding:'Temuan',router:'Router',switch:'Switch',rack:'Rack',backbone:'Backbone',cable:'Kabel'};
function samplingCoveragePanel(v){
 if(v.coverageError)return `<section class="card"><p class="error" role="alert">Cakupan sampling: ${esc(v.coverageError)}</p><button type="button" data-sampling-retry="${esc(v.visit.id)}">Muat ulang</button></section>`;
 if(!v.coverageEnabled)return '';
 const coverage=v.coverage;
 if(coverage)return `<section class="card" id="server-coverage"><div class="detail-content"><h3>Cakupan sampling kunjungan</h3><p>Periode ${esc(coverage.period)} · snapshot tersimpan. Pengukuran per sesi dan submit V2 belum tersedia.</p>${coverage.floors.map(f=>`<details><summary>${esc(f.name)} · ${f.points.length} titik</summary><ul>${f.points.map(p=>`<li>${esc(p.name)} · ${esc(p.device?.name||'AP belum dihubungkan')} · Belum Diperiksa</li>`).join('')}</ul></details>`).join('')}<p>Hasil AP pada laporan existing belum menjadi hasil tiap sesi dalam cakupan ini.</p></div></section>`;
 if(!v.coverageMaster)return '<section class="card"><p>Belum ada cakupan sampling V2 untuk kunjungan ini.</p></section>';
 return `<section class="card" id="server-coverage"><div class="detail-content"><h3>Bekukan cakupan sampling</h3>${v.coverageMaster.map(f=>`<p><strong>${esc(f.name)}</strong> · target ${f.default_sampling_count}: ${f.points.map(p=>esc(p.name)).join(', ')||'Belum ada titik nyata'}</p>`).join('')}<p>Sesudah dibekukan, cakupan tidak mengikuti perubahan master. Pengukuran per sesi dan submit V2 belum tersedia.</p><form id="activate-sampling-coverage"><fieldset><legend>Foto wajib tiap titik</legend>${['ap','device','area','finding'].map(c=>`<label><input type="checkbox" name="sampling" value="${c}"> ${samplingPhotoLabels[c]}</label>`).join('')}</fieldset><fieldset><legend>Foto wajib infrastruktur</legend>${['router','switch','rack','backbone','ap','cable','finding'].map(c=>`<label><input type="checkbox" name="infrastructure" value="${c}"> ${samplingPhotoLabels[c]}</label>`).join('')}</fieldset><label><input type="checkbox" name="reviewed" required> Saya sudah meninjau titik dan kewajiban foto. Tanpa centang kategori berarti kategori tersebut tidak wajib.</label><button class="primary">Bekukan cakupan kunjungan</button></form></div></section>`;
}
document.addEventListener('submit',async event=>{
 const form=event.target;if(form.id!=='activate-sampling-coverage')return;
 event.preventDefault();const v=samplingView;if(!v||!supervisor()||!v.coverageMaster)return;
 const button=$('button',form);button.disabled=true;
 try{
  const data=new FormData(form);if(!data.has('reviewed'))throw new Error('Tinjau cakupan dan foto wajib dahulu.');
  const body={expected_version:v.visit.version,floors:v.coverageMaster.map(f=>({id:f.id,version:f.version,points:f.points.map(p=>({id:p.id,version:p.version}))})),photo_policy:{sampling_categories:data.getAll('sampling'),infrastructure_categories:data.getAll('infrastructure')}};
  const coverage=await api(`/hotel-visits/${v.visit.id}/sampling-coverage`,{method:'POST',body:JSON.stringify(body)});
  if(samplingView===v){v.coverage=coverage;v.visit=await api('/hotel-visits/'+v.visit.id);state.hotelVisit=v.visit;renderSampling();}
 }catch(error){notice(error.message,true);}finally{button.disabled=false;}
});
