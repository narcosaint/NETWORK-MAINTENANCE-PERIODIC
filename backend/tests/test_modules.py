from datetime import datetime, timedelta, timezone
import pytest
from http_client import ASGIClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.api import db
from app.models import Base, User, LoginSession
from app.security import hash_password, token_hash


@pytest.fixture
def client():
    from app.api import _login_attempts
    _login_attempts.clear()
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(conn, record):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(username='admin', name='Admin', role='supervisor', active=True,
                         password_hash=hash_password('strong-secret-123')))
        session.commit()
    def override():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[db] = override
    # No application lifespan: tests never build a production database engine.
    yield ASGIClient(app), engine
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture(autouse=True)
def isolated_lifespan(monkeypatch):
    # Existing health tests patch the same factory. Keep this fixture local to this module.
    monkeypatch.setattr('app.main.build_engine', lambda: create_engine('sqlite://'))


def login(api, username='admin', password='strong-secret-123'):
    response = api.post('/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def test_crud_roles_and_monthly_schedule(client):
    api, engine = client
    assert api.get('/hotels').status_code == 401
    auth = login(api)
    hotel = api.post('/hotels', headers=auth, json={'name': 'Hotel A'}).json()
    device_data = {'hotel_id': hotel['id'], 'name': 'Router', 'device_type': 'router'}
    device = api.post('/devices', headers=auth, json=device_data).json()
    tech_data = {'username': 'tech', 'name': 'Teknisi', 'role': 'technician', 'password': 'strong-secret-456'}
    response = api.post('/users', headers=auth, json=tech_data)
    assert response.status_code == 201
    tech = response.json()
    assert 'password' not in tech and 'password_hash' not in tech
    tech_auth = login(api, 'tech', tech_data['password'])
    assert api.post('/hotels', headers=tech_auth, json={'name': 'Forbidden'}).status_code == 403
    assert api.get('/users', headers=tech_auth).status_code == 403
    schedule_data = {'device_id': device['id'], 'technician_id': tech['id'], 'month': '2026-11-01'}
    response = api.post('/schedules', headers=auth, json=schedule_data)
    assert response.status_code == 201
    schedule = response.json()
    assert api.post('/schedules', headers=auth, json=schedule_data).status_code == 409
    assert api.post('/schedules', headers=auth, json={**schedule_data, 'month': '2026-12-02'}).status_code == 422
    assert api.get('/schedules', headers=tech_auth).json()[0]['id'] == schedule['id']
    assert api.patch('/schedules/' + schedule['id'] + '/progress', headers=tech_auth, json={'status': 'completed'}).status_code == 200
    assert api.delete('/hotels/' + hotel['id'], headers=auth).status_code == 409
    for path, data in [('hotels/' + hotel['id'], {'name': 'Updated'}), ('devices/' + device['id'], device_data), ('schedules/' + schedule['id'], schedule_data)]:
        assert api.put('/' + path, headers=auth, json=data).status_code == 200
        assert api.get('/' + path, headers=auth).status_code == 200
    for path in ['schedules/' + schedule['id'], 'devices/' + device['id'], 'hotels/' + hotel['id'], 'users/' + tech['id']]:
        assert api.delete('/' + path, headers=auth).status_code == 204
        assert api.get('/' + path, headers=auth).status_code == 404


def test_session_security_and_validation(client):
    api, engine = client
    assert api.post('/auth/login', json={'username': 'admin', 'password': 'wrong'}).status_code == 401
    assert api.post('/auth/login', json={'username': 'absent', 'password': 'wrong'}).status_code == 401
    auth = login(api)
    assert api.post('/hotels', headers=auth, json={'name': '  '}).status_code == 422
    assert api.post('/users', headers=auth, json={'username': 'weak', 'name': 'Weak', 'role': 'supervisor', 'password': 'short'}).status_code == 422
    assert api.get('/hotels?limit=101', headers=auth).status_code == 422
    with Session(engine) as session:
        stored = session.scalar(select(LoginSession))
        assert stored.token_hash == token_hash(auth['Authorization'].split()[1])
        stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    assert api.get('/auth/me', headers=auth).status_code == 401
    auth = login(api)
    assert api.post('/auth/logout', headers=auth).status_code == 204
    assert api.get('/auth/me', headers=auth).status_code == 401


def test_assignment_isolation_and_revocation(client):
    api, engine = client
    auth = login(api)
    users = []
    for username in ['tech1', 'tech2']:
        data = {'username': username, 'name': username, 'role': 'technician', 'password': 'strong-secret-456'}
        users.append(api.post('/users', headers=auth, json=data).json())
    hotel = api.post('/hotels', headers=auth, json={'name': 'A'}).json()
    device = api.post('/devices', headers=auth, json={'hotel_id': hotel['id'], 'name': 'AP', 'device_type': 'ap'}).json()
    data = {'device_id': device['id'], 'technician_id': users[0]['id'], 'month': '2026-11-01'}
    schedule = api.post('/schedules', headers=auth, json=data).json()
    other = login(api, 'tech2', 'strong-secret-456')
    assert api.get('/schedules', headers=other).json() == []
    assert api.get('/schedules/' + schedule['id'], headers=other).status_code == 404
    assert api.patch('/schedules/' + schedule['id'] + '/progress', headers=other, json={'status': 'completed'}).status_code == 404
    updated = {k: v for k, v in users[1].items() if k != 'id'}
    updated['active'] = False
    assert api.put('/users/' + users[1]['id'], headers=auth, json=updated).status_code == 200
    assert api.get('/auth/me', headers=other).status_code == 401
    assert api.post('/schedules', headers=auth, json={**data, 'technician_id': users[1]['id'], 'month': '2026-12-01'}).status_code == 422


def test_login_throttle(client):
    api, _ = client
    for _ in range(20):
        assert api.post('/auth/login', json={'username': 'absent', 'password': 'wrong'}).status_code == 401
    assert api.post('/auth/login', json={'username': 'absent', 'password': 'wrong'}).status_code == 429


def setup_visit(api):
    auth = login(api)
    users = []
    for username in ('assigned', 'other'):
        users.append(api.post('/users', headers=auth, json={
            'username': username, 'name': username, 'role': 'technician',
            'password': 'strong-secret-456'}).json())
    hotel = api.post('/hotels', headers=auth, json={'name': 'Visit test hotel'}).json()
    device = api.post('/devices', headers=auth, json={
        'hotel_id': hotel['id'], 'name': 'AP', 'device_type': 'ap'}).json()
    schedule_data = {'device_id': device['id'], 'technician_id': users[0]['id'], 'month': '2026-11-01'}
    schedule = api.post('/schedules', headers=auth, json=schedule_data).json()
    response = api.post('/visits', headers=auth, json={'schedule_id': schedule['id']})
    assert response.status_code == 201
    return auth, login(api, 'assigned', 'strong-secret-456'), login(api, 'other', 'strong-secret-456'), schedule, schedule_data, response.json()


def test_visit_check_in_ownership_conflicts_and_schedule_guard(client):
    api, engine = client
    admin, assigned, other, schedule, schedule_data, visit = setup_visit(api)
    path = '/visits/' + visit['id']
    payload = {'expected_version': 1, 'device_time': '2026-11-11T10:00:00+07:00',
               'latitude': -6.2, 'longitude': 106.8, 'accuracy_m': 12.5}
    assert api.post('/visits', headers=assigned, json={'schedule_id': schedule['id']}).status_code == 403
    assert api.post('/visits', headers=admin, json={'schedule_id': schedule['id']}).status_code == 409
    assert api.get('/visits', headers=other).json() == []
    assert api.get(path, headers=other).status_code == 404
    assert api.post(path + '/check-in', headers=other, json=payload).status_code == 404
    assert api.post(path + '/check-in', headers=admin, json=payload).status_code == 403
    assert api.post(path + '/check-in', json=payload).status_code == 401
    assert api.post(path + '/check-in', headers=assigned, json={**payload, 'expected_version': 2}).status_code == 409
    before = datetime.now(timezone.utc)
    response = api.post(path + '/check-in', headers=assigned, json=payload)
    assert response.status_code == 200
    recorded = response.json()
    assert recorded['status'] == 'in_progress' and recorded['version'] == 2
    assert datetime.fromisoformat(recorded['checked_in_at']).replace(tzinfo=timezone.utc) >= before
    assert recorded['latitude'] == -6.2
    assert api.post(path + '/check-in', headers=assigned, json=payload).status_code == 409
    assert api.post(path + '/check-in', headers=assigned, json={**payload, 'expected_version': 2}).status_code == 409
    assert api.get(path, headers=assigned).json() == recorded
    assert api.put('/schedules/' + schedule['id'], headers=admin, json=schedule_data).status_code == 409
    assert api.patch('/schedules/' + schedule['id'] + '/progress', headers=assigned, json={'status': 'completed'}).status_code == 409
    assert api.delete('/schedules/' + schedule['id'], headers=admin).status_code == 409
    assert api.get('/visits?limit=101', headers=admin).status_code == 422


def test_visit_gps_validation_and_explicit_exception(client):
    api, _ = client
    admin, assigned, _, schedule, _, visit = setup_visit(api)
    path = '/visits/' + visit['id'] + '/check-in'
    base = {'expected_version': 1, 'device_time': '2026-11-11T03:00:00Z'}
    for changes in ({}, {'latitude': 0}, {'gps_exception_reason': '  '},
                    {'device_time': '2026-11-11T03:00:00', 'gps_exception_reason': 'Denied'},
                    {'latitude': 91, 'longitude': 0, 'accuracy_m': 1},
                    {'latitude': 0, 'longitude': 0, 'accuracy_m': -1},
                    {'latitude': 0, 'longitude': 0, 'accuracy_m': 1, 'gps_exception_reason': 'Denied'}):
        assert api.post(path, headers=assigned, json={**base, **changes}).status_code == 422
    response = api.post(path, headers=assigned, json={**base, 'gps_exception_reason': ' Izin lokasi ditolak '})
    assert response.status_code == 200
    assert response.json()['gps_exception_reason'] == 'Izin lokasi ditolak'
    assert response.json()['latitude'] is None


def test_checklist_submission_and_immutable_evidence(client):
    api, _ = client
    admin, assigned, other, schedule, _, visit = setup_visit(api)
    path = '/visits/' + visit['id']
    template_data = {'name': 'AP revision 1', 'device_type': 'ap', 'items': [
        {'label': 'Inspect cable'}, {'label': 'Inspect power'}, {'label': 'Optional notes', 'required': False}]}
    assert api.post('/checklist-templates', headers=assigned, json=template_data).status_code == 403
    template = api.post('/checklist-templates', headers=admin, json=template_data).json()
    assert len(api.get('/checklist-templates', headers=assigned).json()) == 1
    assert api.put('/checklist-templates/' + template['id'], headers=admin, json=template_data).status_code == 405
    assert api.delete('/checklist-templates/' + template['id'], headers=admin).status_code == 405
    assert api.put(path + '/template', headers=assigned, json={'expected_version': 1, 'template_id': template['id']}).status_code == 403
    bound = api.put(path + '/template', headers=admin, json={'expected_version': 1, 'template_id': template['id']})
    assert bound.status_code == 200 and bound.json()['version'] == 2
    assert api.put(path + '/template', headers=admin, json={'expected_version': 2, 'template_id': template['id']}).status_code == 409
    gps = {'device_time': '2026-11-12T10:00:00+07:00', 'gps_exception_reason': 'Location permission denied'}
    answer = {'item_id': template['items'][0]['id'], 'answer': 'pass'}
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 2, 'answers': [answer]}).status_code == 409
    assert api.post(path + '/check-in', headers=assigned, json={'expected_version': 2, **gps}).status_code == 200
    checkout = {**gps, 'expected_version': 3, 'pic_exception_reason': 'PIC unavailable; needs supervisor review'}
    assert api.post(path + '/check-out', headers=assigned, json=checkout).status_code == 409
    assert api.get(path, headers=assigned).json()['version'] == 3  # failed mutation rolls back
    assert api.get(path + '/checklist', headers=other).status_code == 404
    assert api.put(path + '/checklist', headers=other, json={'expected_version': 3, 'answers': [answer]}).status_code == 404
    assert api.put(path + '/checklist', headers=admin, json={'expected_version': 3, 'answers': [answer]}).status_code == 403
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 3, 'answers': [answer, answer]}).status_code == 422
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 3, 'answers': [{**answer, 'answer': 'fail'}]}).status_code == 422
    from uuid import uuid4
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 3, 'answers': [{**answer, 'item_id': str(uuid4())}]}).status_code == 422
    assert api.get(path, headers=assigned).json()['version'] == 3
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 3, 'answers': [answer]}).json()['version'] == 4
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 3, 'answers': [answer]}).status_code == 409
    assert api.post(path + '/check-out', headers=assigned, json={**checkout, 'expected_version': 4}).status_code == 409
    second = {'item_id': template['items'][1]['id'], 'answer': 'fail', 'notes': 'Power adapter replaced; requires follow-up'}
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 4, 'answers': [second]}).json()['version'] == 5
    saved = api.get(path + '/checklist', headers=assigned).json()
    assert len(saved['answers']) == 2 and saved['template']['id'] == template['id']
    assert api.post(path + '/check-out', headers=other, json={**checkout, 'expected_version': 5}).status_code == 404
    assert api.post(path + '/check-out', headers=admin, json={**checkout, 'expected_version': 5}).status_code == 403
    assert api.post(path + '/check-out', headers=assigned, json={**checkout, 'expected_version': 5, 'pic_exception_reason': ' '}).status_code == 422
    submitted = api.post(path + '/check-out', headers=assigned, json={**checkout, 'expected_version': 5})
    assert submitted.status_code == 200
    assert submitted.json()['status'] == 'submitted' and submitted.json()['version'] == 6
    assert submitted.json()['checked_out_at'] and submitted.json()['checkout_gps_exception_reason']
    assert api.get('/schedules/' + schedule['id'], headers=admin).json()['status'] == 'pending'
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 6, 'answers': [answer]}).status_code == 409
    assert api.post(path + '/check-out', headers=assigned, json={**checkout, 'expected_version': 6}).status_code == 409
    assert api.get(path + '/checklist', headers=assigned).json()['answers'] == saved['answers']


