"""Hotel-wide visits, explicit sampling and private device photo evidence."""
import hashlib
import io
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select, update, delete, func, inspect
from sqlalchemy.orm import Session
from app import models as m, schemas as s, hotel_schemas as hs
from app.api import db, current, supervisor, get, save
from app.report_rules import site_report

router = APIRouter(prefix='/hotel-visits', tags=['Hotel visits'])
MAX_PHOTO_BYTES = 10 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000


def storage():
    return Path(os.environ.get('PHOTO_STORAGE_ROOT', '/app/storage/photos'))


def visible(session, identifier, user):
    visit = get(session, m.HotelVisit, identifier)
    if user.role == 'technician' and visit.technician_id != user.id:
        raise HTTPException(404, 'Kunjungan tidak ditemukan')
    return visit


def advance(session, identifier, user, version, statuses=('in_progress', 'revision_requested'), owner=True, **values):
    visit = visible(session, identifier, user)
    if owner and (user.role != 'technician' or visit.technician_id != user.id):
        raise HTTPException(403, 'Hanya teknisi yang ditugaskan dapat mengubah pemeriksaan')
    result = session.execute(update(m.HotelVisit).where(
        m.HotelVisit.id == identifier, m.HotelVisit.version == version,
        m.HotelVisit.status.in_(statuses),
    ).values(version=m.HotelVisit.version + 1, **values), execution_options={'synchronize_session': False})
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'Data kunjungan berubah atau status tidak sesuai. Muat ulang dahulu.')
    session.refresh(visit)
    return visit


def photo_info(photo):
    return {'id': photo.id, 'created_at': photo.created_at, 'uploaded_by': photo.uploaded_by,
            'sha256': photo.sha256, 'size_bytes': photo.size_bytes, 'width': photo.width,
            'height': photo.height, 'url': f'/hotel-visits/photos/{photo.id}'}


def device_info(session, item):
    photos = session.scalars(select(m.DevicePhoto).where(m.DevicePhoto.visit_device_id == item.id).order_by(m.DevicePhoto.created_at, m.DevicePhoto.id)).all()
    return {'id': item.id, 'device_id': item.device_id, 'device': item.device_snapshot,
            'floor': item.floor, 'point': item.point, 'result': item.result,
            'photos': [photo_info(photo) for photo in photos],
            'speedtests': [speedtest_info(run) for run in session.scalars(select(m.NetworkSpeedtest).where(
                m.NetworkSpeedtest.visit_device_id == item.id).order_by(m.NetworkSpeedtest.created_at, m.NetworkSpeedtest.id))]}


def visit_info(visit):
    return {'id': visit.id, 'hotel_id': visit.hotel_id, 'technician_id': visit.technician_id,
            'planned_date': visit.planned_date, 'status': visit.status, 'version': visit.version,
            'created_at': visit.created_at, 'checkin': visit.checkin, 'checkout': visit.checkout,
            'report': visit.report,
            'maintenance_completed': visit.status == 'approved' and visit.report.get('work_status') == 'completed'}


def detail(session, visit):
    result = {**visit_info(visit), 'site': s.HotelOutput.model_validate(get(session, m.Hotel, visit.hotel_id), from_attributes=True), 'devices': [device_info(session, item) for item in session.scalars(
        select(m.HotelVisitDevice).where(m.HotelVisitDevice.visit_id == visit.id).order_by(m.HotelVisitDevice.id))]}
    if inspect(session.connection()).has_table('sampling_coverages'):
        coverage = session.scalar(select(m.SamplingCoverage).where(m.SamplingCoverage.hotel_visit_id == visit.id))
        if coverage:
            from app.sampling_coverage_api import coverage_info
            result['sampling_coverage'] = coverage_info(session, coverage)
    return result


