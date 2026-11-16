"""Opt-in writes on a dedicated PostgreSQL database, isolated per test schema."""
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.api import db, _login_attempts
from app.main import app
from app.models import User
from app.security import hash_password
from http_client import ASGIClient
from test_modules import (
    setup_submitted_visit, test_device_details_validation_and_roundtrip as inventory_flow,
    test_review_revision_resubmission_and_approval as review_flow,
    test_review_authorization_validation_and_stale_decisions as review_permissions,
    test_failed_history_write_rolls_back_approval as review_rollback,
)

STAGING_URL = os.environ.get('HOTEL_STAGING_DATABASE_URL')
pytestmark = pytest.mark.skipif(not STAGING_URL, reason='HOTEL_STAGING_DATABASE_URL is not set')


def validate_staging_url(value):
    url = make_url(value)
    if url.drivername != 'postgresql+psycopg' or not (url.database or '').endswith(('_test', '_staging')):
        raise ValueError('Use postgresql+psycopg and a dedicated database ending _test or _staging')
    # Prevent connection overrides from bypassing the database-name guard.
    if url.query:
        raise ValueError('Connection query parameters are not allowed for staging tests')
    return url


@pytest.fixture
def staging_engine():
    url = validate_staging_url(STAGING_URL)
    owner = create_engine(url, poolclass=NullPool, connect_args={'connect_timeout': 3})
    schema = 'hotel_test_' + secrets.token_hex(12)
    # The generated identifier contains only a fixed prefix and hexadecimal digits.
    with owner.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, poolclass=NullPool, connect_args={
        'connect_timeout': 3, 'options': f'-c search_path={schema} -c lock_timeout=5000 -c statement_timeout=15000'})
    try:
        yield engine
    finally:
        engine.dispose()
        # Cleanup targets only the random schema created by this fixture.
        with owner.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        owner.dispose()


def migrate(engine, revision):
    config = Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, revision)


@pytest.fixture
def postgres_client(staging_engine):
    migrate(staging_engine, 'head')
    with Session(staging_engine) as session:
        session.add(User(username='admin', name='Staging Admin', role='supervisor', active=True,
                         password_hash=hash_password('strong-secret-123')))
        session.commit()
    _login_attempts.clear()
    previous = dict(app.dependency_overrides)
    def override():
        with Session(staging_engine) as session:
            yield session
    app.dependency_overrides[db] = override
    try:
        yield ASGIClient(app), staging_engine
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_upgrade_preserves_existing_inventory(staging_engine):
    migrate(staging_engine, '0001_initial')
    hotel_id, device_id = uuid4(), uuid4()
    with staging_engine.begin() as connection:
        connection.execute(text('INSERT INTO hotels (id, name, address) VALUES (:id, :name, :address)'),
                           {'id': hotel_id, 'name': 'Isolated staging hotel', 'address': 'Staging only'})
        connection.execute(text('INSERT INTO devices (id, hotel_id, name, device_type) VALUES (:id, :hotel, :name, :type)'),
                           {'id': device_id, 'hotel': hotel_id, 'name': 'Staging AP', 'type': 'ap'})
    migrate(staging_engine, 'head')
    # Running upgrade again must not create duplicates or alter old data.
    migrate(staging_engine, 'head')
    with staging_engine.connect() as connection:
        assert connection.execute(text('SELECT name FROM hotels WHERE id=:id'), {'id': hotel_id}).scalar_one() == 'Isolated staging hotel'
        assert connection.execute(text('SELECT hotel_id FROM devices WHERE id=:id'), {'id': device_id}).scalar_one() == hotel_id
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0009_site_report_profile'
        assert connection.execute(text('SELECT brand FROM devices WHERE id=:id'), {'id': device_id}).scalar_one() is None
        assert connection.execute(text('SELECT count(*) FROM users')).scalar_one() == 0
        assert connection.execute(text('SELECT count(*) FROM visit_events')).scalar_one() == 0


def test_postgres_review_flow(postgres_client):
    review_flow(postgres_client)


def test_postgres_review_permissions(postgres_client):
    review_permissions(postgres_client)


def test_postgres_review_rollback(postgres_client):
    review_rollback(postgres_client, None)


def test_concurrent_supervisor_decisions(postgres_client):
    api, engine = postgres_client
    admin, assigned, _, schedule, _, visit, _ = setup_submitted_visit(api)
    path = '/visits/' + visit['id']
    barrier = Barrier(2)
    def decide(decision):
        barrier.wait(timeout=10)
        response = api.post(path + '/review', headers=admin, json={
            'expected_version': visit['version'], 'decision': decision, 'reason': 'Reviewed test evidence'})
        return decision, response.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(decide, decision) for decision in ('approved', 'revision_requested')]
        outcomes = [future.result(timeout=25) for future in futures]
    assert sorted(code for _, code in outcomes) == [200, 409]
    winner = next(decision for decision, code in outcomes if code == 200)
    assert api.get(path, headers=assigned).json()['status'] == winner
    expected_schedule = 'completed' if winner == 'approved' else 'pending'
    assert api.get('/schedules/' + schedule['id'], headers=admin).json()['status'] == expected_schedule
    history = api.get(path + '/history', headers=admin).json()
    assert len(history) == 2 and history[-1]['action'] == winner