def test_template_device_validation_and_missing_template(client):
    api, _ = client
    admin, assigned, _, schedule, _, visit = setup_visit(api)
    path = '/visits/' + visit['id']
    template = api.post('/checklist-templates', headers=admin, json={
        'name': 'Router', 'device_type': 'router', 'items': [{'label': 'Power'}]}).json()
    assert api.put(path + '/template', headers=admin, json={'expected_version': 1, 'template_id': template['id']}).status_code == 422
    # New visit rejects mismatched device types before attempting duplicate insert.
    assert api.post('/visits', headers=admin, json={'schedule_id': schedule['id'], 'template_id': template['id']}).status_code == 422
    gps = {'device_time': '2026-11-12T03:00:00Z', 'latitude': 0, 'longitude': 0, 'accuracy_m': 1}
    assert api.post(path + '/check-in', headers=assigned, json={'expected_version': 1, **gps}).status_code == 200
    assert api.post(path + '/check-out', headers=assigned, json={'expected_version': 2, **gps, 'pic_exception_reason': 'PIC absent'}).status_code == 409
    assert api.get(path, headers=assigned).json()['status'] == 'in_progress'


def setup_submitted_visit(api):
    admin, assigned, other, schedule, schedule_data, visit = setup_visit(api)
    path = '/visits/' + visit['id']
    template = api.post('/checklist-templates', headers=admin, json={
        'name': 'AP review test', 'device_type': 'ap', 'items': [{'label': 'Inspect cable'}]}).json()
    assert api.put(path + '/template', headers=admin, json={
        'expected_version': 1, 'template_id': template['id']}).status_code == 200
    gps = {'device_time': '2026-11-12T03:00:00Z', 'gps_exception_reason': 'GPS permission denied'}
    assert api.post(path + '/check-in', headers=assigned, json={'expected_version': 2, **gps}).status_code == 200
    answer = {'item_id': template['items'][0]['id'], 'answer': 'fail', 'notes': 'Cable needs replacement'}
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 3, 'answers': [answer]}).status_code == 200
    submitted = api.post(path + '/check-out', headers=assigned, json={
        'expected_version': 4, **gps, 'pic_exception_reason': 'PIC unavailable'} )
    assert submitted.status_code == 200
    return admin, assigned, other, schedule, schedule_data, submitted.json(), answer


