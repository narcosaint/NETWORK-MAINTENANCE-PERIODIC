import io
from pathlib import Path
import pytest
from PIL import Image
from test_modules import client, isolated_lifespan, login


@pytest.fixture(autouse=True)
def private_photos(monkeypatch, tmp_path):
    monkeypatch.setenv('PHOTO_STORAGE_ROOT', str(tmp_path / 'photos'))
    return tmp_path / 'photos'


def image_bytes():
    stream = io.BytesIO()
    Image.new('RGB', (80, 60), (40, 100, 60)).save(stream, 'PNG')
    return stream.getvalue()


def setup_hotel(api):
    admin = login(api)
    users = []
    for username in ('hotel_tech', 'hotel_other'):
        users.append(api.post('/users', headers=admin, json={
            'username': username, 'name': username, 'role': 'technician', 'password': 'strong-secret-456'}).json())
    hotel = api.post('/hotels', headers=admin, json={'name': 'Hotel-wide test'}).json()
    devices = []
    for kind, name in [('router', 'Router'), ('switch', 'Switch'), ('ap', 'AP 2601'), ('ap', 'AP corridor')]:
        devices.append(api.post('/devices', headers=admin, json={
            'hotel_id': hotel['id'], 'device_type': kind, 'name': name}).json())
    payload = {'hotel_id': hotel['id'], 'technician_id': users[0]['id'], 'planned_date': '2026-11-12'}
    response = api.post('/hotel-visits', headers=admin, json=payload)
    assert response.status_code == 201
    return admin, login(api, 'hotel_tech', 'strong-secret-456'), login(api, 'hotel_other', 'strong-secret-456'), response.json(), devices, payload


def mutate(api, path, auth, suffix, body=None, method='post', **kwargs):
    version = api.get(path, headers=auth).json()['version']
    return getattr(api, method)(path + suffix, headers=auth,
            json={'expected_version': version, **(body or {})}, **kwargs)


def populate(api, path, assigned, devices, photos=True, work='completed'):
    assert mutate(api, path, assigned, '/check-in', {'device_time': '2026-11-12T03:00:00Z',
           'gps_exception_reason': 'GPS unavailable in isolated test'}).status_code == 200
    assert mutate(api, path, assigned, '/samples', {'device_id': devices[2]['id'], 'floor': '26', 'point': 'Kamar 2601'}).status_code == 201
    detail = api.get(path, headers=assigned).json()
    assert len(detail['devices']) == 3  # unsampled corridor AP does not acquire a result
    for item in detail['devices']:
        result = {'outcome': 'pass', 'notes': 'Checked'}
        if item['device']['device_type'] == 'ap':
            result.update(band_24={'status': 'measured', 'signal_dbm': -65, 'channel': 6, 'bandwidth_mbps': 30},
                          band_5={'status': 'unavailable', 'reason': 'AP only supports 2.4 GHz'})
        assert mutate(api, path, assigned, '/devices/' + item['id'] + '/result', {'result': result}, method='put').status_code == 200
        if photos:
            version = api.get(path, headers=assigned).json()['version']
            response = api.post(path + '/devices/' + item['id'] + f'/photos?expected_version={version}',
                        headers={**assigned, 'Content-Type': 'image/png'}, content=image_bytes())
            assert response.status_code == 201
    report = {'form_version': 2, 'backbone_mode': 'fo_only', 'fo': {'download_mbps': 45, 'upload_mbps': 40},
              'router_connector': 'normal', 'switch_connector': 'normal', 'signal_test': 'good',
              'blank_spot': False, 'hotspot': True, 'router_connector_notes': 'Router normal', 'switch_connector_notes': 'Switch normal', 'signal_test_notes': 'Signal good', 'blank_spot_notes': 'No blank spot in sample', 'hotspot_notes': 'Hotspot present', 'summary': 'Hotel inspection completed', 'work_status': work,
              'pic_name': 'Test PIC', 'pic_exception_reason': 'Digital signatures not available at this stage'}
    if work == 'pending':
        report['pending_reason'] = 'Follow-up replacement required'
    assert mutate(api, path, assigned, '/report', {'report': report}, method='put').status_code == 200


def checkout(api, path, assigned):
    return mutate(api, path, assigned, '/check-out', {'device_time': '2026-11-12T04:00:00Z',
                  'gps_exception_reason': 'GPS permission denied'})


