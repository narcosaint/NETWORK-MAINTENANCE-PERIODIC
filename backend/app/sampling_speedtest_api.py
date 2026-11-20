"""Point-scoped LibreSpeed attempts; legacy AP measurements remain independent."""
import os
from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID, uuid5
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import Field, model_validator
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app import models as m
from app.api import current, db, save, get
from app.hotel_api import detail, advance
from app.sampling_api import master_enabled
from app.sampling_schemas import StrictInput
from app.sampling_observation_schemas import WifiConnection
from app.sampling_observation_api import scoped_session
from app import speedtest_api as engine, speedtest_schemas as speed


def speedtests_enabled():
    return master_enabled() and os.environ.get('SAMPLING_SPEEDTEST_ENABLED') == 'true'


def available(user=Depends(current)):
    if not speedtests_enabled():
        raise HTTPException(503, 'Speedtest per sesi belum diaktifkan')


class AttemptVersion(StrictInput):
    id: UUID
    expected_visit_version: int = Field(ge=1)
    expected_session_version: int = Field(ge=1)


class BindingSnapshot(StrictInput):
    id: UUID
    network_handle: str = Field(pattern=r'^[0-9]{1,30}$')
    source: str = Field(pattern=r'^android_native$')


class StartAttempt(AttemptVersion):
    connection: WifiConnection
    binding: BindingSnapshot | None = None


class FailedAttempt(AttemptVersion):
    reason: str = Field(min_length=1, max_length=5000)


class SessionMetrics(speed.Metrics):
    jitter_ms: float | None = Field(default=None, ge=0, le=120000, allow_inf_nan=False)


class SessionResult(speed.FinishSpeedtest):
    metrics: SessionMetrics | None = None


class FinishAttempt(StrictInput):
    result: SessionResult
    connection: WifiConnection | None = None
    binding: BindingSnapshot | None = None

    @model_validator(mode='after')
    def require_reason(self):
        if self.result.status != 'completed' and not self.result.error:
            raise ValueError('Pengujian gagal/dibatalkan wajib alasan')
        return self


router = APIRouter(prefix='/hotel-visits/{identifier}/sampling-sessions/{session_id}',
    tags=['Sampling speedtests'], dependencies=[Depends(available)])


def attempt_info(session, attempt):
    run = engine.summary(get(session, m.NetworkSpeedtest, attempt.run_id)) if attempt.run_id else None
    failed = not run or run['status'] == 'failed'
    return {'id': attempt.id, 'session_id': attempt.session_id, 'created_at': attempt.created_at,
        'run': run, 'status': run['status'] if run else 'failed',
        'error': run['error'] if run else attempt.failure_reason,
        'finding': (run['error'] if run else attempt.failure_reason) if failed else None,
        'completion_accepted': False}


def lock_point(session, identifier, session_id, user):
    visit, point = scoped_session(session, identifier, session_id, user)
    if user.role != 'technician' or visit.technician_id != user.id:
        raise HTTPException(403, 'Hanya teknisi yang ditugaskan dapat menguji titik')
    session.execute(select(m.HotelVisit.id).where(m.HotelVisit.id == identifier).with_for_update()).scalar_one()
    session.refresh(visit); session.refresh(point)
    return visit, point


def replay(session, data, session_id, user):
    existing = session.get(m.SamplingSpeedtestAttempt, data.id)
    if existing:
        if existing.session_id != session_id or existing.actor_id != user.id or existing.request_payload != jsonable_encoder(data):
            raise HTTPException(409, 'UUID percobaan sudah dipakai untuk data berbeda')
    return existing


def check_versions(visit, point, data):
    if visit.status not in ('in_progress', 'revision_requested') or visit.version != data.expected_visit_version or point.version != data.expected_session_version:
        raise HTTPException(409, 'Versi atau status kunjungan/sesi berubah. Muat ulang dahulu.')