def test_review_revision_resubmission_and_approval(client):
    api, _ = client
    admin, assigned, other, schedule, schedule_data, visit, answer = setup_submitted_visit(api)
    path = '/visits/' + visit['id']
    original_checkout = visit['checked_out_at']
    history = api.get(path + '/history', headers=assigned).json()
    assert len(history) == 1 and history[0]['action'] == 'submitted'
    assert history[0]['snapshot']['answers'][0]['answer'] == 'fail'
    review = {'expected_version': 5, 'decision': 'revision_requested', 'reason': 'Replace cable and document action'}
    assert api.post(path + '/review', headers=admin, json=review).json()['status'] == 'revision_requested'
    assert api.get('/schedules/' + schedule['id'], headers=admin).json()['status'] == 'pending'
    revised = {**answer, 'answer': 'pass', 'notes': 'Cable replaced and tested'}
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 6, 'answers': [revised]}).json()['version'] == 7
    assert api.post(path + '/review', headers=admin, json={**review, 'expected_version': 7, 'decision': 'approved'}).status_code == 409
    assert api.post(path + '/resubmit', headers=assigned, json={'expected_version': 6}).status_code == 409
    submitted = api.post(path + '/resubmit', headers=assigned, json={'expected_version': 7})
    assert submitted.status_code == 200 and submitted.json()['version'] == 8
    assert submitted.json()['checked_out_at'] == original_checkout
    assert api.post(path + '/review', headers=admin, json={
        'expected_version': 8, 'decision': 'approved', 'reason': 'Cable fixed; GPS/PIC exceptions accepted'}).json()['version'] == 9
    assert api.get(path, headers=assigned).json()['status'] == 'approved'
    assert api.get('/schedules/' + schedule['id'], headers=admin).json()['status'] == 'completed'
    events = api.get(path + '/history', headers=admin).json()
    assert [e['action'] for e in events] == ['submitted', 'revision_requested', 'resubmitted', 'approved']
    assert [e['version'] for e in events] == [5, 6, 8, 9]
    assert events[0]['snapshot']['answers'][0]['answer'] == 'fail'
    assert events[1]['snapshot']['answers'][0]['answer'] == 'fail'
    assert events[2]['snapshot']['answers'][0]['answer'] == 'pass'
    assert events[3]['snapshot']['schedule']['status'] == 'completed'
    assert events[3]['reason'] == 'Cable fixed; GPS/PIC exceptions accepted'
    # Approval locks evidence and cannot be undone through the old schedule API.
    assert api.put(path + '/checklist', headers=assigned, json={'expected_version': 9, 'answers': [answer]}).status_code == 409
    assert api.post(path + '/resubmit', headers=assigned, json={'expected_version': 9}).status_code == 409
    assert api.post(path + '/review', headers=admin, json={**review, 'expected_version': 9}).status_code == 409
    assert api.put('/schedules/' + schedule['id'], headers=admin, json=schedule_data).status_code == 409
    assert api.patch('/schedules/' + schedule['id'] + '/progress', headers=admin, json={'status': 'pending'}).status_code == 409
    assert api.get(path + '/history', headers=admin).json() == events


