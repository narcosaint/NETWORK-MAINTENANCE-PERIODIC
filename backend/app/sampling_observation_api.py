"""Idempotent, versioned observations attached to one immutable sampling session."""
import os
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app import models as m
from app.api import db, current, save
from app.hotel_api import visible, detail
from app.sampling_api import master_enabled
from app.sampling_observation_schemas import ObservationCreate


def observations_enabled():
    return master_enabled() and os.environ.get('SAMPLING_OBSERVATIONS_ENABLED') == 'true'


def observation_available(user=Depends(current)):
    if not observations_enabled():
        raise HTTPException(503, 'Penyimpanan observasi titik belum diaktifkan')


router = APIRouter(prefix='/hotel-visits/{identifier}/sampling-sessions/{session_id}',
    tags=['Sampling observations'], dependencies=[Depends(observation_available)])


def scoped_session(session, identifier, session_id, user):
    visit = visible(session, identifier, user)
    point = session.scalar(select(m.SamplingSession).join(m.SamplingCoverage,
        m.SamplingCoverage.id == m.SamplingSession.coverage_id).where(
            m.SamplingSession.id == session_id, m.SamplingCoverage.hotel_visit_id == identifier))
    if point is None:
        raise HTTPException(404, 'Sesi sampling tidak ditemukan')
    return visit, point


def observation_info(record):
    return {'id': record.id, 'session_id': record.session_id, 'actor_id': record.actor_id,
        'session_version': record.session_version, 'visit_version': record.visit_version,
        'captured_at': record.captured_at, 'received_at': record.received_at,
        'notes': record.payload['notes'], 'wifi_connection': record.payload['wifi_connection'],
        'wifi_scan': record.payload['wifi_scan'], 'measurement_trust': 'client_reported',
        'radio_verified': False, 'completion_accepted': False}


@router.get('/observations')
def read_observations(identifier: UUID, session_id: UUID, offset: int = 0, limit: int = 50,
                      user=Depends(current), session: Session = Depends(db)):
    scoped_session(session, identifier, session_id, user)
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Invalid pagination')
    records = session.scalars(select(m.SamplingObservation).where(m.SamplingObservation.session_id == session_id)
        .order_by(m.SamplingObservation.session_version.desc()).offset(offset).limit(limit)).all()
    return [observation_info(record) for record in records]


@router.post('/observations', status_code=201)
def write_observation(identifier: UUID, session_id: UUID, data: ObservationCreate,
                      user=Depends(current), session: Session = Depends(db)):
    visit, point = scoped_session(session, identifier, session_id, user)
    if user.role != 'technician' or visit.technician_id != user.id:
        raise HTTPException(403, 'Hanya teknisi yang ditugaskan dapat menyimpan observasi')
    # All session writes serialize on the visit, like the existing report workflow.
    session.execute(select(m.HotelVisit.id).where(m.HotelVisit.id == identifier).with_for_update()).scalar_one()
    session.refresh(visit)
    session.refresh(point)
    payload = jsonable_encoder(data)
    previous = session.get(m.SamplingObservation, data.id)
    if previous:
        if previous.session_id != session_id or previous.actor_id != user.id or previous.payload != payload:
            raise HTTPException(409, 'UUID observasi sudah dipakai untuk data berbeda')
        return {'observation': observation_info(previous), 'visit': detail(session, visit), 'replayed': True}
    if visit.status not in ('in_progress', 'revision_requested'):
        raise HTTPException(409, 'Observasi hanya dapat disimpan pada kunjungan yang dapat diedit')
    if visit.version != data.expected_visit_version or point.version != data.expected_session_version:
        raise HTTPException(409, 'Versi kunjungan/sesi berubah. Draf tetap disimpan; tinjau sebelum mengirim ulang.')
    visit_change = session.execute(update(m.HotelVisit).where(m.HotelVisit.id == identifier,
        m.HotelVisit.version == data.expected_visit_version,
        m.HotelVisit.status.in_(('in_progress', 'revision_requested'))).values(
            version=m.HotelVisit.version + 1), execution_options={'synchronize_session': False})
    point_change = session.execute(update(m.SamplingSession).where(m.SamplingSession.id == session_id,
        m.SamplingSession.version == data.expected_session_version).values(
            version=m.SamplingSession.version + 1), execution_options={'synchronize_session': False})
    if visit_change.rowcount != 1 or point_change.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'Versi berubah. Muat ulang dahulu.')
    record = m.SamplingObservation(id=data.id, session_id=session_id, actor_id=user.id,
        session_version=data.expected_session_version + 1, visit_version=data.expected_visit_version + 1,
        captured_at=data.captured_at, payload=payload)
    session.add(record)
    save(session)
    session.refresh(visit)
    session.refresh(record)
    return {'observation': observation_info(record), 'visit': detail(session, visit), 'replayed': False}
