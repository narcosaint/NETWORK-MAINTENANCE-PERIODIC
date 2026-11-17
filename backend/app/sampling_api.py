"""Server master sampling. Disabled until the reviewed schema is installed."""
import os
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app import models as m, sampling_schemas as s
from app.api import current, supervisor, db, get, save


def master_enabled():
    return os.environ.get('SAMPLING_MASTER_ENABLED') == 'true'


def available(user=Depends(current)):
    if not master_enabled():
        raise HTTPException(503, 'Master sampling belum diaktifkan; schema harus direview dan dipasang dahulu')


router = APIRouter(prefix='/hotels/{hotel_id}/floors', tags=['Sampling master'],
                   dependencies=[Depends(available)])


def hotel(session, hotel_id, user, lock=False):
    site = session.scalar(select(m.Hotel).where(m.Hotel.id == hotel_id).with_for_update()) if lock else get(session, m.Hotel, hotel_id)
    if site is None:
        raise HTTPException(404, 'Hotel tidak ditemukan')
    if user.role != 'supervisor' and not session.scalar(select(m.HotelVisit.id).where(
            m.HotelVisit.hotel_id == hotel_id, m.HotelVisit.technician_id == user.id).limit(1)):
        raise HTTPException(404, 'Hotel tidak ditemukan')
    return site


def floor(session, hotel_id, floor_id, lock=False):
    obj = session.scalar(select(m.HotelFloor).where(
        m.HotelFloor.id == floor_id, m.HotelFloor.hotel_id == hotel_id).with_for_update()) if lock else session.get(m.HotelFloor, floor_id)
    if obj is None or obj.hotel_id != hotel_id:
        raise HTTPException(404, 'Lantai tidak ditemukan')
    return obj


def active(obj):
    if obj.archived_at is not None:
        raise HTTPException(409, 'Master sudah diarsipkan')


def device(session, identifier, hotel_id):
    if identifier is None:
        return
    obj = session.scalar(select(m.Device).where(m.Device.id == identifier).with_for_update())
    if obj is None or obj.hotel_id != hotel_id or obj.device_type != 'ap':
        raise HTTPException(422, 'Pilih AP dari hotel yang sama')


def create_once(session, model, values):
    existing = session.get(model, values['id'])
    if existing is not None:
        if existing.archived_at is not None or any(getattr(existing, key) != value for key, value in values.items()):
            raise HTTPException(409, 'UUID sudah dipakai untuk data berbeda')
        return existing
    obj = model(**values)
    session.add(obj)
    save(session)
    session.refresh(obj)
    return obj


def patch(session, obj, data):
    values = data.model_dump(exclude_unset=True, exclude={'expected_version'})
    if 'archived' in values:
        archive = values.pop('archived')
        if not archive and obj.archived_at is not None:
            raise HTTPException(409, 'Buat master baru untuk menggantikan arsip')
        if archive:
            values['archived_at'] = datetime.now(timezone.utc)
    active(obj)
    result = session.execute(update(type(obj)).where(
        type(obj).id == obj.id, type(obj).version == data.expected_version,
        type(obj).archived_at.is_(None),
    ).values(**values, version=type(obj).version + 1), execution_options={'synchronize_session': False})
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'Versi berubah. Muat ulang dahulu.')
    save(session)
    session.refresh(obj)
    return obj


@router.get('', response_model=list[s.FloorOutput])
def list_floors(hotel_id: UUID, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
                include_archived: bool = False, user=Depends(current), session: Session = Depends(db)):
    hotel(session, hotel_id, user)
    query = select(m.HotelFloor).where(m.HotelFloor.hotel_id == hotel_id)
    if not include_archived:
        query = query.where(m.HotelFloor.archived_at.is_(None))
    return session.scalars(query.order_by(m.HotelFloor.position, m.HotelFloor.id).offset(offset).limit(limit)).all()


@router.post('', response_model=s.FloorOutput, status_code=201)
def create_floor(hotel_id: UUID, data: s.FloorCreate, user=Depends(supervisor), session: Session = Depends(db)):
    hotel(session, hotel_id, user, lock=True)
    return create_once(session, m.HotelFloor, {**data.model_dump(), 'hotel_id': hotel_id})


@router.patch('/{floor_id}', response_model=s.FloorOutput)
def patch_floor(hotel_id: UUID, floor_id: UUID, data: s.FloorPatch,
                user=Depends(supervisor), session: Session = Depends(db)):
    hotel(session, hotel_id, user, lock=True)
    return patch(session, floor(session, hotel_id, floor_id, lock=True), data)


@router.get('/{floor_id}/sampling-points', response_model=list[s.PointOutput])
def list_points(hotel_id: UUID, floor_id: UUID, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
                include_archived: bool = False, user=Depends(current), session: Session = Depends(db)):
    hotel(session, hotel_id, user)
    floor(session, hotel_id, floor_id)
    query = select(m.SamplingPoint).where(m.SamplingPoint.floor_id == floor_id)
    if not include_archived:
        query = query.where(m.SamplingPoint.archived_at.is_(None))
    return session.scalars(query.order_by(m.SamplingPoint.position, m.SamplingPoint.id).offset(offset).limit(limit)).all()


@router.post('/{floor_id}/sampling-points', response_model=s.PointOutput, status_code=201)
def create_point(hotel_id: UUID, floor_id: UUID, data: s.PointCreate,
                 user=Depends(supervisor), session: Session = Depends(db)):
    hotel(session, hotel_id, user, lock=True)
    active(floor(session, hotel_id, floor_id, lock=True))
    device(session, data.device_id, hotel_id)
    return create_once(session, m.SamplingPoint, {**data.model_dump(), 'floor_id': floor_id})


@router.patch('/{floor_id}/sampling-points/{point_id}', response_model=s.PointOutput)
def patch_point(hotel_id: UUID, floor_id: UUID, point_id: UUID, data: s.PointPatch,
                user=Depends(supervisor), session: Session = Depends(db)):
    hotel(session, hotel_id, user, lock=True)
    active(floor(session, hotel_id, floor_id, lock=True))
    obj = get(session, m.SamplingPoint, point_id)
    if obj.floor_id != floor_id:
        raise HTTPException(404, 'Titik tidak ditemukan')
    device(session, data.device_id if 'device_id' in data.model_fields_set else obj.device_id, hotel_id)
    return patch(session, obj, data)
