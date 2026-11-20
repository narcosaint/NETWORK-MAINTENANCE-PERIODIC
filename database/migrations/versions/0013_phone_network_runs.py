"""Reviewed: speedtest belongs to an area OR a legacy visit device, never fake APs."""
from alembic import op
import sqlalchemy as sa
revision = '0013_phone_network_runs'
down_revision = '0012_sampling_speedtest_attempts'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('network_speedtests', sa.Column('sampling_session_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_speedtest_sampling_session', 'network_speedtests', 'sampling_sessions',
                          ['sampling_session_id'], ['id'], ondelete='RESTRICT')
    op.alter_column('network_speedtests', 'visit_device_id', existing_type=sa.Uuid(), nullable=True)
    op.create_check_constraint('ck_speedtest_one_scope', 'network_speedtests',
        '(visit_device_id IS NOT NULL AND sampling_session_id IS NULL) OR '
        '(visit_device_id IS NULL AND sampling_session_id IS NOT NULL)')
    op.create_index('ix_network_speedtests_sampling_session_id', 'network_speedtests', ['sampling_session_id'])


def downgrade():
    raise RuntimeError('Phone-network measurement history requires reviewed forward recovery')