def test_review_authorization_validation_and_stale_decisions(client):
    api, _ = client
    admin, assigned, other, schedule, _, visit, answer = setup_submitted_visit(api)
    path = '/visits/' + visit['id']
    review = {'expected_version': 5, 'decision': 'approved', 'reason': 'Reviewed failures and accepted GPS/PIC exceptions'}
    assert api.post(path + '/review', json=review).status_code == 401
    for tech in (assigned, other):
        assert api.post(path + '/review', headers=tech, json=review).status_code == 403
    assert api.get(path + '/history', headers=other).status_code == 404
    assert api.get(path + '/history').status_code == 401
    assert api.get(path + '/history?limit=101', headers=admin).status_code == 422
    assert api.post(path + '/resubmit', headers=other, json={'expected_version': 5}).status_code == 404
    assert api.post(path + '/resubmit', headers=admin, json={'expected_version': 5}).status_code == 403
    assert api.post(path + '/resubmit', headers=assigned, json={'expected_version': 5}).status_code == 409
    for invalid in ({'reason': ' '}, {'decision': 'completed'}, {'expected_version': True}):
        assert api.post(path + '/review', headers=admin, json={**review, **invalid}).status_code == 422
    assert api.post(path + '/review', headers=admin, json={**review, 'expected_version': 4}).status_code == 409
    assert api.get('/schedules/' + schedule['id'], headers=admin).json()['status'] == 'pending'
    assert len(api.get(path + '/history', headers=admin).json()) == 1
    assert api.post(path + '/review', headers=admin, json=review).json()['status'] == 'approved'
    assert api.post(path + '/review', headers=admin, json=review).status_code == 409
    events = api.get(path + '/history', headers=admin).json()
    assert len(events) == 2 and events[-1]['snapshot']['answers'][0]['answer'] == 'fail'


