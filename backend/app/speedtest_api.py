"""Purpose-bound LibreSpeed transfers and immutable, provenance-aware results."""
import asyncio
import hashlib
import hmac
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect
from app import models as m, schemas as s, speedtest_schemas as st
from app.api import db, current, save, get
from app.hotel_api import visible, selected, advance, detail, speedtest_info

router = APIRouter(tags=['Automatic speedtests'])
_lock = threading.Lock()
_live = {}
DOWNLOAD_LIMIT = 512 * 1024 * 1024
UPLOAD_LIMIT = 128 * 1024 * 1024
CHUNK = 64 * 1024
RESPONSE_BYTES = 4 * 1024 * 1024
TTL = 180
NO_CACHE = {'Cache-Control':'no-store, no-cache, must-revalidate, no-transform', 'Content-Encoding':'identity'}


def direct_origin(request):
    configured = os.environ.get('PUBLIC_SPEEDTEST_ORIGIN', '').rstrip('/')
    parsed = urlsplit(configured)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        return False
    return (request.headers.get('origin') == configured and request.url.scheme == 'https'
            and request.headers.get('host') == parsed.netloc)


def summary(run):
    info = speedtest_info(run)
    return {**info, 'can_apply':run.sampling_session_id is None and not run.context.get('sampling_session_id') and info['status']=='completed' and run.context.get('transport')=='direct_https'
                        and run.context.get('network')=='hotel_wifi' and run.context.get('wifi_confirmed') is True}


@router.post('/hotel-visits/{identifier}/devices/{item_id}/speedtests', status_code=201)
def start_test(identifier: UUID, item_id: UUID, data: st.StartSpeedtest, request: Request,
               user=Depends(current), session: Session = Depends(db)):
    visit = advance(session, identifier, user, data.expected_version)
    item = selected(session, identifier, item_id)
    if item.device_snapshot['device_type'] != 'ap':
        raise HTTPException(422, 'Speedtest sampling harus dikaitkan ke AP yang dipilih')
    run, token = allocate_run(session, item_id, data, request, user)
    return commit_run(session, run, token, visit)


def allocate_run(session, item_id, data, request, user, context_extra=None, sampling_session_id=None):
    now = datetime.now(timezone.utc)
    session.execute(update(m.NetworkSpeedtest).where(m.NetworkSpeedtest.status=='running',
        m.NetworkSpeedtest.expires_at < now).values(status='failed',error='Sesi pengukuran kedaluwarsa',finished_at=now))
    run = m.NetworkSpeedtest(visit_device_id=item_id, sampling_session_id=sampling_session_id, actor_id=user.id, band=data.band,
        expires_at=now+timedelta(seconds=TTL), context={
            **data.model_dump(exclude={'expected_version','band'}),
            'transport':'direct_https' if direct_origin(request) else 'diagnostic_tunnel_or_local',
            'endpoint_origin':str(request.headers.get('origin') or request.base_url).rstrip('/'),
            'engine':'LibreSpeed browser', 'measurement_trust':'browser_reported',
            'radio_verified':False, 'transport_validation':'configured_https_origin_not_network_attestation', 'endpoint_path':'/network-speedtests/transfer/',
        })
    if context_extra:
        run.context = {**run.context, **context_extra}
    session.add(run)
    session.flush()
    token = secrets.token_urlsafe(32)
    with _lock:
        for key, value in list(_live.items()):
            if value['until'] < time.monotonic():
                _live.pop(key, None)
        if len(_live) >= 2 or any(value['actor_id']==user.id for value in _live.values()):
            raise HTTPException(429, 'Tunggu pengukuran aktif selesai sebelum memulai lagi')
        _live[run.id]={'hash':hashlib.sha256(token.encode()).digest(),'until':time.monotonic()+TTL,
                      'actor_id':user.id,'worker_origin':run.context.get('worker_origin'),'download':0,'upload':0,'pings':0,'error':None}
    return run, token


def commit_run(session, run, token, visit):
    try:
        save(session)
    except Exception:
        with _lock:
            _live.pop(run.id,None)
        raise
    return {**summary(run),'transfer_token':token,'visit_version':visit.version,
            'duration_seconds':8,'download_limit_bytes':DOWNLOAD_LIMIT,'upload_limit_bytes':UPLOAD_LIMIT,
            'transfer_base':f'/network-speedtests/transfer/{run.id}'}


def transfer(run_id, request):
    provided=request.headers.get('x-speedtest-token','')
    digest=hashlib.sha256(provided.encode()).digest()
    with _lock:
        live=_live.get(run_id)
        if not live or live['until']<time.monotonic() or not hmac.compare_digest(digest,live['hash']):
            raise HTTPException(401, 'Sesi transfer tidak valid atau kedaluwarsa')
        if live['error']:
            raise HTTPException(429, live['error'])
        return live


def count(live, key, size, limit):
    with _lock:
        if live[key]+size>limit:
            live['error']='Batas volume pengujian tercapai; hasil pengukuran tidak diterima'
            raise HTTPException(429, live['error'])
        live[key]+=size


@router.get('/network-speedtests/transfer/{run_id}/ping')
def ping(run_id: UUID, request: Request):
    live=transfer(run_id,request)
    with _lock:
        live['pings']+=1
        if live['pings']>100:
            live['error']='Batas permintaan ping tercapai'
            raise HTTPException(429,live['error'])
    return Response('',headers=NO_CACHE)


