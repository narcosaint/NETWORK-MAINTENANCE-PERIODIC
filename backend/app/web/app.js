'use strict';
const $ = (s, root = document) => root.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = {assigned:'Ditugaskan',in_progress:'Dalam pengerjaan',submitted:'Menunggu review',revision_requested:'Perlu revisi',approved:'Disetujui',pending:'Belum selesai',completed:'Selesai',pass:'Baik',fail:'Bermasalah',not_applicable:'Tidak berlaku',technician:'Teknisi',supervisor:'Supervisor',router:'Router',switch:'Switch',ap:'Access point'};
const title = v => labels[v] || v;
const badge = v => `<span class="badge ${esc(v)}">${esc(title(v))}</span>`;
const date = v => v ? new Date(v).toLocaleString('id-ID',{dateStyle:'medium',timeStyle:'short'}) : '—';
const state = {token:null,user:null,page:'dashboard',data:{},visit:null,hotelVisit:null,filter:'',status:'',busy:false};
const pages = {dashboard:['Ringkasan','◫'],hotelvisits:['Maintenance Hotel','▣'],visits:['Kunjungan perangkat','◷'],hotels:['Data Hotel','▤'],devices:['Perangkat','◇'],users:['Tim Teknisi','♙'],templates:['Template Checklist','☷'],schedules:['Jadwal perangkat','▦']};
const mainPages=['dashboard','hotelvisits','hotels','users','templates'];
const endpoints = {hotelvisits:'/hotel-visits',hotels:'/hotels',devices:'/devices',users:'/users',templates:'/checklist-templates',schedules:'/schedules',visits:'/visits'};
function notice(message, error=false){const el=$('#notice');el.textContent=message;el.className=error?'error':'';el.hidden=false;}
function clearSession(){closeNavigation();if(typeof hotelDetailView!=='undefined')hotelDetailView=null;state.maintenanceHotelId=null;if(typeof clearSampling==='function')clearSampling();state.token=null;state.user=null;state.data={};state.visit=null;state.hotelVisit=null;if(typeof clearHotelPhotos==='function')clearHotelPhotos();$('#workspace').hidden=true;$('#login-view').hidden=false;$('#form-dialog').close();$('#login-form').reset();}
async function api(path, options={}){
  let response;
  try {response=await fetch(path,{...options,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(state.token?{Authorization:`Bearer ${state.token}`}:{})},cache:'no-store'});} catch {throw new Error('Koneksi ke server terputus. Coba lagi saat koneksi tersedia.');}
  if(response.status===204)return null;
  const data=await response.json().catch(()=>null);
  if(!response.ok){
    if(response.status===401&&state.token){clearSession();$('#login-error').textContent='Sesi berakhir. Silakan masuk kembali.';}
    if(response.status===409)throw new Error(path.startsWith('/hotel-visits')&&typeof data?.detail==='string'?data.detail:'Data sudah berubah atau operasi tidak sesuai status saat ini. Muat ulang data sebelum melanjutkan.');
    if(response.status===401)throw new Error('Username atau password tidak sesuai.');
    if(response.status===403)throw new Error('Akun ini tidak memiliki izin untuk tindakan tersebut.');
    if(response.status===404)throw new Error('Data tidak ditemukan atau tidak tersedia untuk akun Anda.');
    if(response.status===429)throw new Error(path.includes('speedtests')&&typeof data?.detail==='string'?data.detail:'Terlalu banyak percobaan. Tunggu satu menit.');
    if(Array.isArray(data?.detail))throw new Error(data.detail.map(e=>`${e.loc.slice(1).join('.')}: ${e.msg}`).join('\n'));
    throw new Error(data?.detail || 'Server tidak dapat memproses permintaan.');
  }
  return data;
}
async function collection(path){let all=[],offset=0;for(;;){const rows=await api(`${path}?limit=100&offset=${offset}`);all.push(...rows);if(rows.length<100)return all;offset+=100;}}
const supervisor=()=>state.user?.role==='supervisor';
const find=(kind,id)=>state.data[kind]?.find(x=>x.id===id);
function deviceName(id){return find('devices',id)?.name || 'Perangkat tidak tersedia';}
function hotelFor(deviceId){const device=find('devices',deviceId);return find('hotels',device?.hotel_id)?.name || 'Hotel tidak tersedia';}
function techName(id){return find('users',id)?.name || (id===state.user?.id?state.user.name:'Teknisi');}
function visitSchedule(visit){return find('schedules',visit.schedule_id);}
function visitName(visit){if(visit.hotel_id)return 'Router · switch · LAN · AP sampling';const schedule=visitSchedule(visit);return schedule?deviceName(schedule.device_id):'Kunjungan';}
function visitHotel(visit){if(visit.hotel_id)return find('hotels',visit.hotel_id)?.name||'Hotel';const schedule=visitSchedule(visit);return schedule?hotelFor(schedule.device_id):'Hotel tidak tersedia';}
function month(v){return new Date(v+'T00:00:00').toLocaleDateString('id-ID',{month:'long',year:'numeric'});}
function nav(){
  const allowed=mainPages.filter(k=>supervisor()||k!=='users');
  const active=['visits','schedules'].includes(state.page)?'hotelvisits':state.page==='devices'?'hotels':state.page;
  $('#navigation').innerHTML=allowed.map(k=>`<button class="nav-button ${active===k?'active':''}" data-page="${k}" ${active===k?'aria-current="page"':''}><span class="nav-symbol" aria-hidden="true">${pages[k][1]}</span>${pages[k][0]}</button>`).join('');
  $('#breadcrumb').textContent=pages[active]?.[0] || 'Maintenance Hotel';
}
async function reload(){
  const kinds=supervisor()?Object.keys(endpoints):['hotels','devices','templates','schedules','visits','hotelvisits'];
  const pairs=await Promise.all(kinds.map(async kind=>[kind,await collection(endpoints[kind])]));
  if(!state.token)return;
  state.data=Object.fromEntries(pairs);
}
function checklistLetter(index){let n=index+1,result='';while(n>0){n--;result=String.fromCharCode(97+n%26)+result;n=Math.floor(n/26);}return result;}
function checklistDisplayTitle(value){return String(value??'').replace(/^\s*(?:[a-z]|\d+)[.)]\s+/i,'');}
function checklistCategory(title,index){return `${index+1}. ${title}`;}
function maintenanceItem(key,title,index,statusControl,notesControl,{required=false,level=4}={}){
 const headingId=`inspection-${key}-title`;
 return `<article class="maintenance-item" role="group" aria-labelledby="${esc(headingId)}"><h${level} class="maintenance-item-title" id="${esc(headingId)}"><span class="inspection-number">${checklistLetter(index)}.</span> ${esc(checklistDisplayTitle(title))}${required?'<span class="required">WAJIB</span>':''}</h${level}><div class="maintenance-item-fields"><div class="maintenance-control">${statusControl}</div><div class="maintenance-control">${notesControl}</div></div></article>`;
}
function maintenanceReadOnly(key,title,index,status,notes,options={}){
 return maintenanceItem(key,title,index,`<span class="maintenance-label">Status</span><div class="maintenance-value">${status}</div>`,`<span class="maintenance-label">Keterangan</span><p class="maintenance-value maintenance-note">${esc(notes||'Belum ada keterangan')}</p>`,options);
}
function heading(name,description,action=''){return `<div class="page-heading"><div><p class="eyebrow">MAINTENANCE WORKSPACE</p><h2>${esc(name)}</h2><p class="muted">${esc(description)}</p></div>${action}</div>`;}
function empty(message='Data belum tersedia.',description='Mulai dengan menambahkan data nyata sesuai kebutuhan operasional.'){return `<div class="empty"><h3>${esc(message)}</h3><p>${esc(description)}</p></div>`;}
function table(headers, rows){return rows.length?`<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`:empty();}
function footer(){return `<div class="screen-footer"><span>HOTEL NETWORK / MAINTENANCE OPERATIONS</span><span>Data langsung dari server · ${new Date().toLocaleDateString('id-ID',{dateStyle:'long'})}</span></div>`;}
function visitRows(visits){return visits.map(v=>`<tr><td><strong>${esc(visitHotel(v))}</strong><small>${esc(visitName(v))}</small></td><td>${esc(techName(v.technician_id))}</td><td>${esc(v.planned_date?new Date(v.planned_date+'T00:00:00').toLocaleDateString('id-ID',{dateStyle:'medium'}):month(visitSchedule(v)?.month||'2000-01-01'))}</td><td>${badge(v.status)}</td><td><button class="link-button" ${v.hotel_id?'data-maintenance-visit':'data-visit'}="${v.id}">Buka pemeriksaan →</button></td></tr>`);}
function dashboard(){
 const current=new Date(),period=`${current.getFullYear()}-${String(current.getMonth()+1).padStart(2,'0')}`;
 const visits=(state.data.hotelvisits||[]).filter(v=>v.planned_date?.startsWith(period));
 const pending=visits.filter(v=>['submitted','revision_requested'].includes(v.status)).length;
 const stats=[['Hotel terdaftar',state.data.hotels.length,'Lokasi dalam inventaris'],['Maintenance bulan berjalan',visits.length,month(period+'-01')],['Maintenance selesai',visits.filter(v=>v.maintenance_completed).length,'Disetujui dengan pekerjaan selesai'],['Maintenance tertunda',visits.filter(v=>v.report?.work_status==='pending').length,'Status pekerjaan pending dari server'],['Perlu review',pending,'Dikirim atau perlu revisi'],['Total temuan','Belum tersedia','Lihat titik bermasalah per penugasan']];
 const relevant=[...visits].sort((a,b)=>new Date(b.created_at)-new Date(a.created_at)).slice(0,8);
 return heading(`Selamat datang, ${state.user.name.split(' ')[0]}.`,supervisor()?'Pantau kunjungan dan jaga setiap lokasi tetap terawat.':'Pilih hotel, lantai, dan titik sampling untuk melanjutkan pemeriksaan.',`<button class="secondary" data-refresh>↻ Muat ulang</button>`)+`<section class="stats" aria-label="Ringkasan operasional">${stats.map(([label,note,sub])=>`<article class="stat"><p>${esc(label)}</p><strong>${note}</strong><small>${esc(sub)}</small></article>`).join('')}</section><section class="card"><div class="card-heading"><div><h3>Maintenance hotel terbaru</h3><p>Pantau tugas, status pemeriksaan, dan hasil review.</p></div><button class="link-button" data-page="hotelvisits">Lihat semua →</button></div>${relevant.length?table(['Hotel','Teknisi','Periode','Status',''],visitRows(relevant)):empty('Belum ada kunjungan.',supervisor()?'Tambahkan hotel dan inventaris, lalu jadwalkan PM hotel bulanan.':'Penugasan akan muncul setelah dibuat oleh supervisor.')}</section>`+footer();
}
function resourceRows(kind, rows){
 return rows.map(r=>{let cells=[];
 if(kind==='hotels')cells=[`<strong>${esc(r.name)}</strong>`,esc(r.address||'—')];
 if(kind==='devices')cells=[`<strong>${esc(r.name)}</strong><small>${esc([r.brand,r.model].filter(Boolean).join(' ')||'Merek / model belum diisi')}</small>`,esc(find('hotels',r.hotel_id)?.name||'—'),esc(title(r.device_type)),`<strong>${esc(r.location||'—')}</strong><small>${esc(r.ip_address||'IP belum diisi')}</small>`,`${esc(r.serial_number||'—')}<small>${esc(r.mac_address||'MAC belum diisi')}</small>`];
 if(kind==='users')cells=[`<strong>${esc(r.name)}</strong><small>${esc(r.username)}</small>`,esc(title(r.role)),r.active?'Aktif':'Nonaktif'];
 if(kind==='templates')cells=[`<strong>${esc(r.name)}</strong>`,esc(title(r.device_type)),`${r.items.length} pemeriksaan`];
 if(kind==='schedules')cells=[`<strong>${esc(hotelFor(r.device_id))}</strong><small>${esc(deviceName(r.device_id))}</small>`,esc(techName(r.technician_id)),esc(month(r.month)),badge(r.status)];
 const bound=kind==='schedules'&&state.data.visits.some(v=>v.schedule_id===r.id);
 let actions=kind==='hotels'?`<button class="link-button" data-site-detail="${r.id}">Detail Hotel →</button>`:'';
 if(supervisor()){
  if(kind==='templates')actions=`<button class="link-button" data-template="${r.id}">Lihat item</button>`;
  else actions+=`<button class="link-button" data-edit="${kind}" data-id="${r.id}" ${bound?'disabled':''}>Ubah</button><button class="link-button" data-delete="${kind}" data-id="${r.id}" ${bound?'disabled':''}>Hapus</button>`;
 }
 if(kind==='schedules'&&bound){const visit=state.data.visits.find(v=>v.schedule_id===r.id);actions+=`<button class="link-button" data-visit="${visit.id}">Kunjungan →</button>`;}

 return `<tr>${cells.map(c=>`<td>${c}</td>`).join('')}<td><div class="table-actions">${actions||'—'}</div></td></tr>`;
 });
}
function listPage(){
 const kind=state.page,rows=state.data[kind]||[];
 const descriptions={hotels:'Kelola lokasi hotel dan alamat kunjungan.',devices:'Inventaris router, switch, dan access point.',users:'Kelola akun serta peran tim operasional.',templates:'Template tetap tersimpan. Perubahan dibuat sebagai template baru.',schedules:'Rencanakan preventive maintenance bulanan per perangkat.',visits:'Kelola penugasan dan pantau perjalanan setiap kunjungan.'};
 const headers={hotels:['Hotel','Alamat','Tindakan'],devices:['Perangkat / model','Hotel','Jenis','Lokasi / IP','Serial / MAC','Tindakan'],users:['Anggota tim','Peran','Status','Tindakan'],templates:['Template','Jenis perangkat','Item','Tindakan'],schedules:['Hotel / perangkat','Teknisi','Periode','Status','Tindakan']};
 const add=supervisor()&&!['visits','schedules'].includes(kind)?`<button class="primary" data-create="${kind}">＋ Tambah ${esc(pages[kind][0].toLowerCase())}</button>`:'';
 let filtered=rows.filter(r=>JSON.stringify(r).toLowerCase().includes(state.filter.toLowerCase()) || (kind==='visits'&&`${visitName(r)} ${visitHotel(r)} ${techName(r.technician_id)}`.toLowerCase().includes(state.filter.toLowerCase())) || (kind==='schedules'&&`${deviceName(r.device_id)} ${hotelFor(r.device_id)} ${techName(r.technician_id)}`.toLowerCase().includes(state.filter.toLowerCase())));
 if(state.status)filtered=filtered.filter(r=>r.status===state.status);
 return heading(pages[kind][0],descriptions[kind],add)+`<section class="card"><div class="card-heading"><div><h3>${esc(kind==='visits'?'Daftar kunjungan':'Daftar '+pages[kind][0].toLowerCase())}</h3><p>${rows.length} data tersedia</p></div><div class="toolbar"><input id="search" aria-label="Cari data" placeholder="Cari data…" value="${esc(state.filter)}">${['visits','schedules'].includes(kind)?`<select id="status-filter" aria-label="Filter status"><option value="">Semua status</option>${(kind==='visits'?['assigned','in_progress','submitted','revision_requested','approved']:['pending','completed']).map(v=>`<option value="${v}" ${state.status===v?'selected':''}>${esc(title(v))}</option>`).join('')}</select>`:''}<button class="secondary" data-refresh>↻</button></div></div>${table(kind==='visits'?['Hotel / perangkat','Teknisi','Periode','Status','Tindakan']:headers[kind],kind==='visits'?visitRows(filtered):resourceRows(kind,filtered))}<div class="rows-count">Menampilkan ${filtered.length} dari ${rows.length} data</div></section>`+footer();
}
function render(){if(!state.user)return;if(typeof hotelDetailView!=='undefined'&&hotelDetailView&&state.page==='hotels'){renderHotelDetail();return;}nav();$('#page-content').innerHTML=state.page==='hotelvisits'?hotelList():state.page==='dashboard'?dashboard():listPage();}
async function navigate(page){if(typeof hotelDetailView!=='undefined')hotelDetailView=null;state.maintenanceHotelId=null;if(typeof clearSampling==='function')clearSampling();state.page=page;state.visit=null;state.hotelVisit=null;if(typeof clearHotelPhotos==='function')clearHotelPhotos();state.filter='';state.status='';$('#notice').hidden=true;render();}
function options(kind, label, filter=()=>true){return (state.data[kind]||[]).filter(filter).map(x=>[x.id,label(x)]);}
function field(name,label,type='text',value='',opts=[],required=true){if(type==='checkbox')return `<label class="checkbox-label"><input name="${name}" type="checkbox" ${value?'checked':''}>${esc(label)}</label>`;return `<label>${esc(label)}${type==='textarea'?`<textarea name="${name}" ${required?'required':''} maxlength="5000">${esc(value)}</textarea>`:type==='select'?`<select name="${name}" ${required?'required':''}><option value="">Pilih…</option>${opts.map(([v,l])=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(l)}</option>`).join('')}</select>`:`<input name="${name}" type="${type}" value="${type==='password'?'':esc(value)}" ${required?'required':''} ${type==='number'?'step="any"':type==='password'?'minlength="12" maxlength="128" autocomplete="new-password"':type==='text'?'maxlength="200"':''}>`}</label>`;}
let editorAction=null;
function dialog(name, html, action, save='Simpan'){$('#dialog-fields').oninput=null;$('#dialog-fields').onchange=null;$('#form-dialog').classList.remove('report-wide');$('#dialog-title').textContent=name;$('#dialog-fields').innerHTML=html;$('#form-error').textContent='';$('#save-form').textContent=save;editorAction=action;$('#form-dialog').showModal();}
function editResource(kind,id){
 const row=id?find(kind,id):(kind==='devices'&&typeof hotelDetailView!=='undefined'&&hotelDetailView?{hotel_id:hotelDetailView.hotel.id}:{});let html='';const types=[['router','Router'],['switch','Switch'],['ap','Access point']];
 if(kind==='hotels'){
 const profile=row.maintenance_profile||{};
 html=field('name','Nama hotel / site','text',row.name)+field('customer_name','Nama pelanggan / perusahaan (kosongkan jika sama dengan site)','text',row.customer_name||'',[],false)+field('address','Alamat','textarea',row.address||'',[],false)+`<fieldset><legend>Profil maintenance site</legend><p class="validation-hint">Diisi sekali oleh supervisor. Nama pelanggan dan bandwidth layanan akan otomatis dibaca pada laporan teknisi. Tidak ada angka layanan atau ambang kesesuaian yang diasumsikan.</p>`+field('profile_percent','Batas minimum kesesuaian (% bandwidth layanan)','number',profile.minimum_percent??'',[],false)+`<h3 class="small">1. Fiber optic</h3>`+field('profile_fo_down','Download layanan FO (Mbps)','number',profile.fo?.download_mbps??'',[],false)+field('profile_fo_up','Upload layanan FO (Mbps)','number',profile.fo?.upload_mbps??'',[],false)+`<h3 class="small">2. Backup wireless</h3>`+field('profile_wireless_down','Download layanan wireless (Mbps)','number',profile.wireless?.download_mbps??'',[],false)+field('profile_wireless_up','Upload layanan wireless (Mbps)','number',profile.wireless?.upload_mbps??'',[],false)+'</fieldset>';
 }
 if(kind==='devices')html=field('hotel_id','Hotel','select',row.hotel_id,options('hotels',x=>x.name))+field('name','Nama perangkat','text',row.name)+field('device_type','Jenis perangkat','select',row.device_type,types)+field('serial_number','Nomor serial (opsional)','text',row.serial_number||'',[],false)+field('brand','Merek (opsional)','text',row.brand||'',[],false)+field('model','Model (opsional)','text',row.model||'',[],false)+field('location','Lokasi pemasangan (opsional)','text',row.location||'',[],false)+field('ip_address','Alamat IPv4 / IPv6 (opsional)','text',row.ip_address||'',[],false)+field('mac_address','MAC address (opsional)','text',row.mac_address||'',[],false)+field('notes','Catatan perangkat (opsional)','textarea',row.notes||'',[],false);
 if(kind==='users')html=field('username','Username','text',row.username)+field('name','Nama lengkap','text',row.name)+field('role','Peran','select',row.role||'technician',[['technician','Teknisi'],['supervisor','Supervisor']])+field('password',id?'Password baru (kosongkan jika tetap)':'Password (12–128 karakter)','password','',[],!id)+field('active','Akun aktif','checkbox',row.active??true);
 if(kind==='templates')html=field('name','Nama dan versi template','text')+field('device_type','Jenis perangkat','select','',types)+field('items','Item wajib — satu pemeriksaan per baris','textarea')+'<p class="validation-hint">Setiap baris menjadi satu item wajib. Maksimal 100 item, 200 karakter per item. Template yang dibuat tidak dapat diubah atau dihapus.</p>';
 if(kind==='schedules')html=field('device_id','Perangkat','select',row.device_id,options('devices',x=>`${hotelFor(x.id)} / ${x.name}`))+field('technician_id','Teknisi','select',row.technician_id,options('users',x=>x.name,x=>x.role==='technician'&&x.active))+field('month','Periode','month',row.month?.slice(0,7))+field('notes','Catatan (opsional)','textarea',row.notes||'',[],false);
 dialog(`${id?'Ubah':'Tambah'} ${pages[kind][0].toLowerCase()}`,html,async form=>{
  const payload=Object.fromEntries(form);
  if(kind==='hotels'){
   const numeric=key=>payload[key]===''||payload[key]===undefined?null:Number(payload[key]);
   const profile={minimum_percent:numeric('profile_percent'),fo:{download_mbps:numeric('profile_fo_down'),upload_mbps:numeric('profile_fo_up')},wireless:{download_mbps:numeric('profile_wireless_down'),upload_mbps:numeric('profile_wireless_up')}};
   if(profile.fo.download_mbps===null&&profile.fo.upload_mbps===null)profile.fo=null;
   if(profile.wireless.download_mbps===null&&profile.wireless.upload_mbps===null)profile.wireless=null;
   payload.maintenance_profile=profile.minimum_percent===null&&profile.fo===null&&profile.wireless===null?null:profile;
   for(const key of Object.keys(payload))if(key.startsWith('profile_'))delete payload[key];
   if(!payload.customer_name)payload.customer_name=null;
  }
  if(kind==='users'){payload.active=form.has('active');if(id&&!payload.password)payload.password=null;}
  if(kind==='templates'){payload.items=payload.items.split('\n').map(v=>v.trim()).filter(Boolean).map(label=>({label,required:true}));}
  if(kind==='schedules'){payload.month+='-01';payload.status=row.status||'pending';}
  for(const key of ['address','serial_number','brand','model','location','ip_address','mac_address','notes'])if(key in payload&&!payload[key])payload[key]=null;
  await api(endpoints[kind]+(id?'/'+id:''),{method:id?'PUT':'POST',body:JSON.stringify(payload)});
 });
}
function assign(scheduleId){
 const schedule=find('schedules',scheduleId),device=find('devices',schedule.device_id);
 dialog('Buat penugasan kunjungan',`<p class="muted small">${esc(hotelFor(device.id))} / ${esc(device.name)} · ${esc(techName(schedule.technician_id))}</p>`+field('template_id','Template checklist','select','',options('templates',x=>x.name,x=>x.device_type===device.device_type)),async form=>{await api('/visits',{method:'POST',body:JSON.stringify({schedule_id:scheduleId,template_id:form.get('template_id')})});},'Buat kunjungan');
}
async function openVisit(id){
 if(typeof hotelDetailView!=='undefined')hotelDetailView=null;if(typeof clearSampling==='function')clearSampling();state.hotelVisit=null;if(typeof clearHotelPhotos==='function')clearHotelPhotos();
 $('#page-content').innerHTML='<div class="loading">Memuat kunjungan…</div>';
 try{
 const visit=await api('/visits/'+id),checklist=await api(`/visits/${id}/checklist`),history=await collection(`/visits/${id}/history`);
 if(!state.token)return;
 state.visit=visit;state.page='visits';nav();
 const own=visit.technician_id===state.user.id&&state.user.role==='technician';
 const editable=own&&['in_progress','revision_requested'].includes(visit.status);
 const schedule=visitSchedule(visit),device=find('devices',schedule?.device_id);
 setBreadcrumb([{label:'Maintenance Hotel',page:'hotelvisits'},{label:visitHotel(visit)},{label:'Histori perangkat lama'}]);
 const answers=new Map(checklist.answers.map(a=>[a.item_id,a]));
 const itemMarkup=checklist.template?.items.map((item,index)=>{
 const answer=answers.get(item.id),key='legacy-'+item.id;
 if(!editable)return maintenanceReadOnly(key,item.label,index,answer?badge(answer.answer):'<span class="muted small">Belum diperiksa</span>',answer?.notes,{required:item.required});
 const status=`<label for="answer-${item.id}">Status</label><select id="answer-${item.id}" data-item="${item.id}" aria-describedby="inspection-${key}-title"><option value="" ${answer?'disabled':''}>Belum diperiksa</option>${['pass','fail','not_applicable'].map(v=>`<option value="${v}" ${answer?.answer===v?'selected':''}>${esc(title(v))}</option>`).join('')}</select>`;
 const notes=`<label for="notes-${item.id}">Keterangan</label><textarea id="notes-${item.id}" data-notes="${item.id}" aria-describedby="inspection-${key}-title" placeholder="Catatan tindakan / alasan" maxlength="5000">${esc(answer?.notes||'')}</textarea>`;
 return maintenanceItem(key,item.label,index,status,notes,{required:item.required});
 }).join('');
 let actions='';
 if(own&&visit.status==='assigned')actions='<button class="primary" data-checkin>Mulai kunjungan / check-in</button>';
 if(editable&&checklist.template)actions='<button class="primary" data-save-checklist>Simpan jawaban</button>'+(visit.status==='in_progress'?'<button class="secondary" data-checkout>Check-out & kirim laporan</button>':'<button class="secondary" data-resubmit>Kirim ulang untuk review</button>');
 if(supervisor()&&visit.status==='submitted')actions='<button class="primary" data-review="approved">Setujui laporan</button><button class="secondary" data-review="revision_requested">Minta revisi</button>';
 if(supervisor()&&!visit.template_id&&['assigned','in_progress'].includes(visit.status))actions='<button class="primary" data-bind-template>Pilih template checklist</button>';
 const gps=visit.latitude!==null?`${visit.latitude}, ${visit.longitude} · ±${visit.accuracy_m} m`:visit.gps_exception_reason||'Belum check-in';
 const outGps=visit.checkout_latitude!==null?`${visit.checkout_latitude}, ${visit.checkout_longitude} · ±${visit.checkout_accuracy_m} m`:visit.checkout_gps_exception_reason||'Belum check-out';
 $('#page-content').innerHTML=`<button class="link-button back" data-site-detail="${esc(device?.hotel_id||'')}" data-return-tab="history">← Riwayat Maintenance Hotel</button>`+heading(visitHotel(visit),`${visitName(visit)} · ${techName(visit.technician_id)}`,badge(visit.status))+`<div class="detail-grid"><div><section class="card"><div class="card-heading"><div><h3>${esc(checklist.template?.name||'Checklist belum ditentukan')}</h3><p>Hasil pemeriksaan perangkat</p></div><span class="small muted">Versi ${visit.version}</span></div><div class="detail-content">${itemMarkup||empty('Template belum dipilih.','Supervisor perlu mengikat template sebelum laporan dapat dikirim.')}<div class="actions">${actions}</div>${visit.status==='approved'?'<p class="detail-note">Laporan telah disetujui dan dikunci. Jadwal preventive maintenance selesai.</p>':''}${visit.status==='revision_requested'?'<p class="detail-note">Perbaiki jawaban sesuai catatan supervisor. Simpan perubahan sebelum mengirim ulang laporan.</p>':''}</div></section><section class="card"><div class="card-heading"><h3>Detail kunjungan</h3></div><div class="detail-content"><dl class="key-values"><div><dt>Periode</dt><dd>${esc(month(schedule?.month||'2000-01-01'))}</dd></div><div><dt>Perangkat</dt><dd>${esc(device?.name||'—')} / ${esc(title(device?.device_type||''))}</dd></div><div><dt>Merek / model</dt><dd>${esc([device?.brand,device?.model].filter(Boolean).join(' ')||'—')}</dd></div><div><dt>Lokasi pemasangan</dt><dd>${esc(device?.location||'—')}</dd></div><div><dt>Alamat IP</dt><dd>${esc(device?.ip_address||'—')}</dd></div><div><dt>MAC / serial</dt><dd>${esc(device?.mac_address||'—')} / ${esc(device?.serial_number||'—')}</dd></div><div><dt>Catatan perangkat</dt><dd>${esc(device?.notes||'—')}</dd></div><div><dt>Check-in server</dt><dd>${esc(date(visit.checked_in_at))}</dd></div><div><dt>Check-out server</dt><dd>${esc(date(visit.checked_out_at))}</dd></div><div><dt>Lokasi / pengecualian check-in</dt><dd>${esc(gps)}</dd></div><div><dt>Lokasi / pengecualian check-out</dt><dd>${esc(outGps)}</dd></div><div><dt>Pengecualian PIC</dt><dd>${esc(visit.pic_exception_reason||'—')}</dd></div><div><dt>Catatan jadwal</dt><dd>${esc(schedule?.notes||'—')}</dd></div></dl><p class="detail-note">Foto dan tanda tangan PIC belum tersedia. Pengecualian serta hasil bermasalah harus ditinjau supervisor sebelum approval.</p></div></section></div><section class="card"><div class="card-heading"><h3>Riwayat laporan</h3></div><div class="detail-content">${history.length?history.map(e=>`<article class="history-event"><strong>${esc(title(e.action==='resubmitted'?'submitted':e.action))}${e.action==='resubmitted'?' · dikirim ulang':''}</strong><small>${esc(date(e.created_at))} · ${esc(supervisor()?techName(e.actor_id):e.actor_id===state.user.id?state.user.name:['approved','revision_requested'].includes(e.action)?'Supervisor':'Teknisi')} · versi ${e.version}</small><p>${esc(e.reason||'Laporan dan bukti pemeriksaan tersimpan.')}</p><details><summary>Lihat snapshot bukti</summary><pre>${esc(JSON.stringify(e.snapshot,null,2))}</pre></details></article>`).join(''):empty('Belum ada pengajuan.','Riwayat akan muncul saat laporan dikirim.')}</div></section></div>`+footer();
 }catch(error){notice(error.message,true);render();}
}
function coordinates(){return new Promise(resolve=>{if(!navigator.geolocation){resolve(null);return;}navigator.geolocation.getCurrentPosition(p=>resolve({latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy_m:p.coords.accuracy}),()=>resolve(null),{enableHighAccuracy:true,timeout:12000,maximumAge:0});});}
async function locationDialog(checkout=false){
 const visit=state.visit;notice('Mencari lokasi perangkat…');const gps=await coordinates();$('#notice').hidden=true;
 const hint=gps?`<p class="validation-hint">Lokasi diperoleh: ${esc(gps.latitude.toFixed(5))}, ${esc(gps.longitude.toFixed(5))} · akurasi ±${Math.round(gps.accuracy_m)} meter.</p>`:field('gps_exception_reason','Lokasi tidak tersedia — jelaskan alasannya','textarea');
 dialog(checkout?'Check-out & kirim laporan':'Mulai kunjungan',`<p class="muted small">${checkout?'Simpan jawaban checklist terlebih dahulu. Semua item wajib harus sudah dijawab.':'Waktu server dan lokasi perangkat akan dicatat.'}</p>${hint}${checkout?field('pic_exception_reason','Alasan pengecualian tanda tangan PIC','textarea')+'<p class="validation-hint">Tanda tangan digital belum tersedia. Jelaskan kondisi sebenarnya untuk review supervisor.</p>':''}`,async form=>{
 const payload={expected_version:visit.version,device_time:new Date().toISOString(),...(gps||{gps_exception_reason:form.get('gps_exception_reason')})};if(checkout)payload.pic_exception_reason=form.get('pic_exception_reason');
 await api(`/visits/${visit.id}/${checkout?'check-out':'check-in'}`,{method:'POST',body:JSON.stringify(payload)});
 },checkout?'Kirim laporan':'Check-in');
}
async function saveAnswers(){
 const answers=[...document.querySelectorAll('[data-item]')].filter(el=>el.value).map(el=>({item_id:el.dataset.item,answer:el.value,notes:$(`[data-notes="${el.dataset.item}"]`).value.trim()||null}));
 if(!answers.length)throw new Error('Isi setidaknya satu hasil pemeriksaan.');
 if(answers.some(a=>a.answer!=='pass'&&!a.notes))throw new Error('Hasil bermasalah atau tidak berlaku wajib memiliki catatan tindakan / alasan.');
 await api(`/visits/${state.visit.id}/checklist`,{method:'PUT',body:JSON.stringify({expected_version:state.visit.version,answers})});
 await openVisit(state.visit.id);notice('Jawaban checklist tersimpan.');
}
$('#login-form').addEventListener('submit',async event=>{
 event.preventDefault();const button=$('button',event.target);button.disabled=true;$('#login-error').textContent='';
 try{const form=new FormData(event.target);const auth=await api('/auth/login',{method:'POST',body:JSON.stringify(Object.fromEntries(form))});state.token=auth.access_token;state.user=await api('/auth/me');await reload();$('#login-view').hidden=true;$('#workspace').hidden=false;$('#user-name').textContent=state.user.name;$('#user-role').textContent=title(state.user.role);$('#avatar').textContent=state.user.name.slice(0,1).toUpperCase();state.page='dashboard';state.filter='';state.status='';$('#notice').hidden=true;render();event.target.reset();}catch(error){state.token=null;state.user=null;$('#login-error').textContent=error.message;}finally{button.disabled=false;}
});
$('#logout').addEventListener('click',async()=>{try{await api('/auth/logout',{method:'POST'});}catch{}clearSession();});
$('#close-dialog').addEventListener('click',()=>$('#form-dialog').close());$('#cancel-dialog').addEventListener('click',()=>$('#form-dialog').close());
$('#editor-form').addEventListener('submit',async event=>{
 event.preventDefault();$('#save-form').disabled=true;$('#form-error').textContent='';const visitId=state.visit?.id;const hotelId=state.hotelVisit?.id;const siteId=typeof hotelDetailView!=='undefined'?hotelDetailView?.hotel.id:null;
 let saved=false;try{await editorAction(new FormData(event.target));saved=true;await reload();if(siteId)await openHotelDetail(siteId,hotelDetailView?.tab);else if(hotelId)await openHotelVisit(hotelId);else if(visitId)await openVisit(visitId);else render();$('#form-dialog').close();notice('Perubahan berhasil disimpan.');}catch(error){if(saved){$('#form-dialog').close();notice('Perubahan tersimpan, tetapi tampilan belum dapat diperbarui. Muat ulang data. '+error.message,true);}else $('#form-error').textContent=error.message;}finally{$('#save-form').disabled=false;}
});
document.addEventListener('input',event=>{if(event.target.id==='search'){const pos=event.target.selectionStart;state.filter=event.target.value;$('#page-content').innerHTML=state.page==='hotelvisits'?hotelList():listPage();$('#search').focus();$('#search').setSelectionRange(pos,pos);}});
document.addEventListener('change',event=>{if(event.target.id==='status-filter'){state.status=event.target.value;render();}});
document.addEventListener('click',async event=>{
 const el=event.target.closest('button');if(!el||el.disabled)return;
 if(state.busy)return;
 state.busy=true;
 try{
 if(el.dataset.page)await navigate(el.dataset.page);
 else if(el.hasAttribute('data-refresh')){const id=state.visit?.id,hotelId=state.hotelVisit?.id;await reload();if(typeof hotelDetailView!=='undefined'&&hotelDetailView)await openHotelDetail(hotelDetailView.hotel.id,hotelDetailView.tab);else if(typeof samplingView!=='undefined'&&samplingView)await openSampling(hotelId);else if(hotelId)await openHotelVisit(hotelId);else if(id)await openVisit(id);else render();notice('Data diperbarui.');}
 else if(el.dataset.create)editResource(el.dataset.create);
 else if(el.dataset.edit)editResource(el.dataset.edit,el.dataset.id);
 else if(el.dataset.delete){if(confirm('Hapus data ini? Data yang masih dirujuk tidak dapat dihapus.')){await api(endpoints[el.dataset.delete]+'/'+el.dataset.id,{method:'DELETE'});await reload();if(typeof hotelDetailView!=='undefined'&&hotelDetailView)await openHotelDetail(hotelDetailView.hotel.id,hotelDetailView.tab);else render();notice('Data dihapus.');}}
 else if(el.dataset.assign)assign(el.dataset.assign);
 else if(el.dataset.visit){$('#notice').hidden=true;await openVisit(el.dataset.visit);}
 else if(el.dataset.template){const row=find('templates',el.dataset.template);dialog(row.name,`<ol class="maintenance-preview">${row.items.map(i=>`<li>${esc(checklistDisplayTitle(i.label))} ${i.required?'(wajib)':'(opsional)'}</li>`).join('')}</ol><p class="validation-hint">Template tidak dapat diubah setelah dibuat.</p>`,async()=>{},'Tutup');}
 else if(el.hasAttribute('data-checkin'))await locationDialog();
 else if(el.hasAttribute('data-checkout'))await locationDialog(true);
 else if(el.hasAttribute('data-save-checklist')){el.disabled=true;try{await saveAnswers();}finally{el.disabled=false;}}
 else if(el.hasAttribute('data-resubmit')){const visit=state.visit;dialog('Kirim ulang laporan','<p class="muted small">Pastikan perubahan jawaban sudah disimpan. Bukti check-out awal tetap dipertahankan.</p>',async()=>api(`/visits/${visit.id}/resubmit`,{method:'POST',body:JSON.stringify({expected_version:visit.version})}),'Kirim ulang');}
 else if(el.dataset.review){const visit=state.visit,decision=el.dataset.review;dialog(decision==='approved'?'Setujui laporan':'Minta revisi',`<p class="muted small">${decision==='approved'?'Tinjau hasil gagal dan seluruh pengecualian GPS/PIC. Approval mengunci laporan dan menyelesaikan jadwal.':'Jelaskan perbaikan yang perlu dilakukan teknisi.'}</p>`+field('reason','Catatan keputusan supervisor','textarea'),async form=>api(`/visits/${visit.id}/review`,{method:'POST',body:JSON.stringify({expected_version:visit.version,decision,reason:form.get('reason')})}),decision==='approved'?'Setujui & selesaikan':'Minta revisi');}
 else if(el.hasAttribute('data-bind-template')){const visit=state.visit,schedule=visitSchedule(visit),device=find('devices',schedule.device_id);dialog('Pilih template checklist',field('template_id','Template','select','',options('templates',x=>x.name,x=>x.device_type===device.device_type)),async form=>api(`/visits/${visit.id}/template`,{method:'PUT',body:JSON.stringify({expected_version:visit.version,template_id:form.get('template_id')})}));}
 }catch(error){notice(error.message,true);}finally{state.busy=false;}
});

function closeNavigation(restore=false){
 $('#workspace').classList.remove('navigation-open');$('#navigation-backdrop').hidden=true;
 $('#open-navigation').setAttribute('aria-expanded','false');
 if(matchMedia('(max-width:700px)').matches){$('#mobile-navigation').inert=true;if(restore)$('#open-navigation').focus();}
}
function openNavigation(){
 $('#workspace').classList.add('navigation-open');$('#navigation-backdrop').hidden=false;
 $('#mobile-navigation').inert=false;$('#open-navigation').setAttribute('aria-expanded','true');$('#close-navigation').focus();
}
$('#open-navigation').addEventListener('click',openNavigation);
$('#close-navigation').addEventListener('click',()=>closeNavigation(true));
$('#navigation-backdrop').addEventListener('click',()=>closeNavigation(true));
document.addEventListener('click',event=>{if(event.target.closest('#navigation button,#logout'))closeNavigation(true);},true);
document.addEventListener('keydown',event=>{
 if(!$('#workspace').classList.contains('navigation-open'))return;
 if(event.key==='Escape'){event.preventDefault();closeNavigation(true);}
 if(event.key==='Tab'){
  const controls=Array.from($('#mobile-navigation').querySelectorAll('a,button')).filter(el=>!el.disabled);
  const first=controls[0],last=controls.at(-1);
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
 }
});
const mobileNavigation=matchMedia('(max-width:700px)');
function updateNavigationLayout(){closeNavigation();$('#mobile-navigation').inert=mobileNavigation.matches;}
mobileNavigation.addEventListener('change',updateNavigationLayout);updateNavigationLayout();
