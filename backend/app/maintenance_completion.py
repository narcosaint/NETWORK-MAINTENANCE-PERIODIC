"""Versioned evidence and PIC review using the existing append-only visit event log.

Photo bytes live in the existing private photo volume. Event UUIDs are retry keys;
signed snapshots are immutable and contain every document input, never bearer tokens.
"""
import base64
import binascii
import hashlib
import json
import math
import os
import re
import unicodedata
import io
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, Response
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models as m, hotel_schemas as hs
from app.api import current, db, save, get
from app.hotel_api import visible, advance, storage, clean_photo, detail
from app.sampling_schemas import StrictInput

router = APIRouter(prefix='/hotel-visits/{identifier}', tags=['Maintenance completion'])
PHOTO_ACTION = 'evidence_added'
SIGN_ACTION = 'pic_signed'


def records(session, visit_id, action):
    return session.scalars(select(m.HotelVisitEvent).where(m.HotelVisitEvent.visit_id == visit_id,
        m.HotelVisitEvent.action == action).order_by(m.HotelVisitEvent.version)).all()


def photos(session, visit_id):
    return [e.snapshot['photo'] for e in records(session, visit_id, PHOTO_ACTION)]


def public_photo(photo):
    return {k:v for k,v in photo.items() if k != 'object_key'}


def file_bytes(photo):
    path = storage() / photo['object_key']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != photo['sha256']:
        raise HTTPException(409, 'Berkas bukti hilang/berubah. Pulihkan bukti sebelum melanjutkan.')
    return path


def owner_lock(session, identifier, user):
    visit = visible(session, identifier, user)
    if user.role != 'technician' or visit.technician_id != user.id:
        raise HTTPException(403, 'Hanya teknisi yang ditugaskan dapat menyimpan bukti/PIC')
    session.execute(select(m.HotelVisit.id).where(m.HotelVisit.id == identifier).with_for_update()).scalar_one()
    session.refresh(visit)
    return visit


def replay(session, identifier, user, data, action):
    old = session.get(m.HotelVisitEvent, data.id)
    if old and (old.visit_id != identifier or old.actor_id != user.id or old.action != action
                or old.snapshot.get('request_digest') != request_digest(data, action)):
        raise HTTPException(409, 'UUID sudah dipakai untuk bukti berbeda')
    return old


def request_digest(data, action):
    value=jsonable_encoder(data)
    if action==PHOTO_ACTION:value.pop('expected_version',None)
    return digest(value)