def advance_point(session, point, expected):
    changed = session.execute(update(m.SamplingSession).where(m.SamplingSession.id == point.id,
        m.SamplingSession.version == expected).values(version=m.SamplingSession.version + 1),
        execution_options={'synchronize_session':False})
    if changed.rowcount != 1:
        raise HTTPException(409, 'Sesi berubah. Muat ulang dahulu.')


@router.get('/speedtests')
def history(identifier: UUID, session_id: UUID, offset: int = 0, limit: int = 50,
            user=Depends(current), session: Session = Depends(db)):
    scoped_session(session, identifier, session_id, user)
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Invalid pagination')
    return [attempt_info(session, item) for item in session.scalars(select(m.SamplingSpeedtestAttempt).where(
        m.SamplingSpeedtestAttempt.session_id == session_id).order_by(m.SamplingSpeedtestAttempt.created_at.desc(),
        m.SamplingSpeedtestAttempt.id.desc()).offset(offset).limit(limit))]


@router.post('/speedtests/failures', status_code=201)
def record_failure(identifier: UUID, session_id: UUID, data: FailedAttempt,
                   user=Depends(current), session: Session = Depends(db)):
    visit, point = lock_point(session, identifier, session_id, user)
    previous = replay(session, data, session_id, user)
    if previous:
        return {'attempt':attempt_info(session, previous), 'visit':detail(session, visit), 'replayed':True}
    check_versions(visit, point, data)
    visit = advance(session, identifier, user, data.expected_visit_version)
    advance_point(session, point, data.expected_session_version)
    attempt = m.SamplingSpeedtestAttempt(id=data.id, session_id=session_id, actor_id=user.id,
        failure_reason=data.reason, request_payload=jsonable_encoder(data))
    session.add(attempt); save(session)
    return {'attempt':attempt_info(session, attempt), 'visit':detail(session, visit), 'replayed':False}


@router.post('/speedtests', status_code=201)
def start(identifier: UUID, session_id: UUID, data: StartAttempt, request: Request,
          user=Depends(current), session: Session = Depends(db)):
    visit, point = lock_point(session, identifier, session_id, user)
    previous = replay(session, data, session_id, user)
    if previous:
        return {'attempt':attempt_info(session, previous), 'visit':detail(session, visit), 'replayed':True}
    check_versions(visit, point, data)
    bssid = data.connection.bssid
    if not bssid or bssid.lower() in ('02:00:00:00:00:00','00:00:00:00:00:00'):
        raise HTTPException(422, 'BSSID aktual diperlukan untuk mendeteksi pergantian AP')
    frequency = data.connection.frequency_mhz
    if frequency is None or not (2400 <= frequency <= 2500 or 5000 <= frequency < 5925):
        raise HTTPException(422, 'Pengukuran hanya mendukung Wi-Fi 2.4/5 GHz')
    visit = advance(session, identifier, user, data.expected_visit_version)
    advance_point(session, point, data.expected_session_version)
    legacy_start = speed.StartSpeedtest(expected_version=data.expected_visit_version,
        band='band_24' if frequency < 2500 else 'band_5', network='hotel_wifi', wifi_confirmed=True,
        observed_type='wifi', ssid=data.connection.ssid, bssid=bssid)
    run, token = engine.allocate_run(session, None, legacy_start, request, user, sampling_session_id=session_id, context_extra={
        'sampling_session_id':str(session_id), 'connection_start':jsonable_encoder(data.connection),
        'measurement_trust':'client_reported', 'sampling_eligible':False,
        'network':'connected_wifi', 'measurement_scope':'phone_connection',
        'binding_start':jsonable_encoder(data.binding),
        'worker_origin':'https://localhost' if data.binding else None,
        'transport':'direct_https' if data.binding and native_https_endpoint(request) else 'diagnostic_tunnel_or_local',
        'endpoint_origin':os.environ.get('PUBLIC_SPEEDTEST_ORIGIN','').rstrip('/') if data.binding and native_https_endpoint(request) else str(request.base_url).rstrip('/'),
        'transport_validation':'android_wifi_binding_client_reported' if data.binding else 'native_wifi_snapshot_does_not_prove_transfer_binding'})
    session.add(m.SamplingSpeedtestAttempt(id=data.id, session_id=session_id, run_id=run.id,
        actor_id=user.id, request_payload=jsonable_encoder(data)))
    response = engine.commit_run(session, run, token, visit)
    return {'attempt':attempt_info(session, session.get(m.SamplingSpeedtestAttempt, data.id)),
        'transfer':response, 'visit':detail(session, visit), 'replayed':False}


