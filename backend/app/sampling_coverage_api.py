"""Visit snapshots; technicians may append audited field scope without rewriting evidence."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, update, inspect, func
from sqlalchemy.orm import Session
from app import models as m, sampling_schemas as s
from app.api import current, supervisor, db, save
from app.hotel_api import visible
from app.sampling_api import available, hotel, device, master_enabled

router = APIRouter(tags=['Sampling coverage'])


@router.get('/sampling-capabilities')
def capabilities(user=Depends(current)):
    from app.sampling_observation_api import observations_enabled
    from app.sampling_speedtest_api import speedtests_enabled
    from app.sampling_field_api import field_enabled
    return {'field_locations_enabled':field_enabled(), 'master_enabled': master_enabled(), 'coverage_enabled': master_enabled(),
            'measurement_enabled': False, 'observations_enabled': observations_enabled(),
            'session_speedtests_enabled': speedtests_enabled()}


def coverage_info(session, coverage):
    from app.sampling_observation_api import observations_enabled
    from app.sampling_field_api import field_enabled
    from app.sampling_speedtest_api import speedtests_enabled, attempt_info
    floors = session.scalars(select(m.SamplingCoverageFloor).where(
        m.SamplingCoverageFloor.coverage_id == coverage.id).order_by(
        m.SamplingCoverageFloor.position_snapshot, m.SamplingCoverageFloor.id)).all()
    sessions = session.scalars(select(m.SamplingSession).where(
        m.SamplingSession.coverage_id == coverage.id).order_by(
        m.SamplingSession.position_snapshot, m.SamplingSession.id)).all()
    from app.sampling_field_api import removed_session_ids
    removed=removed_session_ids(session,coverage.hotel_visit_id)
    sessions=[point for point in sessions if str(point.id) not in removed]
    floors=[floor for floor in floors if any(point.coverage_floor_id==floor.id for point in sessions)]
    observations = {}
    attempts = {}
    if inspect(session.connection()).has_table('sampling_speedtest_attempts'):
        for attempt in session.scalars(select(m.SamplingSpeedtestAttempt).join(m.SamplingSession,
                m.SamplingSession.id == m.SamplingSpeedtestAttempt.session_id).where(m.SamplingSession.coverage_id == coverage.id)
                .order_by(m.SamplingSpeedtestAttempt.created_at, m.SamplingSpeedtestAttempt.id)):
            attempts.setdefault(attempt.session_id, []).append(attempt_info(session, attempt))
    if inspect(session.connection()).has_table('sampling_observations'):
        from app.sampling_observation_api import observation_info
        latest = select(m.SamplingObservation.session_id,
            func.max(m.SamplingObservation.session_version).label('version')).join(m.SamplingSession,
                m.SamplingSession.id == m.SamplingObservation.session_id).where(
                    m.SamplingSession.coverage_id == coverage.id).group_by(m.SamplingObservation.session_id).subquery()
        for record in session.scalars(select(m.SamplingObservation).join(latest,
                (latest.c.session_id == m.SamplingObservation.session_id) &
                (latest.c.version == m.SamplingObservation.session_version))):
            observations[record.session_id] = observation_info(record)
    from app.maintenance_completion import photos, point_completion
    evidence=photos(session,coverage.hotel_visit_id)
    return {'id': coverage.id, 'hotel_visit_id': coverage.hotel_visit_id,
            'field_locations_enabled':field_enabled(), 'observations_enabled': observations_enabled(),
            'session_speedtests_enabled': speedtests_enabled(),
            'period': coverage.period, 'created_at': coverage.created_at,
            'photo_policy': coverage.photo_policy_snapshot, 'completion_available': True,
            'floors': [{'id': floor.id, 'floor_id': floor.floor_id,
                'name': floor.name_snapshot, 'target_count': floor.target_count,
                'points': [{'id': point.id, 'sampling_point_id': point.sampling_point_id,
                    'name': point.point_snapshot['name'], 'location': point.point_snapshot['location'],
                    'device': point.point_snapshot['device'], 'status': point.status,
                    'completion':point_completion(point.id,observations.get(point.id),attempts.get(point.id,[]),coverage.photo_policy_snapshot,evidence),
                    'version': point.version, 'observation': observations.get(point.id), 'speedtests': attempts.get(point.id, [])} for point in sessions if point.coverage_floor_id == floor.id]
                } for floor in floors]}


@router.get('/hotel-visits/{identifier}/sampling-coverage', dependencies=[Depends(available)])
def read_coverage(identifier: UUID, user=Depends(current), session: Session = Depends(db)):
    visible(session, identifier, user)
    coverage = session.scalar(select(m.SamplingCoverage).where(m.SamplingCoverage.hotel_visit_id == identifier))
    return coverage_info(session, coverage) if coverage else None


def normalized_request(data):
    values = jsonable_encoder(data)
    values['floors'] = sorted(values['floors'], key=lambda item: item['id'])
    for floor in values['floors']:
        floor['points'] = sorted(floor['points'], key=lambda item: item['id'])
    for key in values['photo_policy']:
        values['photo_policy'][key] = sorted(set(values['photo_policy'][key]))
    return values


@router.post('/hotel-visits/{identifier}/sampling-coverage', dependencies=[Depends(available)], status_code=201)
def activate_coverage(identifier: UUID, data: s.CoverageCreate,
                      user=Depends(supervisor), session: Session = Depends(db)):
    visit = session.scalar(select(m.HotelVisit).where(m.HotelVisit.id == identifier).with_for_update())
    if visit is None:
        raise HTTPException(404, 'Kunjungan tidak ditemukan')
    request = normalized_request(data)
    previous = session.scalar(select(m.SamplingCoverage).where(m.SamplingCoverage.hotel_visit_id == identifier))
    if previous:
        if previous.hotel_snapshot['activation_request'] != request:
            raise HTTPException(409, 'Cakupan kunjungan sudah dibekukan dengan konfigurasi berbeda')
        return coverage_info(session, previous)
    if visit.status != 'assigned' or visit.checkin is not None or visit.version != data.expected_version:
        raise HTTPException(409, 'Cakupan hanya dapat dibuat sebelum check-in dengan versi kunjungan terbaru')
    site = hotel(session, visit.hotel_id, user, lock=True)
    floors = session.scalars(select(m.HotelFloor).where(m.HotelFloor.hotel_id == site.id,
        m.HotelFloor.archived_at.is_(None)).order_by(m.HotelFloor.id).with_for_update()).all()
    reviewed = {item.id: item for item in data.floors}
    if len(reviewed) != len(data.floors) or set(reviewed) != {item.id for item in floors}:
        raise HTTPException(409, 'Daftar lantai berubah. Tinjau master terbaru.')
    snapshots = []
    for floor in floors:
        points = session.scalars(select(m.SamplingPoint).where(m.SamplingPoint.floor_id == floor.id,
            m.SamplingPoint.archived_at.is_(None)).order_by(m.SamplingPoint.id).with_for_update()).all()
        versions = {point.id: point.version for point in reviewed[floor.id].points}
        if (floor.version != reviewed[floor.id].version or len(versions) != len(reviewed[floor.id].points)
                or versions != {point.id: point.version for point in points}):
            raise HTTPException(409, 'Titik atau versi master berubah. Tinjau master terbaru.')
        if len(points) < floor.default_sampling_count:
            raise HTTPException(409, f'Lengkapi titik nyata pada lantai {floor.name}; target {floor.default_sampling_count}')
        snapshots.append((floor, points))
    # Lock APs in a consistent order; snapshot inventory is not proof of connected radio.
    for device_id in sorted({point.device_id for _, points in snapshots for point in points if point.device_id}):
        device(session, device_id, site.id)
    coverage = m.SamplingCoverage(hotel_visit_id=visit.id, period=visit.planned_date.replace(day=1),
        hotel_snapshot={'id': str(site.id), 'name': site.name, 'address': site.address,
                        'customer_name': site.customer_name, 'activation_request': request},
        photo_policy_snapshot=request['photo_policy'], created_by=user.id)
    session.add(coverage)
    session.flush()
    for floor, points in snapshots:
        snapshot = m.SamplingCoverageFloor(coverage_id=coverage.id, floor_id=floor.id,
            name_snapshot=floor.name, position_snapshot=floor.position,
            target_count=max(floor.default_sampling_count, len(points)))
        session.add(snapshot)
        session.flush()
        for point in points:
            ap = session.get(m.Device, point.device_id) if point.device_id else None
            session.add(m.SamplingSession(coverage_id=coverage.id, coverage_floor_id=snapshot.id,
                sampling_point_id=point.id, position_snapshot=point.position,
                point_snapshot={'id': str(point.id), 'name': point.name, 'location': point.location,
                    'device': {'id': str(ap.id), 'name': ap.name, 'mac_address': ap.mac_address} if ap else None}))
    changed = session.execute(update(m.HotelVisit).where(m.HotelVisit.id == visit.id,
        m.HotelVisit.version == data.expected_version, m.HotelVisit.status == 'assigned').values(
            version=m.HotelVisit.version + 1), execution_options={'synchronize_session': False})
    if changed.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'Kunjungan berubah. Muat ulang dahulu.')
    save(session)
    return coverage_info(session, coverage)
