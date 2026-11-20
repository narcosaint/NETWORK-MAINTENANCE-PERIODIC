"""Verify promoted migrations match reviewed SQL without connecting to a DB."""
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
import re

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from alembic.config import Config
import pytest


def test_sampling_reviewed_sql_and_promoted_chain():
    root = Path(__file__).resolve().parents[2]
    spec = spec_from_file_location('sampling_draft', root / 'docs/migrations/0010_sampling_foundation.py')
    draft = module_from_spec(spec)
    spec.loader.exec_module(draft)
    output = StringIO()
    context = MigrationContext.configure(dialect_name='postgresql', opts={
        'as_sql': True, 'output_buffer': output,
    })
    draft.op = Operations(context)
    draft.upgrade()
    sql = output.getvalue()
    for table in ('hotel_floors', 'sampling_points', 'sampling_coverages',
                  'sampling_coverage_floors', 'sampling_sessions'):
        assert f'CREATE TABLE {table}' in sql
    assert sql.count('CREATE TABLE ') == 5
    assert 'FOREIGN KEY(coverage_floor_id, coverage_id)' in sql
    assert 'UNIQUE (coverage_id, sampling_point_id)' in sql
    assert 'WHERE archived_at IS NULL' in sql
    assert 'DEFAULT \'4\'' in sql
    assert 'EXTRACT(DAY FROM period) = 1' in sql
    assert 'UNIQUE (device_id)' not in sql
    for forbidden in ('DROP ', 'DELETE ', 'UPDATE ', 'INSERT ', 'ALTER TABLE '):
        assert not re.search(r'^\s*' + forbidden, sql, re.MULTILINE)
    with pytest.raises(RuntimeError, match='forward recovery'):
        draft.downgrade()
    scripts = ScriptDirectory.from_config(Config(str(root / 'alembic.ini')))
    assert scripts.get_revision(draft.revision).down_revision == draft.down_revision
    assert scripts.get_current_head() == '0014_user_contact_profile'
    assert (root/'database/migrations/versions/0010_sampling_foundation.py').read_bytes() == (root/'docs/migrations/0010_sampling_foundation.py').read_bytes()


def test_observation_reviewed_migration_is_additive():
    root = Path(__file__).resolve().parents[2]
    spec = spec_from_file_location('observations_draft', root / 'docs/migrations/0011_sampling_observations.py')
    draft = module_from_spec(spec)
    spec.loader.exec_module(draft)
    output = StringIO()
    draft.op = Operations(MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': output}))
    draft.upgrade()
    sql = output.getvalue()
    assert 'CREATE TABLE sampling_observations' in sql
    assert 'UNIQUE (session_id, session_version)' in sql
    assert 'REFERENCES sampling_sessions (id) ON DELETE RESTRICT' in sql
    for forbidden in ('DROP ', 'DELETE ', 'UPDATE ', 'INSERT ', 'ALTER TABLE '):
        assert not re.search(r'^\s*' + forbidden, sql, re.MULTILINE)
    assert ScriptDirectory.from_config(Config(str(root / 'alembic.ini'))).get_current_head() == '0014_user_contact_profile'


def test_session_speedtest_draft_does_not_change_legacy_schema():
    root=Path(__file__).resolve().parents[2]
    spec=spec_from_file_location('speedtest_draft',root/'docs/migrations/0012_sampling_speedtest_attempts.py')
    draft=module_from_spec(spec);spec.loader.exec_module(draft)
    output=StringIO()
    draft.op=Operations(MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':output}))
    draft.upgrade();sql=output.getvalue()
    assert 'CREATE TABLE sampling_speedtest_attempts' in sql
    assert 'REFERENCES network_speedtests (id) ON DELETE RESTRICT' in sql
    assert 'UNIQUE (run_id)' in sql
    assert not re.search(r'^\s*(ALTER|DROP|DELETE|INSERT|UPDATE)\b',sql,re.MULTILINE)
    assert ScriptDirectory.from_config(Config(str(root/'alembic.ini'))).get_current_head()=='0014_user_contact_profile'


@pytest.mark.parametrize('name', ['0010_sampling_foundation','0011_sampling_observations','0012_sampling_speedtest_attempts'])
def test_promoted_revision_matches_reviewed_file(name):
    root=Path(__file__).resolve().parents[2]
    assert (root/'database/migrations/versions'/(name+'.py')).read_bytes()==(root/'docs/migrations'/(name+'.py')).read_bytes()



def test_phone_run_migration_has_one_scope_constraint_and_no_data_rewrite():
    root=Path(__file__).resolve().parents[2]
    spec=spec_from_file_location('phone_runs',root/'database/migrations/versions/0013_phone_network_runs.py')
    module=module_from_spec(spec);spec.loader.exec_module(module)
    output=StringIO();module.op=Operations(MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':output}));module.upgrade()
    sql=output.getvalue()
    assert 'ADD COLUMN sampling_session_id UUID' in sql
    assert 'ALTER COLUMN visit_device_id DROP NOT NULL' in sql
    assert 'ck_speedtest_one_scope' in sql and 'ON DELETE RESTRICT' in sql
    assert not re.search(r'^\s*(UPDATE|INSERT|DELETE|DROP TABLE|TRUNCATE)\b',sql,re.MULTILINE)
    with pytest.raises(RuntimeError):module.downgrade()


def test_user_contact_profile_reviewed_sql_is_additive():
    root=Path(__file__).resolve().parents[2]
    spec=spec_from_file_location('user_profile',root/'database/migrations/versions/0014_user_contact_profile.py')
    migration=module_from_spec(spec);spec.loader.exec_module(migration)
    output=StringIO()
    migration.op=Operations(MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':output}))
    migration.upgrade()
    assert output.getvalue().strip()=='ALTER TABLE users ADD COLUMN contact_profile JSON;'
    assert migration.down_revision=='0013_phone_network_runs'
    assert (root/'docs/reviews/USER-PROFILE-0014.md').is_file()
    with pytest.raises(RuntimeError,match='forward recovery'):migration.downgrade()
