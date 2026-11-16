"""Assigned visits and check-in evidence; no data seeding."""
from alembic import op
import sqlalchemy as sa

revision = '0003_visits'
down_revision = '0002_maintenance'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('visits',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('schedule_id', sa.Uuid(), sa.ForeignKey('maintenance_schedules.id', ondelete='RESTRICT'), nullable=False, unique=True),
        sa.Column('technician_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('checked_in_at', sa.DateTime(timezone=True)),
        sa.Column('device_time', sa.DateTime(timezone=True)),
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('accuracy_m', sa.Float()),
        sa.Column('gps_exception_reason', sa.Text()),
        sa.CheckConstraint("status IN ('assigned', 'in_progress')", name='ck_visit_status'),
        sa.CheckConstraint('version >= 1', name='ck_visit_version'),
        sa.CheckConstraint("(status = 'assigned' AND checked_in_at IS NULL) OR "
                           "(status = 'in_progress' AND checked_in_at IS NOT NULL)", name='ck_visit_checkin'),
        sa.CheckConstraint('(latitude IS NULL AND longitude IS NULL AND accuracy_m IS NULL) OR '
                           '(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 '
                           'AND accuracy_m >= 0 AND latitude IS NOT NULL AND longitude IS NOT NULL '
                           'AND accuracy_m IS NOT NULL)', name='ck_visit_coordinates'))
    op.create_index('ix_visits_technician_id', 'visits', ['technician_id'])


def downgrade():
    op.drop_table('visits')
