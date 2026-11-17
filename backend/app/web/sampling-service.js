'use strict';
// Phase B boundary: replace these adapters only when the native host/API exists.
const SamplingServices = Object.freeze({
 async connection(){return {available:false,reason:'Belum tersedia — informasi jaringan aktif memerlukan aplikasi Android dan plugin Wi-Fi native.'};},
 async scan(){return {available:false,reason:'Belum tersedia — browser tidak dapat memindai radio Wi-Fi. Tidak ada hasil scan atau cache OS yang diterima.'};},
 async saveScan(){throw new Error('Belum tersedia — endpoint penyimpanan scan belum ada.');}
});
const SamplingStore = (()=>{
 let opening;
 function open(){
  if(!opening)opening=new Promise((resolve,reject)=>{
   if(!window.indexedDB){reject(new Error('Penyimpanan lokal tidak tersedia di browser ini.'));return;}
   const request=indexedDB.open('hotel-sampling-drafts-v1',1);
   request.onupgradeneeded=()=>request.result.createObjectStore('records',{keyPath:'key'});
   request.onsuccess=()=>{request.result.onversionchange=()=>{request.result.close();opening=null;};resolve(request.result);};
   request.onerror=()=>{opening=null;reject(new Error('Penyimpanan lokal tidak dapat dibuka.'));};
   request.onblocked=()=>{opening=null;reject(new Error('Tutup tab aplikasi lain untuk membuka penyimpanan lokal.'));};
  });
  return opening;
 }
 async function transaction(mode,action){
  const db=await open();
  return new Promise((resolve,reject)=>{
   const tx=db.transaction('records',mode);let result;
   const request=action(tx.objectStore('records'));
   request.onsuccess=()=>{result=request.result;};
   tx.oncomplete=()=>resolve(result);
   tx.onerror=tx.onabort=()=>reject(new Error('Draf gagal disimpan/dibaca. Periksa ruang penyimpanan dan izin browser.'));
  });
 }
 return Object.freeze({
  async get(key){return (await transaction('readonly',store=>store.get(key)))?.value;},
  async list(prefix){return (await transaction('readonly',store=>store.getAll(IDBKeyRange.bound(prefix,prefix+'\uffff')))).map(row=>({key:row.key,...row.value}));},
  put(key,value){return transaction('readwrite',store=>store.put({key,value}));},
  remove(key){return transaction('readwrite',store=>store.delete(key));}
 });
})();
function samplingId(){return Array.from(crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,'0')).join('');}
function samplingBand(band){return ({band_24:'2.4 GHz',band_5:'5 GHz'})[band]||'Belum diuji';}
function samplingMetrics(item){
 const measured=['band_24','band_5'].map(key=>({key,...item?.result?.[key]})).filter(b=>b.status==='measured');
 const b=measured[0];
 const runs=(item?.speedtests||[]).filter(run=>run.status==='completed'&&run.metrics).sort((a,b)=>new Date(b.finished_at||b.created_at)-new Date(a.finished_at||a.created_at));
 const run=runs[0];
 return {signal:b?.signal_dbm??null,band:b?samplingBand(b.key):run?samplingBand(run.band):null,download:run?.metrics?.download_mbps??b?.bandwidth_mbps??null,
  source:run?'Speedtest tersimpan'+(run.context?.transport==='direct_https'?'':' · diagnostik tunnel/lokal'):b?'Input manual tersimpan':null,time:run?.finished_at||run?.created_at||null};
}
function samplingStatus(point,draft){return draft?.status||point.session?.observation?.notes.condition||({pass:'good',fail:'problem',not_applicable:'not_applicable'})[point.item?.result?.outcome]||'untested';}
const samplingStatusLabels={untested:'Belum Diperiksa',good:'Baik',attention:'Perlu Perhatian',problem:'Bermasalah',not_applicable:'Tidak berlaku'};
function samplingFloors(visit,configuration,drafts){
 const floors=(configuration||[]).map(f=>({...f,points:[]}));
 for(const item of visit.devices.filter(d=>d.device.device_type==='ap')){
  const name=item.floor||'Lantai belum dicatat';let floor=floors.find(f=>f.name===name);
  if(!floor){floor={id:'server:'+name,name,target:4,points:[]};floors.push(floor);}
  floor.points.push({id:'server:'+item.id,name:item.point||item.device.name,item});
 }
 for(const floor of floors){
  const savedLocal=Object.keys(drafts).filter(id=>id.startsWith('local:'+floor.id+':')).map(id=>Number(id.slice(id.lastIndexOf(':')+1))+1).filter(Number.isFinite);
  const count=Math.max(0,floor.target-floor.points.length,...savedLocal);
  for(let i=0;i<count;i++){
   const id='local:'+floor.id+':'+i;
   floor.points.push({id,name:drafts[id]?.location||`Titik ${floor.points.length+1} · tentukan lokasi`,item:null});
  }
 }
 return floors;
}
