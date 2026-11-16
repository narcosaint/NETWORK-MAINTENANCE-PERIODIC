"""Hotel-wide inspections and private photo metadata. Preserve legacy visits."""
from alembic import op
import sqlalchemy as sa

revision = '0007_hotel_visits'
down_revision = '0006_device_details'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('hotel_visits',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('hotel_id', sa.Uuid(), sa.ForeignKey('hotels.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('technician_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('planned_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('checkin', sa.JSON()), sa.Column('checkout', sa.JSON()),
        sa.Column('report', sa.JSON(), nullable=False),
        sa.CheckConstraint("status IN ('assigned', 'in_progress', 'submitted', 'revision_requested', 'approved')", name='ck_hotel_visit_status'),
        sa.CheckConstraint('version >= 1', name='ck_hotel_visit_version'))
    op.create_index('ix_hotel_visits_hotel_id', 'hotel_visits', ['hotel_id'])
    op.create_index('ix_hotel_visits_technician_id', 'hotel_visits', ['technician_id'])
    op.create_table('hotel_visit_devices',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('visit_id', sa.Uuid(), sa.ForeignKey('hotel_visits.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('device_id', sa.Uuid(), sa.ForeignKey('devices.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('device_snapshot', sa.JSON(), nullable=False),
        sa.Column('floor', sa.String(100)), sa.Column('point', sa.String(200)),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.UniqueConstraint('visit_id', 'device_id', name='uq_hotel_visit_device'))
    op.create_index('ix_hotel_visit_devices_visit_id', 'hotel_visit_devices', ['visit_id'])
    op.create_table('device_photos',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('visit_device_id', sa.Uuid(), sa.ForeignKey('hotel_visit_devices.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('object_key', sa.String(50), unique=True, nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False), sa.Column('height', sa.Integer(), nullable=False))
    op.create_index('ix_device_photos_visit_device_id', 'device_photos', ['visit_device_id'])
    op.create_table('hotel_visit_events',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('visit_id', sa.Uuid(), sa.ForeignKey('hotel_visits.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(30), nullable=False), sa.Column('reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.UniqueConstraint('visit_id', 'version', name='uq_hotel_visit_event_version'))
    op.create_index('ix_hotel_visit_events_visit_id', 'hotel_visit_events', ['visit_id'])


def downgrade():
    raise RuntimeError('Photo evidence and hotel visits require reviewed forward recovery')