def test_failed_history_write_rolls_back_approval(client, monkeypatch):
    api, engine = client
    admin, assigned, _, schedule, _, visit, _ = setup_submitted_visit(api)
    path = '/visits/' + visit['id']
    from sqlalchemy.exc import IntegrityError
    from app.models import VisitEvent

    def reject_event(mapper, connection, target):
        raise IntegrityError('simulated history storage failure', {}, Exception('test'))

    event.listen(VisitEvent, 'before_insert', reject_event)
    try:
        assert api.post(path + '/review', headers=admin, json={
            'expected_version': 5, 'decision': 'approved', 'reason': 'Reviewed exceptions'}).status_code == 409
    finally:
        event.remove(VisitEvent, 'before_insert', reject_event)
    assert api.get(path, headers=assigned).json()['status'] == 'submitted'
    assert api.get(path, headers=assigned).json()['version'] == 5
    assert api.get('/schedules/' + schedule['id'], headers=admin).json()['status'] == 'pending'
    assert len(api.get(path + '/history', headers=admin).json()) == 1


def test_device_details_validation_and_roundtrip(client):
    api, _ = client
    admin = login(api)
    hotel = api.post('/hotels', headers=admin, json={'name': 'Inventory test hotel'}).json()
    base = {'hotel_id': hotel['id'], 'name': 'AP inventory', 'device_type': 'ap'}
    details = {'brand': '  Test brand  ', 'model': 'Model 1', 'location': 'Lobby rack',
               'ip_address': ' 2001:0db8:0:0:0:0:0:1 ', 'mac_address': 'AA-BB-CC-DD-EE-FF',
               'notes': 'Inspection point near reception'}
    response = api.post('/devices', headers=admin, json={**base, **details})
    assert response.status_code == 201
    device = response.json()
    assert device['brand'] == 'Test brand'
    assert device['ip_address'] == '2001:db8::1'
    assert device['mac_address'] == 'aa:bb:cc:dd:ee:ff'
    assert api.get('/devices/' + device['id'], headers=admin).json()['location'] == 'Lobby rack'
    assert api.get('/devices', headers=admin).json()[0]['model'] == 'Model 1'
    for bad in [{'ip_address': '999.1.1.1'}, {'ip_address': 'router.local'}, {'ip_address': 'fe80::1%eth0'},
                {'mac_address': 'GG:BB:CC:DD:EE:FF'}, {'mac_address': 'aa:bb:cc'}, {'brand': 'x'*101}]:
        assert api.put('/devices/' + device['id'], headers=admin, json={**base, **bad}).status_code == 422
    assert api.get('/devices/' + device['id'], headers=admin).json()['ip_address'] == '2001:db8::1'
    updated = api.put('/devices/' + device['id'], headers=admin, json={**base, 'ip_address': '192.168.10.2', 'brand': '  ', 'notes': ''})
    assert updated.status_code == 200
    assert updated.json()['ip_address'] == '192.168.10.2'
    assert updated.json()['brand'] is None and updated.json()['notes'] is None
    # Old requests that omit all detail fields still create valid devices.
    assert api.post('/devices', headers=admin, json=base).json()['location'] is None


def test_inventory_changes_do_not_rewrite_report_snapshots(client):
    api, _ = client
    admin, assigned, _, _, _, visit, _ = setup_submitted_visit(api)
    path = '/visits/' + visit['id'] + '/history'
    original = api.get(path, headers=admin).json()
    assert original[0]['snapshot']['device']['brand'] is None
    device = api.get('/devices', headers=admin).json()[0]
    payload = {k: v for k, v in device.items() if k not in ('id', 'created_at')}
    payload.update(brand='Changed brand', location='New location', ip_address='10.0.0.10')
    assert api.put('/devices/' + device['id'], headers=assigned, json=payload).status_code == 403
    assert api.put('/devices/' + device['id'], headers=admin, json=payload).status_code == 200
    assert api.get(path, headers=admin).json() == original
