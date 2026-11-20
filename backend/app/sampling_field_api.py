"""Assigned technicians append actual field locations; existing evidence is immutable."""
import os
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import Field, model_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app import models as m
from app.api import current, db, save
from app.hotel_api import visible, advance, detail
from app.sampling_api import master_enabled, device
from app.sampling_schemas import StrictInput


def field_enabled():
    return master_enabled() and os.environ.get('SAMPLING_FIELD_ENABLED') == 'true'


def available(user=Depends(current)):
    if not field_enabled():
        raise HTTPException(503, 'Penambahan lokasi lapangan belum diaktifkan pada server')


class FieldPoint(StrictInput):
    name: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=4000)
    device_id: UUID | None = None


class FieldLocations(StrictInput):
    id: UUID
    expected_visit_version: int = Field(ge=1)
    coverage_floor_id: UUID | None = None
    floor_name: str | None = Field(default=None, min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=4000)
    points: list[FieldPoint] = Field(min_length=1, max_length=32)

    @model_validator(mode='after')
    def valid_locations(self):
        if bool(self.coverage_floor_id) == bool(self.floor_name):
            raise ValueError('Pilih lantai kunjungan atau isi nama lantai baru')
        names = [point.name.casefold() for point in self.points]
        if len(names) != len(set(names)):
            raise ValueError('Nama titik dalam satu lantai harus berbeda')
        return self


router = APIRouter(prefix='/hotel-visits/{identifier}', tags=['Field sampling'],
                   dependencies=[Depends(available)])


def owner(session, identifier, user):
    visit = visible(session, identifier, user)
    if user.role != 'technician' or visit.technician_id != user.id:
        raise HTTPException(403, 'Hanya teknisi yang ditugaskan dapat menambah lokasi lapangan')
    return visit


@router.get('/sampling-inventory')
def inventory(identifier: UUID, user=Depends(current), session: Session = Depends(db)):
    visit = owner(session, identifier, user)
    return [{'id': ap.id, 'name': ap.name, 'mac_address': ap.mac_address} for ap in session.scalars(
        select(m.Device).where(m.Device.hotel_id == visit.hotel_id, m.Device.device_type == 'ap').order_by(m.Device.name, m.Device.id))]


@router.post('/sampling-locations', status_code=201)
def append_locations(identifier: UUID, data: FieldLocations, user=Depends(current), session: Session = Depends(db)):
    visit = owner(session, identifier, user)
    session.execute(select(m.HotelVisit.id).where(m.HotelVisit.id == identifier).with_for_update()).scalar_one()
    session.refresh(visit)
    if visit.technician_id != user.id:
        raise HTTPException(403, 'Penugasan teknisi berubah')
    payload = jsonable_encoder(data)
    previous = session.get(m.HotelVisitEvent, data.id)
    if previous:
        if (previous.visit_id != identifier or previous.actor_id != user.id or
                previous.action != 'field_sampling_added' or previous.snapshot.get('field_request') != payload):
            raise HTTPException(409, 'UUID penambahan lokasi sudah dipakai untuk data berbeda')
        return {'visit': detail(session, visit), 'replayed': True}
    if visit.status not in ('in_progress', 'revision_requested') or visit.version != data.expected_visit_version:
        raise HTTPException(409, 'Check-in dahulu dan gunakan versi kunjungan terbaru. Lokasi hanya ditambah saat kunjungan dapat diedit.')
    # Same lock order as coverage activation: visit first, hotel second. Serializes
    # name allocation across two visits to the same hotel without rewriting masters.
    site = session.scalar(select(m.Hotel).where(m.Hotel.id == visit.hotel_id).with_for_update())
    coverage = session.scalar(select(m.SamplingCoverage).where(m.SamplingCoverage.hotel_visit_id == identifier))
    if coverage is None:
        if data.coverage_floor_id:
            raise HTTPException(404, 'Lantai kunjungan tidak ditemukan')
        coverage = m.SamplingCoverage(hotel_visit_id=identifier, period=visit.planned_date.replace(day=1),
            created_by=user.id, hotel_snapshot={'id':str(site.id), 'name':site.name, 'address':site.address,
                'customer_name':site.customer_name, 'activation_request':{'origin':'technician_field'}},
            photo_policy_snapshot={'sampling_categories':[], 'infrastructure_categories':[]})
        session.add(coverage); session.flush()
    floors = session.scalars(select(m.SamplingCoverageFloor).where(m.SamplingCoverageFloor.coverage_id == coverage.id)).all()
    if data.coverage_floor_id:
        snapshot = next((floor for floor in floors if floor.id == data.coverage_floor_id), None)
        if snapshot is None:
            raise HTTPException(404, 'Lantai bukan bagian kunjungan ini')
        master = session.get(m.HotelFloor, snapshot.floor_id)
    else:
        matching=next((f for f in floors if f.name_snapshot.casefold()==data.floor_name.casefold()),None)
        if matching:
            removed=removed_session_ids(session,identifier)
            floor_points=session.scalars(select(m.SamplingSession).where(m.SamplingSession.coverage_floor_id==matching.id)).all()
            if any(str(point.id) not in removed for point in floor_points):
                raise HTTPException(409,'Lantai sudah ada; pilih lantai tersebut untuk menambah area')
            snapshot=matching;master=session.get(m.HotelFloor,matching.floor_id)
        else:
            if len(floors)>=100:raise HTTPException(422,'Batas lantai per kunjungan tercapai')
            masters = session.scalars(select(m.HotelFloor).where(m.HotelFloor.hotel_id == site.id)).all()
            master = next((f for f in masters if f.archived_at is None and f.name.casefold() == data.floor_name.casefold()), None)
            if master is None:
                master = m.HotelFloor(hotel_id=site.id, name=data.floor_name,
                    position=max((f.position for f in masters), default=-1)+1, default_sampling_count=2)
                session.add(master); session.flush()
            snapshot = m.SamplingCoverageFloor(coverage_id=coverage.id, floor_id=master.id,
                name_snapshot=data.floor_name, position_snapshot=max((f.position_snapshot for f in floors), default=-1)+1,
                target_count=max(2, master.default_sampling_count))
            session.add(snapshot); session.flush()
    if master.archived_at is not None:
        raise HTTPException(409, 'Master lantai sudah diarsipkan; lokasi historis tidak diubah')
    existing = session.scalars(select(m.SamplingSession).where(m.SamplingSession.coverage_floor_id == snapshot.id)).all()
    if len(existing) + len(data.points) > 500:
        raise HTTPException(422, 'Batas titik per lantai tercapai')
    removed=removed_session_ids(session,identifier)
    if any(p.name.casefold() in {s.point_snapshot['name'].casefold() for s in existing if str(s.id) not in removed} for p in data.points):
        raise HTTPException(409, 'Titik sudah ada pada kunjungan ini')
    masters = session.scalars(select(m.SamplingPoint).where(m.SamplingPoint.floor_id == master.id)).all()
    position = max((p.position for p in masters), default=-1)+1
    added = []
    removed=removed_session_ids(session,identifier)
    for index, point in enumerate(data.points):
        cancelled=next((old for old in existing if str(old.id) in removed and old.point_snapshot['name'].casefold()==point.name.casefold()),None)
        if cancelled is not None:
            added.append(str(cancelled.id));continue
        device(session, point.device_id, site.id)
        ap = session.get(m.Device, point.device_id) if point.device_id else None
        source = next((p for p in masters if p.archived_at is None and p.name.casefold() == point.name.casefold()), None)
        # Existing physical point may have a different AP/location this month.
        # Keep its master and prior snapshots; capture today's actual mapping only
        # in the new visit session and audit request.
        if source is None:
            source = m.SamplingPoint(floor_id=master.id, name=point.name, location=point.location,
                device_id=point.device_id, position=position+index)
            session.add(source); session.flush()
        result = m.SamplingSession(coverage_id=coverage.id, coverage_floor_id=snapshot.id,
            sampling_point_id=source.id, position_snapshot=max((p.position_snapshot for p in existing), default=-1)+1+index,
            point_snapshot={'id':str(source.id), 'name':point.name, 'location':point.location,
                'device':{'id':str(ap.id), 'name':ap.name, 'mac_address':ap.mac_address} if ap else None,
                'origin':'technician_field', 'added_by':str(user.id)})
        session.add(result); session.flush();added.append(str(result.id))
    snapshot.target_count = max(snapshot.target_count, len(existing)+len(added))
    visit = advance(session, identifier, user, data.expected_visit_version)
    session.flush()
    session.add(m.HotelVisitEvent(id=data.id, visit_id=identifier, actor_id=user.id, version=visit.version,
        action='field_sampling_added', reason=data.reason,
        snapshot={**jsonable_encoder(detail(session, visit)), 'field_request':payload, 'added_session_ids':added}))
    save(session)
    return {'visit':detail(session, visit), 'replayed':False}


