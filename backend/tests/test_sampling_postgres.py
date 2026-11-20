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
from test_sampling_speedtests import test_point_runs_do_not_share_results_or_apply_to_legacy_ap as sampling_run_flow
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

pytestmark = pytest.mark.skipif(not STAGING_URL, reason='HOTEL_STAGING_DATABASE_URL is not set')


@pytest.fixture
def sampling_postgres_client(postgres_client):
    api, engine = postgres_client
    with engine.begin() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0014_user_contact_profile'
        for table in ('hotel_floors','sampling_points','sampling_coverages','sampling_coverage_floors',
                      'sampling_sessions','sampling_observations','sampling_speedtest_attempts'):
            assert table in inspect(connection).get_table_names()
            assert connection.execute(text(f'SELECT count(*) FROM {table}')).scalar_one()==0
    return api, engine


def test_draft_postgres_master_flow(sampling_postgres_client, monkeypatch):
    master_flow(sampling_postgres_client, monkeypatch)


def test_draft_postgres_coverage_flow(sampling_postgres_client, monkeypatch):
    coverage_flow(sampling_postgres_client, monkeypatch)


@pytest.fixture
def observation_postgres_client(sampling_postgres_client):
    api, engine = sampling_postgres_client
    return api, engine


def test_draft_postgres_observation_flow(observation_postgres_client, monkeypatch):
    observation_flow(observation_postgres_client, monkeypatch)


def test_draft_postgres_radio_flow(observation_postgres_client, monkeypatch):
    radio_flow(observation_postgres_client, monkeypatch)


def test_draft_postgres_session_speedtests(observation_postgres_client, monkeypatch):
    api, engine = observation_postgres_client
    from app import speedtest_api
    speedtest_api._live.clear()
    try: sampling_run_flow((api,engine), monkeypatch)
    finally: speedtest_api._live.clear()


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


@pytest.mark.parametrize('flow_name', ['test_technician_can_start_field_scope_after_checkin_with_default_target_and_audit', 'test_field_append_preserves_existing_coverage_and_rejects_stale_cross_scope_and_wrong_ap', 'test_field_mapping_on_next_visit_does_not_rewrite_prior_snapshot_or_master'])
def test_draft_postgres_field_locations(sampling_postgres_client, monkeypatch, flow_name):
    import test_sampling_field
    getattr(test_sampling_field, flow_name)(sampling_postgres_client, monkeypatch)


def test_concurrent_field_append_uses_one_request(sampling_postgres_client, monkeypatch):
    from test_sampling_field import field_ready
    api, engine = sampling_postgres_client
    _, tech, _, path, _, payload = field_ready(api, monkeypatch)
    barrier = Barrier(2)
    def append():
        barrier.wait(timeout=10)
        return api.post(path+'/sampling-locations', headers=tech, json=payload)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses=list(executor.map(lambda _: append(), range(2)))
    assert [r.status_code for r in responses] == [201,201]
    assert sorted(r.json()['replayed'] for r in responses) == [False,True]
    with engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM sampling_sessions')).scalar_one()==1



def test_postgres_phone_run_without_ap(sampling_postgres_client,monkeypatch):
    from test_sampling_speedtests import test_phone_network_test_needs_no_inventory_or_mac_match
    test_phone_network_test_needs_no_inventory_or_mac_match(sampling_postgres_client,monkeypatch)


@pytest.mark.parametrize('flow_name', ['test_complete_transfer_photo_pic_submit_pdf_and_approval', 'test_edits_invalidate_signature_failed_tests_need_action_and_revision_resigns', 'test_photo_replay_scope_bytes_missing_and_blank_signature'])
def test_postgres_completion_workflow(sampling_postgres_client,monkeypatch,tmp_path,flow_name):
    import test_completion
    getattr(test_completion,flow_name)(sampling_postgres_client,monkeypatch,tmp_path)


def test_postgres_notes_only_preserve_radio_and_independent_area_versions(sampling_postgres_client,monkeypatch):
    from test_sampling_observations import test_notes_only_preserve_radio_independent_edits_and_replay
    test_notes_only_preserve_radio_independent_edits_and_replay(sampling_postgres_client,monkeypatch)


def test_postgres_user_contact_profile(sampling_postgres_client):
    from test_user_profile import test_self_profile_roundtrip_validation_scope_and_conflict
    test_self_profile_roundtrip_validation_scope_and_conflict(sampling_postgres_client)


def test_postgres_contact_upgrade_preserves_existing_users(staging_engine):
    from test_staging import migrate
    migrate(staging_engine,'0013_phone_network_runs')
    user_id=uuid4()
    with staging_engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, username, name, password_hash, role, active) VALUES (:id, 'old_user', 'Old User', 'unchanged-password-hash', 'technician', true)"),{'id':user_id})
        before=connection.execute(text('SELECT id, username, name, password_hash, role, active FROM users')).all()
    migrate(staging_engine,'head')
    with staging_engine.connect() as connection:
        assert connection.execute(text('SELECT id, username, name, password_hash, role, active FROM users')).all()==before
        assert connection.execute(text('SELECT contact_profile FROM users')).scalar_one() is None


def test_postgres_stale_observation_outbox_merge(sampling_postgres_client,monkeypatch):
    from test_sampling_observations import test_stale_outbox_merges_independent_notes_and_preserves_new_radio
    test_stale_outbox_merges_independent_notes_and_preserves_new_radio(sampling_postgres_client,monkeypatch)