def test_postgres_constraints(postgres_client):
    from sqlalchemy.exc import IntegrityError
    api, engine = postgres_client
    _, _, _, schedule, _, _, _ = setup_submitted_visit(api)
    statements = [
        ('UPDATE maintenance_schedules SET month=\'2026-11-02\' WHERE id=:id', {'id': schedule['id']}),
        ('INSERT INTO maintenance_schedules (id, device_id, technician_id, month, status) '
         'SELECT :new_id, device_id, technician_id, month, status FROM maintenance_schedules WHERE id=:id',
         {'new_id': uuid4(), 'id': schedule['id']}),
        ('DELETE FROM hotels', {}),
    ]
    for statement, params in statements:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(statement), params)



def test_postgres_inventory_details(postgres_client):
    inventory_flow(postgres_client)



@pytest.fixture
def hotel_photo_storage(monkeypatch, tmp_path):
    root = tmp_path / 'photos'
    monkeypatch.setenv('PHOTO_STORAGE_ROOT', str(root))
    return root


def test_postgres_hotel_photo_workflow(postgres_client, hotel_photo_storage):
    from test_hotel_visits import test_hotel_sampling_photo_and_revision_flow
    test_hotel_sampling_photo_and_revision_flow(postgres_client, hotel_photo_storage)


def test_postgres_hotel_pending_approval(postgres_client, hotel_photo_storage):
    from test_hotel_visits import test_pending_work_approval_is_not_completion
    test_pending_work_approval_is_not_completion(postgres_client)


def test_concurrent_hotel_reviews(postgres_client, hotel_photo_storage):
    from test_hotel_visits import setup_hotel, populate, checkout
    api, _ = postgres_client
    admin, assigned, _, visit, devices, _ = setup_hotel(api)
    path = '/hotel-visits/' + visit['id']
    populate(api, path, assigned, devices)
    response = checkout(api, path, assigned)
    assert response.status_code == 200
    version = response.json()['version']
    barrier = Barrier(2)
    def decide(decision):
        barrier.wait(timeout=10)
        return decision, api.post(path + '/review', headers=admin, json={
            'expected_version':version, 'decision':decision, 'reason':'Reviewed concurrent test evidence'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(decide, decision) for decision in ('approved','revision_requested')]
        outcomes = [future.result(timeout=25) for future in results]
    assert sorted(status for _, status in outcomes) == [200,409]
    winner = next(decision for decision, status in outcomes if status==200)
    assert api.get(path, headers=assigned).json()['status'] == winner
    assert len(api.get(path + '/history', headers=admin).json()) == 2


def test_postgres_automatic_speedtest_provenance(postgres_client, monkeypatch):
    from test_speedtests import test_https_confirmed_wifi_result_applies_without_overwriting_rf
    from app.speedtest_api import _live
    _live.clear()
    try:
        test_https_confirmed_wifi_result_applies_without_overwriting_rf(postgres_client, monkeypatch)
    finally:
        _live.clear()


def test_concurrent_speedtest_finish(postgres_client, monkeypatch):
    from test_speedtests import setup_sample, start, transfers, METRICS
    from app.speedtest_api import _live
    monkeypatch.delenv('PUBLIC_SPEEDTEST_ORIGIN', raising=False)
    _live.clear()
    try:
        api,_=postgres_client
        _,assigned,_,path,item=setup_sample(api)
        run=start(api,assigned,path,item).json()
        transfers(api,run)
        barrier=Barrier(2)
        def finish(status):
            barrier.wait(timeout=10)
            payload={'status':status}
            if status=='completed':payload['metrics']=METRICS
            return api.post('/network-speedtests/'+run['id']+'/finish',headers=assigned,json=payload).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(finish,status) for status in ('completed','aborted')]
            statuses=[job.result(timeout=25) for job in jobs]
        assert sorted(statuses)==[200,409]
        stored=api.get('/network-speedtests/'+run['id'],headers=assigned).json()
        assert stored['status'] in ('completed','aborted')
        assert (stored['metrics'] is not None)==(stored['status']=='completed')
    finally:
        _live.clear()


def test_postgres_site_report_revision(postgres_client, hotel_photo_storage):
    from test_report_revision import test_site_identity_and_bandwidth_policy_are_authoritative_and_frozen
    test_site_identity_and_bandwidth_policy_are_authoritative_and_frozen(postgres_client)


def test_postgres_legacy_report_compatibility(postgres_client, hotel_photo_storage):
    from test_report_revision import test_legacy_report_remains_readable_without_reinterpreting_old_measurements
    test_legacy_report_remains_readable_without_reinterpreting_old_measurements(postgres_client)
