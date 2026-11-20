from copy import deepcopy
from uuid import uuid4
from test_modules import client, isolated_lifespan
from test_hotel_visits import setup_hotel, mutate, checkout


def configured(api, monkeypatch):
    monkeypatch.setenv('SAMPLING_MASTER_ENABLED', 'true')
    admin, tech, other, visit, devices, _ = setup_hotel(api)
    base = f"/hotels/{visit['hotel_id']}/floors"
    floor = api.post(base, headers=admin, json={'name': 'Lantai 1', 'position': 0}).json()
    points = []
    for i in range(4):
        points.append(api.post(base + '/' + floor['id'] + '/sampling-points', headers=admin,
            json={'name': f'Lokasi {i}', 'position': i, 'device_id': devices[2]['id']}).json())
    payload = {'expected_version': visit['version'], 'floors': [
        {'id': floor['id'], 'version': floor['version'], 'points': [
            {'id': p['id'], 'version': p['version']} for p in points]}],
        'photo_policy': {'sampling_categories': ['ap', 'area'], 'infrastructure_categories': ['rack']}}
    return admin, tech, other, visit, floor, points, payload, base


def test_coverage_snapshot_replay_scope_and_legacy_submit_guard(client, monkeypatch):
    api, _ = client
    admin, tech, other, visit, floor, points, payload, base = configured(api, monkeypatch)
    path = '/hotel-visits/' + visit['id']
    route = path + '/sampling-coverage'
    assert api.get(route, headers=tech).json() is None
    assert api.post(route, headers=tech, json=payload).status_code == 403
    assert api.get(route, headers=other).status_code == 404
    response = api.post(route, headers=admin, json=payload)
    assert response.status_code == 201, response.text
    saved = response.json()
    assert saved['period'] == '2026-11-01'
    assert len(saved['floors'][0]['points']) == 4
    assert len({p['id'] for p in saved['floors'][0]['points']}) == 4
    assert saved['completion_available'] is True
    assert all(p['status'] == 'untested' for p in saved['floors'][0]['points'])
    assert api.post(route, headers=admin, json=payload).json() == saved
    changed = deepcopy(payload)
    changed['photo_policy']['sampling_categories'] = []
    assert api.post(route, headers=admin, json=changed).status_code == 409
    assert api.get(path, headers=tech).json()['version'] == visit['version'] + 1
    assert api.get(path, headers=tech).json()['report'] == visit['report']
    assert api.patch(base + '/' + floor['id'], headers=admin,
        json={'expected_version': 1, 'name': 'Nama berubah'}).status_code == 200
    assert api.patch(base + '/' + floor['id'] + '/sampling-points/' + points[0]['id'], headers=admin,
        json={'expected_version': 1, 'name': 'Titik berubah', 'archived': True}).status_code == 200
    assert api.get(route, headers=tech).json() == saved
    # Old POST is a replay of the originally reviewed request, even after master edits.
    assert api.post(route, headers=admin, json=payload).json() == saved
    assert mutate(api, path, tech, '/check-in', {
        'device_time': '2026-11-16T00:00:00Z', 'gps_exception_reason': 'Test indoor'}).status_code == 200
    before = api.get(path, headers=tech).json()
    response = checkout(api, path, tech)
    assert response.status_code == 409 and 'tanda tangan PIC' in response.json()['detail']['message']
    monkeypatch.setenv('SAMPLING_MASTER_ENABLED', 'false')
    assert checkout(api, path, tech).status_code == 409
    after = api.get(path, headers=tech).json()
    assert after['status'] == 'in_progress' and after['version'] == before['version']


def test_coverage_rejects_stale_incomplete_and_changed_master(client, monkeypatch):
    api, _ = client
    admin, tech, _, visit, floor, points, payload, base = configured(api, monkeypatch)
    route = '/hotel-visits/' + visit['id'] + '/sampling-coverage'
    for alter in ('missing_policy', 'missing_point', 'duplicate_point', 'wrong_floor', 'wrong_version'):
        data = deepcopy(payload)
        if alter == 'missing_policy': del data['photo_policy']
        if alter == 'missing_point': data['floors'][0]['points'].pop()
        if alter == 'duplicate_point': data['floors'][0]['points'].append(data['floors'][0]['points'][0])
        if alter == 'wrong_floor': data['floors'][0]['id'] = str(uuid4())
        if alter == 'wrong_version': data['expected_version'] = 100
        assert api.post(route, headers=admin, json=data).status_code in (409, 422)
    assert api.get(route, headers=tech).json() is None
    # Target > configured real locations cannot activate, even when versions are current.
    api.patch(base + '/' + floor['id'], headers=admin,
        json={'expected_version': 1, 'default_sampling_count': 5})
    payload['floors'][0]['version'] = 2
    response = api.post(route, headers=admin, json=payload)
    assert response.status_code == 409 and 'target 5' in response.json()['detail']
    assert api.get(route, headers=tech).json() is None


def test_coverage_legacy_capability_and_after_checkin(client, monkeypatch):
    api, _ = client
    admin, tech, _, visit, _, _, payload, _ = configured(api, monkeypatch)
    path = '/hotel-visits/' + visit['id']
    assert api.get('/sampling-capabilities', headers=tech).json()['coverage_enabled'] is True
    assert mutate(api, path, tech, '/check-in', {
        'device_time': '2026-11-16T00:00:00Z', 'gps_exception_reason': 'Test indoor'}).status_code == 200
    payload['expected_version'] += 1
    assert api.post(path + '/sampling-coverage', headers=admin, json=payload).status_code == 409
    monkeypatch.delenv('SAMPLING_MASTER_ENABLED')
    assert api.get('/sampling-capabilities', headers=tech).json()['master_enabled'] is False
    assert api.get(path + '/sampling-coverage', headers=tech).status_code == 503


def test_coverage_extra_point_and_same_month_revisit(client, monkeypatch):
    api, _ = client
    admin, tech, _, visit, floor, _, payload, base = configured(api, monkeypatch)
    point = api.post(base + '/' + floor['id'] + '/sampling-points', headers=admin,
        json={'name': 'Extra point without known AP', 'position': 4}).json()
    payload['floors'][0]['points'].append({'id': point['id'], 'version': point['version']})
    for record in (visit, api.post('/hotel-visits', headers=admin, json={
            'hotel_id': visit['hotel_id'], 'technician_id': visit['technician_id'],
            'planned_date': visit['planned_date']}).json()):
        response = api.post('/hotel-visits/' + record['id'] + '/sampling-coverage', headers=admin, json=payload)
        assert response.status_code == 201, response.text
        snapshot = response.json()
        assert snapshot['floors'][0]['target_count'] == 5
        assert len(snapshot['floors'][0]['points']) == 5
        assert snapshot['floors'][0]['points'][-1]['device'] is None
        # Visit detail carries the same snapshot for Android cache and revision history.
        assert api.get('/hotel-visits/' + record['id'], headers=tech).json()['sampling_coverage'] == snapshot
