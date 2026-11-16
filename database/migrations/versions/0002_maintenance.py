"""Users, revocable sessions and monthly preventive maintenance; no seed data."""
from alembic import op
import sqlalchemy as sa

revision = '0002_maintenance'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('password_hash', sa.String(300), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.CheckConstraint("role IN ('technician', 'supervisor')", name='ck_users_role'))
    op.create_table('login_sessions',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_login_sessions_user_id', 'login_sessions', ['user_id'])
    op.create_table('maintenance_schedules',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('device_id', sa.Uuid(), sa.ForeignKey('devices.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('technician_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('notes', sa.Text()),
        sa.UniqueConstraint('device_id', 'month', name='uq_schedule_device_month'),
        sa.CheckConstraint("status IN ('pending', 'completed')", name='ck_schedule_status'),
        sa.CheckConstraint('EXTRACT(DAY FROM month) = 1', name='ck_schedule_month'))
    op.create_index('ix_maintenance_schedules_device_id', 'maintenance_schedules', ['device_id'])
    op.create_index('ix_maintenance_schedules_technician_id', 'maintenance_schedules', ['technician_id'])


def downgrade():
    op.drop_table('maintenance_schedules')
    op.drop_table('login_sessions')
    op.drop_table('users')