def event(session, visit, user, action, reason=None):
    session.flush()
    snapshot = {**detail(session, visit),
                'hotel': s.HotelOutput.model_validate(get(session, m.Hotel, visit.hotel_id), from_attributes=True),
                'technician': s.UserOutput.model_validate(get(session, m.User, visit.technician_id), from_attributes=True)}
    session.add(m.HotelVisitEvent(visit_id=visit.id, actor_id=user.id, version=visit.version,
                                action=action, reason=reason, snapshot=jsonable_encoder(snapshot)))


def selected(session, visit_id, item_id):
    item = get(session, m.HotelVisitDevice, item_id)
    if item.visit_id != visit_id:
        raise HTTPException(404, 'Perangkat kunjungan tidak ditemukan')
    return item


@router.post('', status_code=201)
def create_visit(data: hs.HotelVisitCreate, user=Depends(supervisor), session: Session = Depends(db)):
    site = get(session, m.Hotel, data.hotel_id)
    tech = get(session, m.User, data.technician_id)
    if tech.role != 'technician' or not tech.active:
        raise HTTPException(422, 'Pilih teknisi aktif')
    devices = session.scalars(select(m.Device).where(m.Device.hotel_id == data.hotel_id,
                                                      m.Device.device_type.in_(['router', 'switch']))).all()
    if not devices:
        raise HTTPException(422, 'Daftarkan router atau switch hotel sebelum membuat kunjungan')
    visit = m.HotelVisit(**data.model_dump(), report={'form_version': 2, 'customer_company': site.customer_name or site.name, 'site_profile': site.maintenance_profile or {}})
    session.add(visit)
    session.flush()
    for device in devices:
        session.add(m.HotelVisitDevice(visit_id=visit.id, device_id=device.id,
                    device_snapshot=jsonable_encoder(s.DeviceOutput.model_validate(device, from_attributes=True))))
    save(session)
    session.refresh(visit)
    return detail(session, visit)


@router.get('')
def list_visits(offset: int = 0, limit: int = 50, user=Depends(current), session: Session = Depends(db)):
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Pagination tidak valid')
    query = select(m.HotelVisit).order_by(m.HotelVisit.created_at.desc(), m.HotelVisit.id)
    if user.role == 'technician':
        query = query.where(m.HotelVisit.technician_id == user.id)
    return [visit_info(v) for v in session.scalars(query.offset(offset).limit(limit))]