@router.get('/network-speedtests/transfer/{run_id}/download')
def download(run_id: UUID, request: Request):
    live=transfer(run_id,request)
    # Reserve before response headers: exceeding the cap is a real HTTP error.
    count(live,'download',RESPONSE_BYTES,DOWNLOAD_LIMIT)
    chunk=os.urandom(CHUNK)
    async def chunks():
        for _ in range(RESPONSE_BYTES//CHUNK):
            if await request.is_disconnected():
                return
            yield chunk
    return StreamingResponse(chunks(),media_type='application/octet-stream',
            headers={**NO_CACHE,'Content-Length':str(RESPONSE_BYTES)})


@router.post('/network-speedtests/transfer/{run_id}/upload')
async def upload(run_id: UUID, request: Request):
    live=transfer(run_id,request)
    received=0
    try:
        async with asyncio.timeout(30):
            async for chunk in request.stream():
                received+=len(chunk)
                if received>16*1024*1024:
                    with _lock:live['error']='Ukuran unggahan pengujian terlalu besar'
                    raise HTTPException(413,live['error'])
                count(live,'upload',len(chunk),UPLOAD_LIMIT)
    except TimeoutError:
        with _lock:live['error']='Waktu transfer unggahan habis'
        raise HTTPException(408,live['error'])
    except ClientDisconnect:
        # LibreSpeed deliberately aborts in-flight streams at the phase boundary.
        return Response('',headers=NO_CACHE)
    return Response('',headers=NO_CACHE)


def owned_run(session, run_id, user):
    run=get(session,m.NetworkSpeedtest,run_id)
    if run.sampling_session_id is not None:
        point=get(session,m.SamplingSession,run.sampling_session_id)
        coverage=get(session,m.SamplingCoverage,point.coverage_id)
        visible(session,coverage.hotel_visit_id,user)
        return run,None
    if run.visit_device_id is None:
        raise HTTPException(404, 'Sesi pengujian tidak ditemukan')
    item=get(session,m.HotelVisitDevice,run.visit_device_id)
    visible(session,item.visit_id,user)
    return run,item


@router.post('/network-speedtests/{run_id}/finish')
def finish_test(run_id: UUID, data: st.FinishSpeedtest, user=Depends(current), session: Session = Depends(db)):
    run, _ = owned_run(session, run_id, user)
    if run.sampling_session_id is not None or run.context.get('sampling_session_id'):
        raise HTTPException(409, 'Gunakan endpoint finish sesi sampling beserta bukti koneksi akhir')
    return finish_run(run_id, data, user, session)


def finish_run(run_id, data, user, session, commit=True):
    run,item=owned_run(session,run_id,user)
    run=session.scalar(select(m.NetworkSpeedtest).where(m.NetworkSpeedtest.id==run_id).with_for_update().execution_options(populate_existing=True))
    if run.status!='running':
        raise HTTPException(409,'Hasil pengukuran sudah disimpan; muat ulang untuk melihatnya')
    if user.id!=run.actor_id or user.role!='technician':
        raise HTTPException(403,'Hanya teknisi penguji dapat menyimpan hasil')
    with _lock:
        live=_live.pop(run_id,None)
    status=data.status
    error=data.error
    if not live or live['until']<time.monotonic():
        status='failed';error='Sesi pengukuran terputus atau kedaluwarsa; ulangi pengujian'
    elif live['error']:
        status='failed';error=live['error']
    elif status=='completed' and (live['pings']<3 or live['download']<=0 or live['upload']<=0):
        status='failed';error='Transfer download/upload/ping belum lengkap'
    context={**run.context,'server_observed':{label:live.get(key,0) if live else 0 for key,label in [('download','download_budget_bytes'),('upload','upload_received_bytes'),('pings','ping_requests')]}}
    result=session.execute(update(m.NetworkSpeedtest).where(m.NetworkSpeedtest.id==run_id,
            m.NetworkSpeedtest.status=='running').values(status=status,error=error,
            finished_at=datetime.now(timezone.utc),context=context,
            metrics=data.metrics.model_dump() if status=='completed' else None),
            execution_options={'synchronize_session':False})
    if result.rowcount!=1:
        raise HTTPException(409,'Hasil pengukuran sudah disimpan; muat ulang untuk melihatnya')
    if commit:save(session)
    else:session.flush()
    session.refresh(run)
    return summary(run)


@router.get('/network-speedtests/{run_id}')
def read_test(run_id: UUID, user=Depends(current), session: Session = Depends(db)):
    run,_=owned_run(session,run_id,user)
    return summary(run)


@router.post('/hotel-visits/{identifier}/devices/{item_id}/speedtests/{run_id}/apply')
def apply_test(identifier: UUID,item_id: UUID,run_id: UUID,data: s.VisitVersion,
               user=Depends(current),session: Session = Depends(db)):
    visit=advance(session,identifier,user,data.expected_version)
    item=selected(session,identifier,item_id)
    run=get(session,m.NetworkSpeedtest,run_id)
    if run.visit_device_id!=item_id or run.actor_id!=user.id:
        raise HTTPException(404,'Hasil tidak terkait AP sampling ini')
    if not summary(run)['can_apply']:
        raise HTTPException(409,'Hasil diagnostik/tunnel, seluler, gagal atau jaringan tidak terkonfirmasi tidak dapat dipakai sebagai hasil AP')
    result=dict(item.result)
    band=dict(result.get(run.band) or {})
    band.update(status='measured',bandwidth_mbps=run.metrics['download_mbps'])
    if band.get('signal_dbm') is None or band.get('channel') is None:
        band['reason']=band.get('reason') or 'Sinyal/channel belum dicatat; lengkapi hasil analyzer atau alasan ketidaktersediaan'
    result[run.band]=band
    provenance=dict(result.get('automatic_speedtests') or {})
    provenance[run.band]=jsonable_encoder(summary(run))
    result['automatic_speedtests']=provenance
    item.result=result
    save(session)
    return detail(session,visit)