def removed_session_ids(session,visit_id):
    removed=set()
    events=session.execute(select(m.HotelVisitEvent.action,
        m.HotelVisitEvent.snapshot['removed_session_id'],m.HotelVisitEvent.snapshot['added_session_ids']).where(
        m.HotelVisitEvent.visit_id==visit_id,m.HotelVisitEvent.action.in_(('field_area_removed','field_sampling_added'))).order_by(m.HotelVisitEvent.version))
    for action,removed_id,added_ids in events:
        if action=='field_area_removed':removed.add(removed_id)
        else:removed.difference_update(added_ids or [])
    return removed


class RemoveArea(StrictInput):
    id:UUID
    expected_visit_version:int=Field(ge=1)
    expected_session_version:int=Field(ge=1)


@router.post('/sampling-sessions/{session_id}/remove')
def remove_empty_area(identifier:UUID,session_id:UUID,data:RemoveArea,user=Depends(current),session:Session=Depends(db)):
    from app.sampling_observation_api import scoped_session
    visit=owner(session,identifier,user)
    _,point=scoped_session(session,identifier,session_id,user,include_removed=True)
    payload={'session_id':str(session_id),**jsonable_encoder(data)}
    previous=session.get(m.HotelVisitEvent,data.id)
    if previous:
        if previous.visit_id!=identifier or previous.actor_id!=user.id or previous.action!='field_area_removed' or previous.snapshot.get('request')!=payload:
            raise HTTPException(409,'UUID sudah digunakan untuk tindakan lain')
        return {'visit':detail(session,visit),'replayed':True}
    from app.maintenance_completion import photos
    if (session.scalar(select(m.SamplingObservation.id).where(m.SamplingObservation.session_id==session_id).limit(1))
        or session.scalar(select(m.SamplingSpeedtestAttempt.id).where(m.SamplingSpeedtestAttempt.session_id==session_id).limit(1))
        or any(p['session_id']==str(session_id) for p in photos(session,identifier))):
        raise HTTPException(409,'Area sudah memiliki bukti; riwayat pengukuran harus dipertahankan')
    if point.version!=data.expected_session_version:raise HTTPException(409,'Versi area berubah; muat ulang')
    visit=advance(session,identifier,user,data.expected_visit_version)
    session.add(m.HotelVisitEvent(id=data.id,visit_id=identifier,actor_id=user.id,version=visit.version,
        action='field_area_removed',snapshot={'request':payload,'removed_session_id':str(session_id)}))
    save(session)
    return {'visit':detail(session,visit),'replayed':False}
