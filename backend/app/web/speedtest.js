'use strict';
let activeSpeedtest=null;
function speedNetworkLabel(value){return ({hotel_wifi:'Wi-Fi hotel (konfirmasi teknisi)',cellular:'Data seluler',ethernet:'Kabel / Ethernet',unknown:'Jaringan tidak diketahui'})[value]||'Jaringan tidak diketahui';}
function speedtestHistory(item,editable){
 const records=(item.speedtests||[]).slice(-3).reverse();
 if(!records.length)return '';
 return `<div class="speed-history">${records.map(run=>{
 const direct=run.context.transport==='direct_https',m=run.metrics;
 const ready=direct&&run.status==='completed'&&run.context.network==='hotel_wifi'&&run.context.wifi_confirmed;
 const applied=item.result.automatic_speedtests?.[run.band]?.id===run.id;
 return `<div class="speed-record"><strong>${run.band==='band_24'?'2,4 GHz':'5 GHz'} · ${esc(({running:'Sedang diuji',completed:'Selesai',failed:'Gagal',aborted:'Dibatalkan'})[run.status]||run.status)}</strong><small>${esc(date(run.created_at))} · ${direct?'HTTPS langsung':'Diagnostik tunnel/lokal — bukan hasil AP lapangan'} · ${esc(speedNetworkLabel(run.context.network))}</small>${m?`<p>↓ ${esc(m.download_mbps)} Mbps &nbsp; ↑ ${esc(m.upload_mbps)} Mbps<br>Ping ${esc(m.ping_ms)} ms · jitter ${esc(m.jitter_ms)} ms</p>`:''}${run.error?`<p class="error">${esc(run.error)}</p>`:''}${applied?'<span class="small muted">✓ Bandwidth unduhan sudah masuk hasil AP</span>':editable&&ready?`<button class="link-button" data-speed-apply="${run.id}" data-speed-item="${item.id}">Gunakan hasil pada AP →</button>`:''}</div>`;
 }).join('')}</div>`;
}
function speedDialog(itemId){
 const v=state.hotelVisit,item=v.devices.find(i=>i.id===itemId);
 if(activeSpeedtest)return;
 let modal=$('#speed-dialog');if(!modal){modal=document.createElement('dialog');modal.id='speed-dialog';document.body.append(modal);}
 modal.innerHTML=`<form id="speed-form"><div class="dialog-heading"><div><p class="eyebrow">PENGUKURAN OTOMATIS</p><h2>Speedtest ${esc(item.device.name)}</h2></div></div><p class="validation-hint">Unduh, unggah, ping dan jitter menuju server aplikasi ini. Pengujian ±20–30 detik, dapat memakai hingga 640 MiB dan menggunakan kapasitas jaringan saat berjalan.</p><p class="detail-note">Jika akses memakai PuTTY/localhost, hasil hanya diagnostik. Hasil AP lapangan memerlukan HTTPS langsung dan konfirmasi Wi-Fi hotel. Browser belum dapat memastikan SSID/BSSID atau band secara otomatis.</p><div id="speed-setup">${field('band','Band AP yang sedang digunakan','select','',[['band_24','2,4 GHz'],['band_5','5 GHz']])}${field('network','Jaringan yang sedang digunakan','select','',[['hotel_wifi','Wi-Fi hotel'],['cellular','Data seluler'],['ethernet','Kabel / Ethernet'],['unknown','Tidak diketahui']])}${field('wifi_confirmed','Saya sudah tersambung ke Wi-Fi hotel/AP dan band yang dipilih','checkbox',false)}${field('ssid','SSID yang dikonfirmasi (opsional)','text','',[],false)}${field('bssid','BSSID yang dikonfirmasi (opsional)','text','',[],false)}</div><div id="speed-live" hidden><p id="speed-stage" role="status"></p><progress id="speed-progress" max="100" value="0"></progress><div class="speed-numbers"><div><small>DOWNLOAD</small><strong id="speed-dl">—</strong><span>Mbps</span></div><div><small>UPLOAD</small><strong id="speed-ul">—</strong><span>Mbps</span></div><div><small>PING / JITTER</small><strong id="speed-ping">—</strong><span>ms</span></div></div><p id="speed-context" class="validation-hint"></p></div><p id="speed-error" role="alert" class="error"></p><footer class="dialog-footer"><button type="button" id="speed-close" class="secondary">Tutup</button><button type="button" id="speed-abort" class="danger" hidden>Batalkan pengujian</button><button type="submit" id="speed-start" class="primary">Mulai pengukuran</button></footer></form>`;
 $('#speed-close').addEventListener('click',()=>{if(!activeSpeedtest)modal.close();});
 modal.oncancel=event=>{if(activeSpeedtest){event.preventDefault();cancelSpeedtest();}};
 $('#speed-abort').addEventListener('click',cancelSpeedtest);
 $('#speed-form').addEventListener('submit',async event=>{
 event.preventDefault();if(activeSpeedtest)return;
 $('#speed-start').disabled=true;$('#speed-error').textContent='';
 try{
 const form=new FormData(event.target);
 const observed=navigator.connection?.type;
 const observed_type=['wifi','cellular','ethernet','none'].includes(observed)?observed:'unknown';
 const run=await api(`/hotel-visits/${v.id}/devices/${itemId}/speedtests`,{method:'POST',body:JSON.stringify({expected_version:v.version,band:form.get('band'),network:form.get('network'),wifi_confirmed:form.has('wifi_confirmed'),observed_type,ssid:form.get('ssid')||null,bssid:form.get('bssid')||null})});
 $('#speed-setup').hidden=true;$('#speed-live').hidden=false;$('#speed-start').hidden=true;$('#speed-close').hidden=true;$('#speed-abort').hidden=false;
 $('#speed-context').textContent=speedNetworkLabel(run.context.network)+' · '+(run.context.transport==='direct_https'?'Endpoint HTTPS langsung. Hubungan AP/band berdasarkan konfirmasi teknisi, belum diverifikasi radio Android.':'Mode diagnostik tunnel/lokal: angka tidak akan dimasukkan sebagai bandwidth AP.');
 beginSpeedWorker(run,v.id,itemId);
 }catch(error){$('#speed-error').textContent=error.message;$('#speed-start').disabled=false;}
 });
 modal.showModal();
}
function beginSpeedWorker(run,visitId,itemId){
 const worker=new Worker('/assets/librespeed/speedtest_worker.js');
 const test={worker,run,visitId,itemId,last:null,cancelled:false,finishing:false};activeSpeedtest=test;
 const connection=navigator.connection;
 test.changed=()=>{const type=connection?.type;if(type&&['cellular','ethernet','none'].includes(type)&&run.context.network==='hotel_wifi'){test.failure='Jaringan berubah selama pengukuran. Hasil tidak dipakai sebagai hasil AP.';cancelSpeedtest();}};
 connection?.addEventListener('change',test.changed);
 worker.onmessage=event=>{
 let data;try{data=JSON.parse(event.data);}catch{return;}
 test.last=data;
 $('#speed-dl').textContent=numericLabel(data.dlStatus);$('#speed-ul').textContent=numericLabel(data.ulStatus);
 $('#speed-ping').textContent=`${numericLabel(data.pingStatus)} / ${numericLabel(data.jitterStatus)}`;
 const stage=Number(data.testState);
 $('#speed-stage').textContent=({0:'Menyiapkan pengukuran…',1:'Mengukur kecepatan unduhan…',2:'Mengukur ping dan jitter…',3:'Mengukur kecepatan unggahan…',4:'Menyimpan hasil…',5:'Pengujian dihentikan…'})[stage]||'Mengukur…';
 $('#speed-progress').value=Math.round(Math.max(0,Math.min(100,stage>=4?100:stage===2?(data.pingProgress||0)*20:stage===1?20+(data.dlProgress||0)*40:60+(data.ulProgress||0)*40)));
 if(stage>=4)finishSpeedtest(test,stage===5);
 };
 worker.onerror=()=>{test.failure='Mesin pengukuran tidak dapat dijalankan. Coba muat ulang aplikasi.';finishSpeedtest(test,true);};
 test.timer=setInterval(()=>worker.postMessage('status'),200);
 test.timeout=setTimeout(()=>{test.failure='Waktu pengujian habis. Periksa koneksi lalu ulangi.';cancelSpeedtest();},75000);
 worker.postMessage('start '+JSON.stringify({test_order:'P_D_U',url_dl:run.transfer_base+'/download',url_ul:run.transfer_base+'/upload',url_ping:run.transfer_base+'/ping',time_dl_max:run.duration_seconds,time_ul_max:run.duration_seconds,time_auto:false,count_ping:5,xhr_dlMultistream:2,xhr_ulMultistream:1,xhr_ul_blob_megabytes:4,xhr_ignoreErrors:0,telemetry_level:'disabled',getIp_ispInfo:false,overheadCompensationFactor:1,hotel_transfer_token:run.transfer_token,hotel_run_id:run.id}));
}
function numericLabel(value){const n=Number(value);return value!==''&&value!==null&&Number.isFinite(n)?n.toFixed(2):'—';}
function cancelSpeedtest(){const test=activeSpeedtest;if(!test||test.finishing)return;test.cancelled=true;test.worker.postMessage('abort');setTimeout(()=>finishSpeedtest(test,true),400);}
async function finishSpeedtest(test,aborted){
 if(test.finishing)return;test.finishing=true;clearInterval(test.timer);clearTimeout(test.timeout);test.worker.terminate();navigator.connection?.removeEventListener('change',test.changed);
 const raw=test.last;
 const metrics=raw?{download_mbps:Number(raw.dlStatus),upload_mbps:Number(raw.ulStatus),ping_ms:Number(raw.pingStatus),jitter_ms:Number(raw.jitterStatus)}:null;
 const valid=raw&&[raw.dlStatus,raw.ulStatus,raw.pingStatus,raw.jitterStatus].every(x=>x!==''&&x!==null&&Number.isFinite(Number(x)));
 let status=test.failure?'failed':aborted||test.cancelled?'aborted':valid?'completed':'failed';
 try{
 const saved=await api(`/network-speedtests/${test.run.id}/finish`,{method:'POST',body:JSON.stringify({status,metrics:status==='completed'?metrics:null,error:test.failure||(!valid&&status==='failed'?'Transfer tidak menghasilkan pengukuran lengkap':null)})});
 if(saved.status!=='completed'){for(const id of ['#speed-dl','#speed-ul','#speed-ping'])$(id).textContent='—';}
 let message=saved.status==='completed'?'Hasil pengukuran tersimpan.':saved.error||'Pengujian dibatalkan; tidak ada angka yang dipakai pada AP.';
 if(saved.can_apply){
  try{const fresh=await api(`/hotel-visits/${test.visitId}`);await api(`/hotel-visits/${test.visitId}/devices/${test.itemId}/speedtests/${saved.id}/apply`,{method:'POST',body:JSON.stringify({expected_version:fresh.version})});message='Hasil tersimpan dan bandwidth unduhan otomatis masuk pada AP sampling.';}
  catch(error){message='Hasil tersimpan, tetapi belum dimasukkan ke AP. '+error.message;}
 }else if(saved.status==='completed'){message+=' Mode diagnostik/jaringan tidak terkonfirmasi: hasil tidak dimasukkan ke bandwidth AP.';}
 await reload();await openHotelVisit(test.visitId);
 $('#speed-stage').textContent=message;
 if(saved.status==='failed')$('#speed-error').textContent=saved.error||'Pengujian gagal. Coba ulangi.';
 }catch(error){$('#speed-error').textContent='Hasil belum terkonfirmasi tersimpan. '+error.message+' Muat ulang dan periksa riwayat sebelum mencoba lagi.';}
 finally{activeSpeedtest=null;$('#speed-close').hidden=false;$('#speed-abort').hidden=true;}
}
document.addEventListener('click',async event=>{
 const el=event.target.closest('button');if(!el)return;
 if(el.dataset.speedtest)speedDialog(el.dataset.speedtest);
 if(el.dataset.speedApply){
  el.disabled=true;try{const v=state.hotelVisit;await api(`/hotel-visits/${v.id}/devices/${el.dataset.speedItem}/speedtests/${el.dataset.speedApply}/apply`,{method:'POST',body:JSON.stringify({expected_version:v.version})});await openHotelVisit(v.id);notice('Hasil speedtest masuk ke AP sampling.');}catch(error){notice(error.message,true);}finally{el.disabled=false;}
 }
});
window.addEventListener('beforeunload',event=>{if(activeSpeedtest){event.preventDefault();event.returnValue='';}});
