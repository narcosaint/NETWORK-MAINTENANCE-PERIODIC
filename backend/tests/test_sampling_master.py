from uuid import uuid4
import pytest
from sqlalchemy import inspect
from test_modules import client, isolated_lifespan
from test_hotel_visits import setup_hotel


def test_master_disabled_without_schema_access(client, monkeypatch):
    api, engine = client
    admin, _, _, visit, _, _ = setup_hotel(api)
    monkeypatch.delenv('SAMPLING_MASTER_ENABLED', raising=False)
    from app.models import SamplingPoint, HotelFloor
    SamplingPoint.__table__.drop(engine)
    HotelFloor.__table__.drop(engine)
    response = api.get(f"/hotels/{visit['hotel_id']}/floors", headers=admin)
    assert response.status_code == 503
    assert api.get('/hotels', headers=admin).status_code == 200
    assert 'hotel_floors' not in inspect(engine).get_table_names()


def test_master_scope_versions_archive_and_ap_integrity(client, monkeypatch):
    monkeypatch.setenv('SAMPLING_MASTER_ENABLED', 'true')
    api, _ = client
    admin, assigned, other, visit, devices, _ = setup_hotel(api)
    base = f"/hotels/{visit['hotel_id']}/floors"
    assert api.get(base).status_code == 401
    assert api.get(base, headers=other).status_code == 404
    assert api.post(base, headers=assigned, json={'name': 'Lantai 1', 'position': 0}).status_code == 403
    payload = {'id': str(uuid4()), 'name': 'Lantai 1', 'position': 0}
    response = api.post(base, headers=admin, json=payload)
    assert response.status_code == 201, response.text
    floor = response.json()
    assert floor['default_sampling_count'] == 4 and floor['version'] == 1
    assert api.post(base, headers=admin, json=payload).json()['id'] == floor['id']
    assert api.post(base, headers=admin, json={**payload, 'name': 'Other'}).status_code == 409
    assert api.post(base, headers=admin, json={'name': ' lantai 1 ', 'position': 1}).status_code == 409
    path = base + '/' + floor['id']
    points = path + '/sampling-points'
    assert api.get(points, headers=assigned).json() == []  # target is not four dummy records
    for name in ('Kamar 101', 'Koridor'):
        response = api.post(points, headers=admin, json={
            'name': name, 'position': 0, 'device_id': devices[2]['id']})
        assert response.status_code == 201, response.text
    point = response.json()
    assert len(api.get(points, headers=assigned).json()) == 2
    assert len(api.get(points + '?limit=1', headers=assigned).json()) == 1
    assert api.get(points + '?limit=101', headers=assigned).status_code == 422
    assert api.post(points, headers=admin, json={
        'name': 'Router invalid', 'position': 2, 'device_id': devices[0]['id']}).status_code == 422
    other_hotel = api.post('/hotels', headers=admin, json={'name': 'Other hotel'}).json()
    foreign_ap = api.post('/devices', headers=admin, json={
        'hotel_id': other_hotel['id'], 'device_type': 'ap', 'name': 'Foreign AP'}).json()
    assert api.post(points, headers=admin, json={
        'name': 'Invalid cross hotel', 'position': 2, 'device_id': foreign_ap['id']}).status_code == 422
    assert api.get(f"/hotels/{other_hotel['id']}/floors/{floor['id']}/sampling-points", headers=admin).status_code == 404
    assert api.put('/devices/' + devices[2]['id'], headers=admin, json={
        'hotel_id': other_hotel['id'], 'device_type': 'ap', 'name': 'Moved AP'}).status_code == 409
    point_path = points + '/' + point['id']
    assert api.patch(point_path, headers=admin, json={
        'expected_version': 1, 'device_id': None, 'location': 'Area lift'}).json()['version'] == 2
    assert api.patch(point_path, headers=admin, json={
        'expected_version': 1, 'name': 'Stale'}).status_code == 409
    assert api.patch(point_path, headers=admin, json={
        'expected_version': 2, 'archived': True}).status_code == 200
    assert len(api.get(points, headers=admin).json()) == 1
    assert len(api.get(points + '?include_archived=true', headers=admin).json()) == 2
    assert api.patch(path, headers=admin, json={
        'expected_version': 1, 'name': 'Lantai Dasar', 'position': 3}).json()['version'] == 2
    assert api.patch(path, headers=admin, json={'expected_version': 1, 'archived': True}).status_code == 409
    assert api.patch(path, headers=admin, json={'expected_version': 2, 'archived': True}).status_code == 200
    assert api.get(base, headers=assigned).json() == []
    assert len(api.get(base + '?include_archived=true', headers=admin).json()) == 1
    assert api.post(points, headers=admin, json={'name': 'After archive', 'position': 3}).status_code == 409
    # New masters do not mutate existing report, devices, or workflow.
    after = api.get('/hotel-visits/' + visit['id'], headers=assigned).json()
    assert after['report'] == visit['report'] and after['version'] == visit['version']
    assert after['devices'] == visit['devices']


@pytest.mark.parametrize('payload', [
    {'name': '   ', 'position': 0}, {'name': 'Floor', 'position': -1},
    {'name': 'Floor', 'position': 0, 'default_sampling_count': 0},
    {'name': 'Floor', 'position': 0, 'hotel_id': str(uuid4())},
])
def test_invalid_floor_input(payload):
    from app.sampling_schemas import FloorCreate, FloorPatch, PointPatch
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FloorCreate.model_validate(payload)
    for schema in (FloorPatch, PointPatch):
        with pytest.raises(ValidationError):
            schema.model_validate({'expected_version': 1, 'name': None})
