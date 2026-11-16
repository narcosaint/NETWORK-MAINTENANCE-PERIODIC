"""Browser network tests with explicit transport and connection provenance."""
from alembic import op
import sqlalchemy as sa
revision = '0008_network_speedtests'
down_revision = '0007_hotel_visits'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('network_speedtests',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('visit_device_id', sa.Uuid(), sa.ForeignKey('hotel_visit_devices.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('band', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True)),
        sa.Column('context', sa.JSON(), nullable=False), sa.Column('metrics', sa.JSON()),
        sa.Column('error', sa.Text()),
        sa.CheckConstraint("status IN ('running', 'completed', 'failed', 'aborted')", name='ck_speedtest_status'),
        sa.CheckConstraint("band IN ('band_24', 'band_5')", name='ck_speedtest_band'))
    op.create_index('ix_network_speedtests_visit_device_id', 'network_speedtests', ['visit_device_id'])
    op.create_index('ix_network_speedtests_actor_id', 'network_speedtests', ['actor_id'])


def downgrade():
    raise RuntimeError('Measurement history requires reviewed forward recovery')
