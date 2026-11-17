"""Compile the review draft without activating a revision or connecting to a DB."""
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
import re

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from alembic.config import Config
import pytest


def test_sampling_draft_sql_and_inactive_head():
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
    assert scripts.get_current_head() == draft.down_revision


def test_observation_draft_is_additive_and_inactive():
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
    assert ScriptDirectory.from_config(Config(str(root / 'alembic.ini'))).get_current_head() == '0009_site_report_profile'