@router.get('/photos/{photo_id}')
def read_photo(photo_id: UUID, user=Depends(current), session: Session = Depends(db)):
    photo = get(session, m.DevicePhoto, photo_id)
    item = get(session, m.HotelVisitDevice, photo.visit_device_id)
    visible(session, item.visit_id, user)
    path = storage() / photo.object_key
    if not path.is_file():
        raise HTTPException(404, 'Berkas foto tidak tersedia')
    return FileResponse(path, media_type='image/jpeg', headers={'Cache-Control': 'no-store',
                        'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'"})


@router.get('/{identifier}')
def read_visit(identifier: UUID, user=Depends(current), session: Session = Depends(db)):
    return detail(session, visible(session, identifier, user))


@router.post('/{identifier}/check-in')
def check_in(identifier: UUID, data: s.CheckIn, user=Depends(current), session: Session = Depends(db)):
    evidence = {**jsonable_encoder(data.model_dump(exclude={'expected_version'})), 'server_time': datetime.now(timezone.utc).isoformat()}
    visit = advance(session, identifier, user, data.expected_version, statuses=('assigned',), status='in_progress', checkin=evidence)
    save(session)
    return detail(session, visit)


@router.post('/{identifier}/samples', status_code=201)
def add_sample(identifier: UUID, data: hs.SampleCreate, user=Depends(current), session: Session = Depends(db)):
    visit = advance(session, identifier, user, data.expected_version)
    device = get(session, m.Device, data.device_id)
    if device.hotel_id != visit.hotel_id or device.device_type != 'ap':
        raise HTTPException(422, 'Pilih AP milik hotel kunjungan ini')
    session.add(m.HotelVisitDevice(visit_id=identifier, device_id=device.id, floor=data.floor, point=data.point,
                device_snapshot=jsonable_encoder(s.DeviceOutput.model_validate(device, from_attributes=True))))
    save(session)
    return detail(session, visit)


@router.delete('/{identifier}/samples/{item_id}')
def remove_sample(identifier: UUID, item_id: UUID, expected_version: int, user=Depends(current), session: Session = Depends(db)):
    visit = advance(session, identifier, user, expected_version, statuses=('in_progress',))
    item = selected(session, identifier, item_id)
    if item.device_snapshot['device_type'] != 'ap' or item.result:
        raise HTTPException(409, 'Hanya AP sampling yang belum diperiksa dapat dibatalkan')
    if session.scalar(select(m.DevicePhoto.id).where(m.DevicePhoto.visit_device_id == item_id).limit(1)):
        raise HTTPException(409, 'AP dengan bukti foto tidak dapat dihapus dari kunjungan')
    session.delete(item)
    save(session)
    return detail(session, visit)


@router.put('/{identifier}/devices/{item_id}/result')
def save_result(identifier: UUID, item_id: UUID, data: hs.DeviceResultSave, user=Depends(current), session: Session = Depends(db)):
    visit = advance(session, identifier, user, data.expected_version)
    item = selected(session, identifier, item_id)
    result = data.result.model_dump()
    provenance = item.result.get('automatic_speedtests') or {}
    retained = {band: info for band, info in provenance.items() if result.get(band, {}).get('status') == 'measured'
                and result.get(band, {}).get('bandwidth_mbps') == item.result.get(band, {}).get('bandwidth_mbps')}
    if retained:
        result['automatic_speedtests'] = retained
    item.result = {**result, 'recorded_at': datetime.now(timezone.utc).isoformat()}
    save(session)
    return detail(session, visit)


@router.put('/{identifier}/report')
def save_report(identifier: UUID, data: hs.HotelReportSave, user=Depends(current), session: Session = Depends(db)):
    visit = advance(session, identifier, user, data.expected_version)
    if visit.report.get('form_version') == 2 and data.report.form_version != 2:
        raise HTTPException(409, 'Gunakan form laporan terbaru; laporan tidak dapat diturunkan ke format lama')
    visit.report = site_report(data.report, get(session, m.Hotel, visit.hotel_id)) if data.report.form_version == 2 else data.report.model_dump()
    save(session)
    return detail(session, visit)


def clean_photo(payload, content_type):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(payload)) as original:
                expected = {'image/jpeg': 'JPEG', 'image/png': 'PNG', 'image/webp': 'WEBP'}
                if original.format != expected.get(content_type) or getattr(original, 'is_animated', False):
                    raise ValueError('Unsupported image type')
                original.load()
                if min(original.size) < 32:
                    raise ValueError('Image too small')
                image = ImageOps.exif_transpose(original).convert('RGB')
                result = io.BytesIO()
                image.save(result, 'JPEG', quality=90)
                return result.getvalue(), image.width, image.height
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, 'Foto harus JPEG/PNG/WebP statis yang valid, minimal 32 piksel dan maksimal 20 megapiksel')


@router.post('/{identifier}/devices/{item_id}/photos', status_code=201)
async def upload_photo(identifier: UUID, item_id: UUID, expected_version: int, request: Request,
                       user=Depends(current), session: Session = Depends(db)):
    visit = visible(session, identifier, user)
    if user.role != 'technician' or visit.technician_id != user.id:
        raise HTTPException(403, 'Hanya teknisi yang ditugaskan dapat mengunggah bukti')
    selected(session, identifier, item_id)
    content_type = request.headers.get('content-type', '').split(';')[0].lower()
    if content_type not in ('image/jpeg', 'image/png', 'image/webp'):
        raise HTTPException(415, 'Pilih foto JPEG, PNG atau WebP')
    payload = bytearray()
    async for chunk in request.stream():
        if len(payload) + len(chunk) > MAX_PHOTO_BYTES:
            raise HTTPException(413, 'Ukuran foto maksimal 10 MiB')
        payload.extend(chunk)
    image, width, height = clean_photo(payload, content_type)
    if len(image) > MAX_PHOTO_BYTES:
        raise HTTPException(413, 'Foto setelah normalisasi melebihi 10 MiB')
    visit = advance(session, identifier, user, expected_version)
    if session.scalar(select(func.count()).select_from(m.DevicePhoto).where(m.DevicePhoto.visit_device_id == item_id)) >= 10:
        raise HTTPException(409, 'Maksimal 10 foto per perangkat per kunjungan')
    root = storage()
    root.mkdir(parents=True, exist_ok=True)
    key = f'{uuid4().hex}.jpg'
    path = root / key
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(image)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        session.add(m.DevicePhoto(visit_device_id=item_id, uploaded_by=user.id, object_key=key,
                    sha256=hashlib.sha256(image).hexdigest(), size_bytes=len(image), width=width, height=height))
        save(session)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return detail(session, visit)


