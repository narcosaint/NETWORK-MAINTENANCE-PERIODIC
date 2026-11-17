"""Opt-in draft migration/API checks on a dedicated random PostgreSQL schema."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from test_staging import STAGING_URL, staging_engine, postgres_client
from test_sampling_master import test_master_scope_versions_archive_and_ap_integrity as master_flow
from test_sampling_coverage import test_coverage_snapshot_replay_scope_and_legacy_submit_guard as coverage_flow
from test_sampling_observations import test_observation_scope_replay_and_unchanged_completion as observation_flow
from test_sampling_observations import test_client_radio_observation_keeps_trust_and_point_scope as radio_flow
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

pytestmark = pytest.mark.skipif(not STAGING_URL, reason='HOTEL_STAGING_DATABASE_URL is not set')


@pytest.fixture
def sampling_postgres_client(postgres_client):
    api, engine = postgres_client
    path = Path(__file__).resolve().parents[2] / 'docs/migrations/0010_sampling_foundation.py'
    spec = spec_from_file_location('postgres_sampling_draft', path)
    draft = module_from_spec(spec)
    spec.loader.exec_module(draft)
    with engine.begin() as connection:
        draft.op = Operations(MigrationContext.configure(connection))
        draft.upgrade()
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == draft.down_revision
        for table in ('hotel_floors', 'sampling_points', 'sampling_coverages',
                      'sampling_coverage_floors', 'sampling_sessions'):
            assert table in inspect(connection).get_table_names()
            assert connection.execute(text(f'SELECT count(*) FROM {table}')).scalar_one() == 0
    return api, engine


def test_draft_postgres_master_flow(sampling_postgres_client, monkeypatch):
    master_flow(sampling_postgres_client, monkeypatch)


def test_draft_postgres_coverage_flow(sampling_postgres_client, monkeypatch):
    coverage_flow(sampling_postgres_client, monkeypatch)


@pytest.fixture
def observation_postgres_client(sampling_postgres_client):
    api, engine = sampling_postgres_client
    path = Path(__file__).resolve().parents[2] / 'docs/migrations/0011_sampling_observations.py'
    spec = spec_from_file_location('postgres_observation_draft', path)
    draft = module_from_spec(spec)
    spec.loader.exec_module(draft)
    with engine.begin() as connection:
        draft.op = Operations(MigrationContext.configure(connection))
        draft.upgrade()
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0009_site_report_profile'
    return api, engine


def test_draft_postgres_observation_flow(observation_postgres_client, monkeypatch):
    observation_flow(observation_postgres_client, monkeypatch)


def test_draft_postgres_radio_flow(observation_postgres_client, monkeypatch):
    radio_flow(observation_postgres_client, monkeypatch)


def test_concurrent_coverage_activation_is_idempotent(sampling_postgres_client, monkeypatch):
    from test_sampling_coverage import configured
    api, engine = sampling_postgres_client
    admin, _, _, visit, _, _, payload, _ = configured(api, monkeypatch)
    barrier = Barrier(2)
    def activate():
        barrier.wait(timeout=10)
        return api.post('/hotel-visits/' + visit['id'] + '/sampling-coverage', headers=admin, json=payload)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: activate(), range(2)))
    assert [response.status_code for response in responses] == [201, 201]
    assert responses[0].json()['id'] == responses[1].json()['id']
    with engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM sampling_sessions')).scalar_one() == 4
        assert connection.execute(text('SELECT count(*) FROM sampling_coverages')).scalar_one() == 1
