"""REVIEW DRAFT: deliberately outside Alembic's active versions directory.

Do not move into database/migrations/versions until reviewed. No seed/backfill.
Cross-hotel ownership and immutable snapshots require the companion API.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0010_sampling_foundation'
down_revision = '0009_site_report_profile'
branch_labels = None
depends_on = None


def identifier():
    return sa.Column('id', sa.Uuid(), primary_key=True)


def reference(name, target, nullable=False):
    return sa.Column(name, sa.Uuid(), sa.ForeignKey(target, ondelete='RESTRICT'), nullable=nullable)


def created():
    return sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def version():
    return sa.Column('version', sa.Integer(), nullable=False, server_default='1')


def upgrade():
    op.create_table('hotel_floors', identifier(), reference('hotel_id', 'hotels.id'),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('default_sampling_count', sa.Integer(), nullable=False, server_default='4'),
        version(), created(), sa.Column('archived_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("btrim(name) <> ''", name='ck_floor_name'),
        sa.CheckConstraint('position >= 0', name='ck_floor_position'),
        sa.CheckConstraint('default_sampling_count > 0', name='ck_floor_target'),
        sa.CheckConstraint('version >= 1', name='ck_floor_version'))
    op.create_table('sampling_points', identifier(), reference('floor_id', 'hotel_floors.id'),
        sa.Column('name', sa.String(200), nullable=False), sa.Column('location', sa.Text()),
        sa.Column('position', sa.Integer(), nullable=False),
        reference('device_id', 'devices.id', nullable=True), version(), created(),
        sa.Column('archived_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("btrim(name) <> ''", name='ck_point_name'),
        sa.CheckConstraint('position >= 0', name='ck_point_position'),
        sa.CheckConstraint('version >= 1', name='ck_point_version'))
    op.create_table('sampling_coverages', identifier(), reference('hotel_visit_id', 'hotel_visits.id'),
        sa.Column('period', sa.Date(), nullable=False),
        sa.Column('hotel_snapshot', JSONB(), nullable=False),
        sa.Column('photo_policy_snapshot', JSONB(), nullable=False),
        sa.Column('schema_version', sa.Integer(), nullable=False, server_default='1'),
        reference('created_by', 'users.id'), created(),
        sa.UniqueConstraint('hotel_visit_id', name='uq_coverage_visit'),
        sa.CheckConstraint('EXTRACT(DAY FROM period) = 1', name='ck_coverage_period'),
        sa.CheckConstraint('schema_version = 1', name='ck_coverage_schema_version'))
    op.create_table('sampling_coverage_floors', identifier(),
        reference('coverage_id', 'sampling_coverages.id'), reference('floor_id', 'hotel_floors.id'),
        sa.Column('name_snapshot', sa.String(100), nullable=False),
        sa.Column('position_snapshot', sa.Integer(), nullable=False),
        sa.Column('target_count', sa.Integer(), nullable=False),
        sa.UniqueConstraint('coverage_id', 'floor_id', name='uq_coverage_floor'),
        sa.UniqueConstraint('id', 'coverage_id', name='uq_coverage_floor_scope'),
        sa.CheckConstraint("btrim(name_snapshot) <> ''", name='ck_coverage_floor_name'),
        sa.CheckConstraint('position_snapshot >= 0', name='ck_coverage_floor_position'),
        sa.CheckConstraint('target_count > 0', name='ck_coverage_floor_target'))
    op.create_table('sampling_sessions', identifier(), reference('coverage_id', 'sampling_coverages.id'),
        sa.Column('coverage_floor_id', sa.Uuid(), nullable=False),
        reference('sampling_point_id', 'sampling_points.id'),
        sa.Column('point_snapshot', JSONB(), nullable=False),
        sa.Column('position_snapshot', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='untested'),
        version(), created(), sa.Column('observed_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['coverage_floor_id', 'coverage_id'],
            ['sampling_coverage_floors.id', 'sampling_coverage_floors.coverage_id'],
            name='fk_session_coverage_floor', ondelete='RESTRICT'),
        sa.UniqueConstraint('coverage_id', 'sampling_point_id', name='uq_session_point'),
        sa.CheckConstraint('position_snapshot >= 0', name='ck_session_position'),
        sa.CheckConstraint('version >= 1', name='ck_session_version'),
        sa.CheckConstraint("status IN ('untested', 'good', 'attention', 'problem')", name='ck_session_status'))

    for table, parent in [('hotel_floors', 'hotel_id'), ('sampling_points', 'floor_id')]:
        op.create_index('uq_' + table + '_active_name', table,
            [parent, sa.text('lower(btrim(name))')], unique=True,
            postgresql_where=sa.text('archived_at IS NULL'))
        op.create_index('ix_' + table + '_active_order', table, [parent, 'position', 'id'],
            postgresql_where=sa.text('archived_at IS NULL'))
    for table, columns in [
        ('hotel_floors', ['hotel_id']), ('sampling_points', ['floor_id']),
        ('sampling_points', ['device_id']), ('sampling_coverages', ['created_by']),
        ('sampling_coverage_floors', ['floor_id']),
        ('sampling_sessions', ['coverage_floor_id', 'coverage_id']),
        ('sampling_sessions', ['sampling_point_id']), ('sampling_sessions', ['coverage_id', 'status']),
    ]:
        op.create_index('ix_' + table + '_' + '_'.join(columns), table, columns)


def downgrade():
    raise RuntimeError('Sampling history requires reviewed forward recovery')
