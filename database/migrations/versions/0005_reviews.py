"""Review history and atomic schedule completion; no seed or backfill."""
from alembic import op
import sqlalchemy as sa

revision = '0005_reviews'
down_revision = '0004_checklists'
branch_labels = None
depends_on = None


def upgrade():
    for name in ('ck_visit_status', 'ck_visit_checkin', 'ck_visit_checkout'):
        op.drop_constraint(name, 'visits', type_='check')
    op.create_check_constraint('ck_visit_status', 'visits',
        "status IN ('assigned', 'in_progress', 'submitted', 'revision_requested', 'approved')")
    op.create_check_constraint('ck_visit_checkin', 'visits',
        "(status = 'assigned' AND checked_in_at IS NULL) OR "
        "(status IN ('in_progress', 'submitted', 'revision_requested', 'approved') AND checked_in_at IS NOT NULL)")
    op.create_check_constraint('ck_visit_checkout', 'visits',
        "(status IN ('submitted', 'revision_requested', 'approved') AND checked_out_at IS NOT NULL AND pic_exception_reason IS NOT NULL) OR "
        "(status IN ('assigned', 'in_progress') AND checked_out_at IS NULL)")
    op.create_table('visit_events',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('visit_id', sa.Uuid(), sa.ForeignKey('visits.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.UniqueConstraint('visit_id', 'version', name='uq_visit_event_version'),
        sa.CheckConstraint("action IN ('submitted', 'revision_requested', 'resubmitted', 'approved')", name='ck_visit_event_action'))
    op.create_index('ix_visit_events_visit_id', 'visit_events', ['visit_id'])


def downgrade():
    raise RuntimeError('Review history requires a reviewed forward recovery plan')