def complete(session, visit):
    # The gate may be disabled during rollback; a persisted coverage must still
    # prevent the legacy validator from accepting an incomplete V2 visit.
    if inspect(session.connection()).has_table('sampling_coverages') and session.scalar(select(m.SamplingCoverage.id).where(
            m.SamplingCoverage.hotel_visit_id == visit.id)):
        raise HTTPException(409, 'Cakupan V2 tersimpan. Submit menunggu integrasi pengukuran per titik dan review PIC.')
    report = hs.HotelReport.model_validate(visit.report)
    if not report.summary or not report.summary.strip() or not report.work_status or not report.backbone_mode:
        raise HTTPException(409, 'Isi ringkasan, hasil pekerjaan dan jenis koneksi backbone')
    if report.work_status == 'pending' and not report.pending_reason:
        raise HTTPException(409, 'Pekerjaan pending wajib memiliki alasan')
    if not report.pic_name or not report.pic_exception_reason:
        raise HTTPException(409, 'Isi nama PIC dan alasan pengecualian tanda tangan PIC')
    modes = ('fo_only', 'both', 'failover', 'bonding')
    if report.backbone_mode in modes and report.fo is None:
        raise HTTPException(409, 'Lengkapi hasil pemeriksaan backbone FO')
    if report.backbone_mode != 'fo_only' and report.wireless is None:
        raise HTTPException(409, 'Lengkapi hasil pemeriksaan backbone wireless')
    for branch in (report.fo, report.wireless):
        if branch and (branch.download_mbps is None or branch.upload_mbps is None) and report.form_version == 2 and not (branch.notes or '').strip():
            raise HTTPException(409, 'Isi download/upload backbone atau keterangan pengujian tidak tersedia')
        if branch and branch.speedtest_mbps is None and report.form_version == 1 and not (branch.notes or '').strip():
            raise HTTPException(409, 'Isi hasil speedtest backbone atau alasan pengujian tidak tersedia')
    if report.signal_test is None or report.blank_spot is None or report.hotspot is None:
        raise HTTPException(409, 'Lengkapi signal test, blank spot dan hotspot jaringan lokal')
    if report.form_version == 2:
        for key, label in [('router_connector', 'koneksi LAN router'), ('switch_connector', 'LAN ke switch'),
                           ('signal_test', 'signal test'), ('blank_spot', 'blank spot'), ('hotspot', 'hotspot')]:
            if getattr(report, key) is None or not (getattr(report, key + '_notes') or '').strip():
                raise HTTPException(409, 'Isi hasil dan keterangan ' + label)
    items = session.scalars(select(m.HotelVisitDevice).where(m.HotelVisitDevice.visit_id == visit.id)).all()
    if not any(item.device_snapshot['device_type'] == 'ap' for item in items):
        raise HTTPException(409, 'Pilih setidaknya satu AP sampling yang benar-benar diperiksa')
    for item in items:
        name = item.device_snapshot['name']
        photos = session.scalars(select(m.DevicePhoto).where(m.DevicePhoto.visit_device_id == item.id)).all()
        if not photos or any(not (storage()/photo.object_key).is_file() for photo in photos):
            raise HTTPException(409, f'Foto wajib belum lengkap atau belum tersedia: {name}')
        result = item.result
        if result.get('outcome') not in ('pass', 'fail', 'not_applicable'):
            raise HTTPException(409, f'Isi hasil pemeriksaan: {name}')
        if result['outcome'] != 'pass' and not (result.get('notes') or '').strip():
            raise HTTPException(409, f'Isi catatan tindakan atau alasan: {name}')
        kind = item.device_snapshot['device_type']
        if kind in ('router', 'switch') and not getattr(report, kind+'_connector'):
            raise HTTPException(409, f'Isi pemeriksaan konektor LAN {kind}')
        if kind == 'ap':
            bands = [result.get('band_24', {}), result.get('band_5', {})]
            if not any(b.get('status') == 'measured' for b in bands):
                if not (report.work_status == 'pending' and result['outcome'] == 'fail' and all(b.get('reason') for b in bands)):
                    raise HTTPException(409, f'Isi pengukuran AP atau catat kegagalan dengan alasan dan pekerjaan pending: {name}')
            for band in bands:
                if band.get('status') == 'measured':
                    if any(band.get(k) is None for k in ('signal_dbm', 'channel', 'bandwidth_mbps')) and not band.get('reason'):
                        raise HTTPException(409, f'Lengkapi sinyal, channel, bandwidth atau alasan hasil tidak tersedia: {name}')
                elif not band.get('reason'):
                    raise HTTPException(409, f'Jelaskan band AP yang tidak diuji/tidak tersedia: {name}')