def digest(value):
    return hashlib.sha256(json.dumps(jsonable_encoder(value), sort_keys=True,
        separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


class PhotoInput(StrictInput):
    id: UUID
    expected_version: int = Field(ge=1)
    session_id: UUID | None = None
    category: Literal['router','switch','rack','backbone','ap','cable','finding','device','area']
    caption: str = Field(default='', max_length=2000)
    captured_at: AwareDatetime
    content_type: Literal['image/jpeg','image/png','image/webp']
    image_base64: str = Field(min_length=1, max_length=14_000_000)


@router.post('/evidence', status_code=201)
def upload_evidence(identifier: UUID, data: PhotoInput, user=Depends(current), session: Session=Depends(db)):
    visit = owner_lock(session, identifier, user)
    old = replay(session, identifier, user, data, PHOTO_ACTION)
    if old:
        return {'photo':public_photo(old.snapshot['photo']), 'visit':detail(session, visit), 'replayed':True}
    if data.session_id:
        from app.sampling_observation_api import scoped_session
        scoped_session(session, identifier, data.session_id, user)
        if data.category not in ('ap','device','area','finding'):
            raise HTTPException(422, 'Kategori foto area tidak valid')
    elif data.category in ('device','area'):
        raise HTTPException(422, 'Foto area/perangkat sampling memerlukan sesi area')
    existing = photos(session, identifier)
    if sum(p['session_id'] == (str(data.session_id) if data.session_id else None)
           and (data.session_id is not None or p['category'] == data.category) for p in existing) >= 10:
        raise HTTPException(409, 'Maksimal 10 foto pada area/kategori ini')
    try:
        payload = base64.b64decode(data.image_base64, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, 'Data foto tidak valid')
    if len(payload) > 10*1024*1024:
        raise HTTPException(413, 'Foto maksimal 10 MiB')
    image, width, height = clean_photo(payload, data.content_type)
    if len(image) > 10*1024*1024:
        raise HTTPException(413, 'Foto maksimal 10 MiB setelah normalisasi')
    visit = advance(session, identifier, user, data.expected_version)
    root = storage(); root.mkdir(parents=True, exist_ok=True)
    key = uuid4().hex+'.jpg'; path=root/key
    photo = {'id':str(data.id), 'session_id':str(data.session_id) if data.session_id else None,
        'category':data.category, 'caption':data.caption, 'captured_at':data.captured_at.isoformat(),
        'created_at':datetime.now(timezone.utc).isoformat(), 'uploaded_by':str(user.id),
        'object_key':key, 'sha256':hashlib.sha256(image).hexdigest(), 'size_bytes':len(image),
        'width':width, 'height':height, 'url':f'/hotel-visits/{identifier}/evidence/{data.id}'}
    try:
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(image); stream.flush(); os.fsync(stream.fileno())
        directory_fd=os.open(root,os.O_RDONLY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
        session.add(m.HotelVisitEvent(id=data.id, visit_id=identifier, actor_id=user.id,
            version=visit.version, action=PHOTO_ACTION,
            snapshot={'request_digest':request_digest(data, PHOTO_ACTION), 'photo':photo}))
        save(session)
    except Exception:
        path.unlink(missing_ok=True); raise
    return {'photo':public_photo(photo), 'visit':detail(session,visit), 'replayed':False}


@router.get('/evidence/{photo_id}')
def read_evidence(identifier: UUID, photo_id: UUID, user=Depends(current), session:Session=Depends(db)):
    visible(session,identifier,user)
    item=get(session,m.HotelVisitEvent,photo_id)
    if item.visit_id != identifier or item.action != PHOTO_ACTION:
        raise HTTPException(404,'Foto tidak ditemukan')
    return FileResponse(file_bytes(item.snapshot['photo']), media_type='image/jpeg',
        headers={'Cache-Control':'private, no-store'})


@router.get('/evidence/{photo_id}/thumbnail')
def thumbnail(identifier: UUID, photo_id: UUID, user=Depends(current), session:Session=Depends(db)):
    visible(session,identifier,user)
    item=get(session,m.HotelVisitEvent,photo_id)
    if item.visit_id!=identifier or item.action!=PHOTO_ACTION:raise HTTPException(404,'Foto tidak ditemukan')
    from PIL import Image
    with Image.open(file_bytes(item.snapshot['photo'])) as image:
        image.thumbnail((640,640));output=io.BytesIO();image.save(output,'JPEG',quality=75)
    return {'image_base64':base64.b64encode(output.getvalue()).decode()}


def document(session,visit):
    from app.sampling_coverage_api import coverage_info
    coverage=session.scalar(select(m.SamplingCoverage).where(m.SamplingCoverage.hotel_visit_id==visit.id))
    site=get(session,m.Hotel,visit.hotel_id); tech=get(session,m.User,visit.technician_id)
    prior=records(session,visit.id,SIGN_ACTION)
    technician={'id':str(tech.id),'name':tech.name}
    if prior and prior[-1].snapshot['document']['technician']['id']==str(tech.id):
        technician=prior[-1].snapshot['document']['technician']
    hotel=coverage.hotel_snapshot if coverage else {'name':site.name,'address':site.address,'customer_name':site.customer_name}
    data={'schema':1,'visit_id':str(visit.id),'planned_date':visit.planned_date.isoformat(),
        'hotel':{key:hotel.get(key) for key in ('name','address','customer_name')},
        'technician':technician,'checkin':visit.checkin,
        'report':visit.report,'floors':[], 'photo_policy':{},'photos':photos(session,visit.id)}
    if coverage:
        info=coverage_info(session,coverage)
        data['floors']=info['floors']; data['photo_policy']=info['photo_policy']
        # Capability/trust annotations are not evidence and may change on upgrades.
        for floor in data['floors']:
            for point in floor['points']:
                point.pop('photos',None)
                point.pop('completion',None)
                for attempt in point['speedtests']:
                    attempt.pop('completion_accepted',None)
                    if attempt['run']:attempt['run'].pop('can_apply',None)
    return jsonable_encoder(data)


def run_valid(attempt):
    run=attempt.get('run') or {}; ctx=run.get('context') or {}; metrics=run.get('metrics') or {}
    before=ctx.get('connection_start') or {}; after=ctx.get('connection_end') or {}
    binding=ctx.get('binding_start'); counters=ctx.get('server_observed') or {}
    return (run.get('status')=='completed' and ctx.get('transport')=='direct_https'
        and ctx.get('network')=='connected_wifi' and binding and binding==ctx.get('binding_end')
        and bool(before.get('bssid')) and before.get('bssid','').lower()==after.get('bssid','').lower()
        and before.get('frequency_mhz')==after.get('frequency_mhz')
        and all(isinstance(metrics.get(k),(int,float)) and not isinstance(metrics.get(k),bool)
            and math.isfinite(metrics[k]) and metrics[k]>=0 for k in ('download_mbps','upload_mbps','ping_ms'))
        and counters.get('download_budget_bytes',0)>0 and counters.get('upload_received_bytes',0)>0
        and counters.get('ping_requests',0)>=3)


def point_completion(point_id, observation, attempts, policy, evidence):
    latest=attempts[-1] if attempts else {}; accepted=bool(run_valid(latest))
    failed=latest.get('status') in ('failed','aborted') and bool((latest.get('error') or '').strip())
    notes=(observation or {}).get('notes') or {}; connection=(observation or {}).get('wifi_connection') or {}
    photo_ready=True
    done=bool(observation) and (accepted or failed) and photo_ready and (bool(connection.get('bssid') and connection.get('rssi_dbm') is not None) or failed) and (not (failed or notes.get('findings')) or bool((notes.get('action') or notes.get('notes') or '').strip()))
    return {'done':bool(done),'speedtest_accepted':accepted,'failed_with_reason':bool(failed)}


def validation(data, check_files=True):
    errors=[]; report=hs.HotelReport.model_validate(data['report'])
    for key,label in [('summary','Ringkasan laporan'),('work_status','Status pekerjaan'),('backbone_mode','Jenis backbone')]:
        if not getattr(report,key): errors.append(label+' belum diisi')
    if report.work_status=='pending' and not report.pending_reason:errors.append('Alasan pending belum diisi')
    for key,required in [('fo',report.backbone_mode in ('fo_only','both','failover','bonding')),
                         ('wireless',report.backbone_mode in ('wireless_only','both','failover','bonding'))]:
        branch=getattr(report,key)
        if required and (not branch or ((branch.download_mbps is None or branch.upload_mbps is None) and not branch.notes)):
            errors.append('Lengkapi hasil download/upload backbone '+key.upper())
    for key,label in [('router_connector','LAN router'),('switch_connector','LAN switch'),('signal_test','Signal test'),
                      ('blank_spot','Blank spot'),('hotspot','Hotspot')]:
        if getattr(report,key) is None or not (getattr(report,key+'_notes') or '').strip():
            errors.append('Isi hasil dan keterangan '+label)
    if not data['floors']:errors.append('Tambahkan lantai dan area aktual')
    evidence=data['photos']; points=[]
    for floor in data['floors']:
        if not floor['points']:errors.append(f"{floor['name']}: tambahkan area aktual atau batalkan lantai kosong")
        for point in floor['points']:
            obs=point.get('observation') or {}; notes=obs.get('notes') or {}
            attempts=point.get('speedtests') or []; latest=attempts[-1] if attempts else {}
            accepted=bool(run_valid(latest)); failed=latest.get('status') in ('failed','aborted') and bool((latest.get('error') or '').strip())
            label=f"{floor['name']} / {point['name']}"
            if any(a.get('status')=='running' for a in attempts):errors.append(label+': masih ada pengujian berjalan; tunggu selesai atau kedaluwarsa')
            connection=obs.get('wifi_connection') or {}
            if not obs: errors.append(label+': catatan area belum disimpan')
            if not (connection.get('bssid') and connection.get('rssi_dbm') is not None) and not failed:
                errors.append(label+': hasil Wi-Fi Analyzer belum disimpan')
            if not (accepted or failed):errors.append(label+': speedtest belum lengkap; lakukan tes atau catat gagal uji beralasan')
            if (failed or notes.get('findings')) and not (notes.get('action') or notes.get('notes') or '').strip():
                errors.append(label+': isi tindakan/tindak lanjut untuk temuan atau gagal uji')

            points.append({'id':point['id'],'name':point['name'],'floor':floor['name'],'speedtest_accepted':accepted,'failed_with_reason':bool(failed)})
    for category in data['photo_policy'].get('infrastructure_categories',[]):
        if not any(p['session_id'] is None and p['category']==category for p in evidence):errors.append('Dokumentasi utama: foto '+category+' wajib')
    if check_files:
        for photo in evidence:
            try:file_bytes(photo)
            except HTTPException: errors.append('Berkas foto '+photo['id']+' hilang/berubah')
    return errors,points


def current_signature(session,visit,data=None):
    signed=records(session,visit.id,SIGN_ACTION)
    if not signed:return None
    record=signed[-1]; body=record.snapshot
    latest_revision=session.scalar(select(m.HotelVisitEvent.version).where(m.HotelVisitEvent.visit_id==visit.id,m.HotelVisitEvent.action=='revision_requested').order_by(m.HotelVisitEvent.version.desc()).limit(1))
    if latest_revision and record.version<latest_revision:return None
    if body['document_digest'] != digest(data if data is not None else document(session,visit)):return None
    return record


def completion_info(session,visit):
    data=document(session,visit); errors,points=validation(data)
    signed=current_signature(session,visit,data)
    return {'ready':not errors, 'errors':errors, 'points':points, 'document_digest':digest(data),
        'signature':({'id':signed.id,'name':signed.snapshot['signature']['name'],
            'position':signed.snapshot['signature']['position'],'signed_at':signed.snapshot['signed_at']} if signed else None),
        'pdf_available':bool(signed),'can_submit':not errors and bool(signed) and visit.status in ('in_progress','revision_requested')}


@router.get('/completion')
def review_completion(identifier:UUID,user=Depends(current),session:Session=Depends(db)):
    return completion_info(session,visible(session,identifier,user))


class SignatureInput(StrictInput):
    id:UUID
    expected_version:int=Field(ge=1)
    document_digest:str=Field(pattern=r'^[0-9a-f]{64}$')
    name:str=Field(min_length=1,max_length=200)
    position:str=Field(min_length=1,max_length=200)
    consent:Literal[True]
    strokes:list[list[tuple[float,float]]]=Field(min_length=1,max_length=100)

    @model_validator(mode='after')
    def ink(self):
        coords=[p for stroke in self.strokes for p in stroke]
        if (not self.name.strip() or not self.position.strip() or len(coords)<8 or len(coords)>8000
            or any(not math.isfinite(v) or v<0 or v>1 for p in coords for v in p)
            or sum(math.dist(a,b) for stroke in self.strokes for a,b in zip(stroke,stroke[1:]))<0.05):
            raise ValueError('Tanda tangan harus berisi goresan nyata dan nama/jabatan PIC')
        return self


@router.post('/pic-signature',status_code=201)
def sign(identifier:UUID,data:SignatureInput,user=Depends(current),session:Session=Depends(db)):
    visit=owner_lock(session,identifier,user);old=replay(session,identifier,user,data,SIGN_ACTION)
    if old:return {'visit':detail(session,visit),'completion':completion_info(session,visit),'replayed':True}
    body=document(session,visit);errors,_=validation(body)
    if errors:raise HTTPException(409,{'message':'Laporan belum lengkap','errors':errors})
    if digest(body)!=data.document_digest:raise HTTPException(409,'Isi laporan berubah. PIC perlu meninjau ulang.')
    visit=advance(session,identifier,user,data.expected_version)
    snapshot={'request_digest':digest(jsonable_encoder(data)),'document':body,'document_digest':digest(body),
        'signed_at':datetime.now(timezone.utc).isoformat(),'signature':{'name':data.name.strip(),
        'position':data.position.strip(),'consent':True,'strokes':data.strokes}}
    session.add(m.HotelVisitEvent(id=data.id,visit_id=identifier,actor_id=user.id,version=visit.version,
        action=SIGN_ACTION,snapshot=jsonable_encoder(snapshot)))
    save(session)
    return {'visit':detail(session,visit),'completion':completion_info(session,visit),'replayed':False}


def require_complete(session,visit):
    info=completion_info(session,visit)
    if not info['ready'] or not info['signature']:
        raise HTTPException(409,{'message':'Lengkapi laporan dan tanda tangan PIC terbaru sebelum submit',
            'errors':info['errors']+([] if info['signature'] else ['Tanda tangan PIC belum ada atau isi laporan telah berubah'])})


def report_filename(data,preview=False):
    name=unicodedata.normalize('NFKD',data['hotel']['name']).encode('ascii','ignore').decode()
    name=re.sub(r'[^A-Za-z0-9 _-]+',' ',name)
    name=re.sub(r'\s+',' ',name).strip()[:120] or 'Lokasi'
    period=data['planned_date'][:7]
    return f'Nusa Maintenance-{"DRAF-" if preview else ""}{name}-{period}.pdf'


@router.get('/report.pdf')
def report_pdf(identifier:UUID,user=Depends(current),session:Session=Depends(db)):
    visit=visible(session,identifier,user);signed=current_signature(session,visit)
    if not signed:raise HTTPException(409,'Tanda tangan PIC terbaru diperlukan sebelum PDF final tersedia')
    from app.maintenance_pdf import make_pdf
    for photo in signed.snapshot['document']['photos']:file_bytes(photo)
    data=make_pdf(signed.snapshot,visit.status)
    return Response(data,media_type='application/pdf',headers={'Cache-Control':'private, no-store',
        'Content-Disposition':f'attachment; filename="{report_filename(signed.snapshot["document"])}"'})


@router.get('/report-download')
def report_download(identifier:UUID,user=Depends(current),session:Session=Depends(db)):
    response=report_pdf(identifier,user,session)
    return {'filename':response.headers['content-disposition'].split('filename="')[1].rstrip('"'),'content_type':'application/pdf',
        'data_base64':base64.b64encode(response.body).decode()}


@router.get('/report-preview-download')
def preview_download(identifier:UUID,user=Depends(current),session:Session=Depends(db)):
    visit=visible(session,identifier,user);data=document(session,visit)
    for photo in data['photos']:file_bytes(photo)
    from app.maintenance_pdf import make_pdf
    pdf=make_pdf({'document':data,'document_digest':digest(data),'signed_at':'Belum ditandatangani',
        'signature':{'name':'Belum ditandatangani','position':'-','strokes':[]}},visit.status,preview=True)
    return {'filename':report_filename(data,preview=True),'content_type':'application/pdf','data_base64':base64.b64encode(pdf).decode()}