def test_hotel_sampling_photo_and_revision_flow(client, private_photos):
    api, _ = client
    admin, assigned, other, visit, devices, _ = setup_hotel(api)
    path = '/hotel-visits/' + visit['id']
    assert len(visit['devices']) == 2
    assert api.get(path, headers=other).status_code == 404
    assert api.get('/hotel-visits', headers=other).json() == []
    populate(api, path, assigned, devices)
    detail = api.get(path, headers=assigned).json()
    photo = detail['devices'][0]['photos'][0]
    assert api.get(photo['url']).status_code == 401
    assert api.get(photo['url'], headers=other).status_code == 404
    response = api.get(photo['url'], headers=admin)
    assert response.status_code == 200 and response.headers['content-type'] == 'image/jpeg'
    assert response.headers['cache-control'] == 'no-store'
    assert Image.open(io.BytesIO(response.content)).size == (80, 60)
    assert checkout(api, path, assigned).json()['status'] == 'submitted'
    original = api.get(path + '/history', headers=admin).json()
    assert original[0]['snapshot']['devices'][0]['photos'][0]['sha256']
    assert mutate(api, path, admin, '/review', {'decision': 'revision_requested', 'reason': 'Clarify summary'}).json()['status'] == 'revision_requested'
    report = api.get(path, headers=assigned).json()['report'];report['summary'] = 'Updated explanation'
    assert mutate(api, path, assigned, '/report', {'report': report}, method='put').status_code == 200
    assert mutate(api, path, assigned, '/resubmit').json()['status'] == 'submitted'
    approved = mutate(api, path, admin, '/review', {'decision': 'approved', 'reason': 'Reviewed photo and findings'})
    assert approved.json()['maintenance_completed'] is True
    assert len(api.get(path + '/history', headers=assigned).json()) == 4
    assert api.get(path + '/history', headers=admin).json()[0] == original[0]
    assert mutate(api, path, assigned, '/report', {'report': report}, method='put').status_code == 409
    version = api.get(path, headers=assigned).json()['version']
    assert api.post(path + '/devices/' + detail['devices'][0]['id'] + f'/photos?expected_version={version}',
                    headers={**assigned, 'Content-Type': 'image/png'}, content=image_bytes()).status_code == 409
    assert len(list(private_photos.glob('*.jpg'))) == 3


def test_missing_photos_block_submission_without_losing_draft(client):
    api, _ = client
    _, assigned, _, visit, devices, _ = setup_hotel(api)
    path = '/hotel-visits/' + visit['id']
    populate(api, path, assigned, devices, photos=False)
    before = api.get(path, headers=assigned).json()
    response = checkout(api, path, assigned)
    assert response.status_code == 409 and 'Foto wajib' in response.json()['detail']
    after = api.get(path, headers=assigned).json()
    assert after['version'] == before['version'] and after['status'] == 'in_progress'
    assert after['checkout'] is None


def test_pending_work_approval_is_not_completion(client):
    api, _ = client
    admin, assigned, _, visit, devices, _ = setup_hotel(api)
    path = '/hotel-visits/' + visit['id']
    populate(api, path, assigned, devices, work='pending')
    assert checkout(api, path, assigned).status_code == 200
    approved = mutate(api, path, admin, '/review', {'decision': 'approved', 'reason': 'Pending action acknowledged'})
    assert approved.status_code == 200 and approved.json()['status'] == 'approved'
    assert approved.json()['maintenance_completed'] is False