@router.post('/{identifier}/check-out')
def check_out(identifier: UUID, data: s.CheckIn, user=Depends(current), session: Session = Depends(db)):
    evidence = {**jsonable_encoder(data.model_dump(exclude={'expected_version'})), 'server_time': datetime.now(timezone.utc).isoformat()}
    visit = advance(session, identifier, user, data.expected_version, statuses=('in_progress',), status='submitted', checkout=evidence)
    complete(session, visit)
    event(session, visit, user, 'submitted')
    save(session)
    return detail(session, visit)


@router.post('/{identifier}/resubmit')
def resubmit(identifier: UUID, data: s.VisitVersion, user=Depends(current), session: Session = Depends(db)):
    visit = advance(session, identifier, user, data.expected_version, statuses=('revision_requested',), status='submitted')
    complete(session, visit)
    event(session, visit, user, 'resubmitted')
    save(session)
    return detail(session, visit)


@router.post('/{identifier}/review')
def review(identifier: UUID, data: s.VisitReview, user=Depends(supervisor), session: Session = Depends(db)):
    visit = advance(session, identifier, user, data.expected_version, statuses=('submitted',), owner=False, status=data.decision)
    if data.decision == 'approved':
        complete(session, visit)
    event(session, visit, user, data.decision, data.reason)
    save(session)
    return detail(session, visit)


@router.get('/{identifier}/history')
def history(identifier: UUID, offset: int = 0, limit: int = 50, user=Depends(current), session: Session = Depends(db)):
    visible(session, identifier, user)
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Pagination tidak valid')
    events = session.scalars(select(m.HotelVisitEvent).where(m.HotelVisitEvent.visit_id == identifier)
                .order_by(m.HotelVisitEvent.version).offset(offset).limit(limit)).all()
    return [{'id': e.id, 'actor_id': e.actor_id, 'version': e.version, 'action': e.action,
             'reason': e.reason, 'created_at': e.created_at, 'snapshot': e.snapshot} for e in events]



def speedtest_info(run):
    # No transfer capability is persisted or returned through report history.
    expired = run.status == 'running' and run.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc)
    return {'id':run.id,'band':run.band,'status':'failed' if expired else run.status,'created_at':run.created_at,
            'finished_at':run.finished_at,'context':run.context,'metrics':run.metrics,
            'error':'Sesi pengukuran kedaluwarsa' if expired else run.error}