@router.post('/speedtests/{attempt_id}/finish')
def finish(identifier: UUID, session_id: UUID, attempt_id: UUID, data: FinishAttempt,
           user=Depends(current), session: Session = Depends(db)):
    visit, point = lock_point(session, identifier, session_id, user)
    attempt = get(session, m.SamplingSpeedtestAttempt, attempt_id)
    if visit.status not in ('in_progress', 'revision_requested'):
        raise HTTPException(409, 'Kunjungan tidak dapat diedit')
    if attempt.session_id != session_id or attempt.actor_id != user.id or not attempt.run_id:
        raise HTTPException(404, 'Percobaan pengujian tidak ditemukan')
    run = get(session, m.NetworkSpeedtest, attempt.run_id)
    if run.sampling_session_id is not None and run.sampling_session_id != session_id:
        raise HTTPException(404, 'Hasil bukan milik area ini')
    if run.status != 'running':
        raise HTTPException(409, 'Pengujian sudah berakhir. Muat ulang riwayat dahulu.')
    before = run.context['connection_start']
    after = jsonable_encoder(data.connection) if data.connection else None
    binding_end = jsonable_encoder(data.binding)
    result = data.result
    if result.status == 'completed' and (not after or not after['bssid'] or
            after['bssid'].lower() != before['bssid'].lower() or after['frequency_mhz'] != before['frequency_mhz']):
        result = speed.FinishSpeedtest(status='failed', error='Koneksi Wi-Fi/AP berubah atau tidak dapat diverifikasi saat selesai')
    if result.status == 'completed' and run.context.get('binding_start') and binding_end != run.context['binding_start']:
        result = speed.FinishSpeedtest(status='failed', error='Binding jaringan akhir tidak sesuai binding awal')
    # Hold the visit lock while the existing immutable finish path verifies actual transfers.
    visit = advance(session, identifier, user, visit.version)
    advance_point(session, point, point.version)
    run.context = {**run.context, 'connection_end':after, 'binding_end':binding_end}
    session.flush()
    engine.finish_run(attempt.run_id, result, user=user, session=session, commit=False)
    session.refresh(run)
    previous=session.scalar(select(m.SamplingObservation).where(m.SamplingObservation.session_id==session_id).order_by(m.SamplingObservation.session_version.desc()).limit(1))
    notes=dict(previous.payload['notes']) if previous else {'condition':'good','notes':'','findings':'','action':'','recommendation':''}
    if run.status!='completed':
        notes['condition']='attention'
        if not notes.get('findings'):notes['findings']=run.error or 'Pengujian tidak selesai'
    observation_payload={'id':str(uuid5(attempt.id,'wifi-connection')), 'expected_visit_version':visit.version-1,
        'expected_session_version':point.version,'captured_at':before['observed_at'],'notes':notes,
        'wifi_connection':before,'wifi_scan':None}
    session.add(m.SamplingObservation(id=UUID(observation_payload['id']),session_id=session_id,actor_id=user.id,
        session_version=point.version+1,visit_version=visit.version,captured_at=data.connection.observed_at if data.connection else datetime.fromisoformat(before['observed_at']),payload=observation_payload))
    save(session)
    return {'attempt':attempt_info(session, attempt), 'visit':detail(session, visit)}


def native_https_endpoint(request):
    configured = os.environ.get('PUBLIC_SPEEDTEST_ORIGIN','').rstrip('/')
    value = urlsplit(configured)
    return bool(value.scheme == 'https' and value.netloc and not value.path and not value.query and not value.fragment
        and not value.username and request.url.scheme == 'https' and request.headers.get('host') == value.netloc)