def test_upload_validation_ownership_conflicts_and_sample_scope(client, private_photos):
    api, _ = client
    admin, assigned, other, visit, devices, _ = setup_hotel(api)
    path = '/hotel-visits/' + visit['id']
    assert mutate(api, path, assigned, '/check-in', {'device_time': '2026-11-12T03:00:00Z', 'gps_exception_reason': 'Denied'}).status_code == 200
    item = visit['devices'][0]
    upload = path + '/devices/' + item['id'] + '/photos?expected_version=2'
    assert api.post(upload, headers={**other, 'Content-Type': 'image/png'}, content=image_bytes()).status_code == 404
    assert api.post(upload, headers={**admin, 'Content-Type': 'image/png'}, content=image_bytes()).status_code == 403
    assert api.post(upload, headers={**assigned, 'Content-Type': 'image/svg+xml'}, content=b'<svg/>').status_code == 415
    assert api.post(upload, headers={**assigned, 'Content-Type': 'image/png'}, content=b'not a real photo').status_code == 422
    assert api.post(upload, headers={**assigned, 'Content-Type': 'image/jpeg'}, content=image_bytes()).status_code == 422
    assert api.post(upload, headers={**assigned, 'Content-Type': 'image/png'}, content=b'x'*(10*1024*1024+1)).status_code == 413
    assert api.post(upload.replace('version=2','version=1'), headers={**assigned, 'Content-Type': 'image/png'}, content=image_bytes()).status_code == 409
    assert not private_photos.exists() or not list(private_photos.iterdir())
    other_hotel = api.post('/hotels', headers=admin, json={'name': 'Other hotel'}).json()
    other_ap = api.post('/devices', headers=admin, json={'hotel_id': other_hotel['id'], 'name': 'Other AP', 'device_type': 'ap'}).json()
    assert mutate(api, path, assigned, '/samples', {'device_id': other_ap['id'], 'floor': '1', 'point': 'Room'}).status_code == 422
    assert mutate(api, path, assigned, '/samples', {'device_id': devices[0]['id'], 'floor': '1', 'point': 'Room'}).status_code == 422
    assert api.get(path, headers=assigned).json()['version'] == 2
    assert mutate(api, path, assigned, '/samples', {'device_id': devices[2]['id'], 'floor': '26', 'point': '2601'}).status_code == 201
    before = api.get(path, headers=assigned).json()['version']
    assert mutate(api, path, assigned, '/samples', {'device_id': devices[2]['id'], 'floor': '26', 'point': '2601'}).status_code == 409
    assert api.get(path, headers=assigned).json()['version'] == before


def test_photo_database_failure_removes_file_and_rolls_back_version(client, private_photos):
    from sqlalchemy import event
    from sqlalchemy.exc import IntegrityError
    from app.models import DevicePhoto
    api, _ = client
    _, assigned, _, visit, _, _ = setup_hotel(api)
    path = '/hotel-visits/' + visit['id']
    assert mutate(api, path, assigned, '/check-in', {'device_time':'2026-11-12T03:00:00Z','gps_exception_reason':'Denied'}).status_code == 200
    def fail(mapper, connection, target):
        raise IntegrityError('simulated database failure', {}, Exception('test'))
    event.listen(DevicePhoto, 'before_insert', fail)
    try:
        response = api.post(path + '/devices/' + visit['devices'][0]['id'] + '/photos?expected_version=2',
            headers={**assigned, 'Content-Type':'image/png'}, content=image_bytes())
        assert response.status_code == 409
    finally:
        event.remove(DevicePhoto, 'before_insert', fail)
    detail = api.get(path, headers=assigned).json()
    assert detail['version'] == 2 and not detail['devices'][0]['photos']
    assert not list(private_photos.glob('*.jpg'))



def test_failed_ap_can_be_reported_pending_without_invented_measurements(client):
    api, _ = client
    _, assigned, _, visit, devices, _ = setup_hotel(api)
    path = '/hotel-visits/' + visit['id']
    populate(api, path, assigned, devices, work='pending')
    sample = next(i for i in api.get(path, headers=assigned).json()['devices'] if i['device']['device_type']=='ap')
    failed = {'outcome':'fail','notes':'AP tidak menyala, menunggu penggantian',
              'band_24':{'status':'unavailable','reason':'AP tidak menyala'},
              'band_5':{'status':'unavailable','reason':'AP tidak menyala'}}
    assert mutate(api, path, assigned, '/devices/'+sample['id']+'/result', {'result':failed}, method='put').status_code == 200
    report = api.get(path, headers=assigned).json()['report']
    report['work_status']='completed';report['pending_reason']=None
    assert mutate(api, path, assigned, '/report', {'report':report}, method='put').status_code == 200
    assert checkout(api, path, assigned).status_code == 409
    report['work_status']='pending';report['pending_reason']='Menunggu penggantian AP'
    assert mutate(api, path, assigned, '/report', {'report':report}, method='put').status_code == 200
    submitted = checkout(api, path, assigned)
    assert submitted.status_code == 200
    result = next(i for i in submitted.json()['devices'] if i['id']==sample['id'])['result']
    assert result['band_24']['signal_dbm'] is None
    assert result['band_24']['bandwidth_mbps'] is None
