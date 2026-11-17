'use strict';
function samplingObservationNotes(draft={},saved={}){
 const condition=draft.status||saved.condition||'untested';
 return {condition:['good','attention','problem'].includes(condition)?condition:'untested',
  ...Object.fromEntries(['notes','findings','action','recommendation'].map(key=>[key,String(draft[key]??saved[key]??'').trim()]))};
}
function samplingObservationPanel(v,point){
 if(!point.session)return '';
 const saved=point.session.observation,conflict=v.noteConflicts?.[point.id];
 return `<section class="sampling-card"><h3>Catatan titik di server</h3>${saved?`<details><summary>Catatan terakhir di server · ${esc(date(saved.received_at))}</summary>${['notes','findings','action','recommendation'].map(key=>`<p>${esc(saved.notes[key])}</p>`).join('')}</details>`:'<p>Belum ada catatan diterima server.</p>'}<p>Lokasi memakai snapshot kunjungan. Foto dan speedtest belum ikut dikirim. Kondisi Baik belum berarti pemeriksaan selesai.</p>${v.coverage.observations_enabled?`<button type="button" data-observation-save ${!samplingEditable(v)||v.observationBusy?'disabled':''}>Simpan catatan ke server</button>${conflict?`<p>Tinjau catatan server dan draf, lalu muat ulang kunjungan sebelum membuat kiriman pengganti.</p><button type="button" data-observation-rebase ${!samplingEditable(v)||v.observationBusy?'disabled':''}>Kirim draf setelah review</button>`:''}`:'<p>Penyimpanan catatan server belum diaktifkan.</p>'}</section>`;
}
document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-observation-save],[data-observation-rebase]');
 const v=samplingView;if(!button||!v||!samplingEditable(v)||v.observationBusy)return;
 const point=samplingFindPoint(v);if(!point?.session||!v.coverage.observations_enabled)return;
 const key=v.scope+'observation-outbox:'+point.id;
 v.observationBusy=true;renderSampling();
 try{
  await samplingWrites;
  let pending=await SamplingStore.get(key);
  const rebase=button.hasAttribute('data-observation-rebase');
  if(rebase){
   if(!pending?.conflict)throw new Error('Kirim ulang request sebelumnya dahulu untuk memastikan penerimaan.');
   if(pending.payload.expected_visit_version===v.visit.version&&pending.payload.expected_session_version===point.session.version)throw new Error('Muat ulang kunjungan dan tinjau perubahan server dahulu.');
   pending=null;
  }
  if(!pending){
   const draft=v.drafts[point.id]||{},notes=samplingObservationNotes(draft,point.session.observation?.notes);
   if(['attention','problem'].includes(notes.condition)&&!notes.findings)throw new Error('Isi temuan untuk kondisi perlu perhatian/bermasalah.');
   pending={conflict:false,payload:{id:crypto.randomUUID(),captured_at:draft.updatedAt||new Date().toISOString(),
    expected_visit_version:rebase?v.visit.version:draft.baseVisitVersion??v.visit.version,
    expected_session_version:rebase?point.session.version:draft.baseSessionVersion??point.session.version,notes}};
   await SamplingStore.put(key,pending);
  }
  if(!navigator.onLine)throw new Error('Catatan tersimpan dalam antrean perangkat. Kirim kembali saat online.');
  let result;
  try{result=await api(`/hotel-visits/${v.visit.id}/sampling-sessions/${point.id}/observations`,{method:'POST',body:JSON.stringify(pending.payload)});}
  catch(error){if(error.status===409){await SamplingStore.put(key,{...pending,conflict:true});v.noteConflicts={...v.noteConflicts,[point.id]:true};}throw error;}
  await SamplingStore.remove(key);
  if(JSON.stringify(samplingObservationNotes(v.drafts[point.id],point.session.observation?.notes))===JSON.stringify(result.observation.notes)){
   await SamplingStore.remove(samplingDraftKey(v,point.id));delete v.drafts[point.id];
  }
  v.visit=result.visit;v.coverage=result.visit.sampling_coverage;
  if(v.noteConflicts)delete v.noteConflicts[point.id];
  if(samplingView===v){state.hotelVisit=v.visit;notice('Catatan titik tersimpan di server. Foto dan pengujian belum ikut tersinkron.');}
 }catch(error){if(samplingView===v)notice(error.message,true);}
 finally{v.observationBusy=false;if(samplingView===v)renderSampling();}
});
