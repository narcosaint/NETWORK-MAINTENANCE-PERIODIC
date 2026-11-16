"""Immutable checklists and submitted visits. No seed data."""
from alembic import op
import sqlalchemy as sa

revision = '0004_checklists'
down_revision = '0003_visits'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('checklist_templates',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('device_type', sa.String(20), nullable=False),
        sa.CheckConstraint("device_type IN ('router', 'switch', 'ap')", name='ck_template_device_type'))
    op.create_table('checklist_items',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('template_id', sa.Uuid(), sa.ForeignKey('checklist_templates.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(200), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('template_id', 'position', name='uq_checklist_position'))
    op.create_index('ix_checklist_items_template_id', 'checklist_items', ['template_id'])
    op.add_column('visits', sa.Column('template_id', sa.Uuid()))
    op.create_foreign_key('fk_visit_template', 'visits', 'checklist_templates', ['template_id'], ['id'], ondelete='RESTRICT')
    for name in ('checked_out_at', 'checkout_device_time'):
        op.add_column('visits', sa.Column(name, sa.DateTime(timezone=True)))
    for name in ('checkout_latitude', 'checkout_longitude', 'checkout_accuracy_m'):
        op.add_column('visits', sa.Column(name, sa.Float()))
    for name in ('checkout_gps_exception_reason', 'pic_exception_reason'):
        op.add_column('visits', sa.Column(name, sa.Text()))
    op.drop_constraint('ck_visit_status', 'visits', type_='check')
    op.drop_constraint('ck_visit_checkin', 'visits', type_='check')
    op.create_check_constraint('ck_visit_status', 'visits', "status IN ('assigned', 'in_progress', 'submitted')")
    op.create_check_constraint('ck_visit_checkin', 'visits', "(status = 'assigned' AND checked_in_at IS NULL) OR (status IN ('in_progress', 'submitted') AND checked_in_at IS NOT NULL)")
    op.create_check_constraint('ck_visit_checkout', 'visits', "(status = 'submitted' AND checked_out_at IS NOT NULL AND pic_exception_reason IS NOT NULL) OR (status <> 'submitted' AND checked_out_at IS NULL)")
    op.create_table('checklist_results',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('visit_id', sa.Uuid(), sa.ForeignKey('visits.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('item_id', sa.Uuid(), sa.ForeignKey('checklist_items.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('answer', sa.String(20), nullable=False),
        sa.Column('notes', sa.Text()),
        sa.UniqueConstraint('visit_id', 'item_id', name='uq_checklist_visit_item'),
        sa.CheckConstraint("answer IN ('pass', 'fail', 'not_applicable')", name='ck_checklist_answer'))
    op.create_index('ix_checklist_results_visit_id', 'checklist_results', ['visit_id'])


def downgrade():
    # Do not silently discard submitted visits or maintenance evidence.
    raise RuntimeError('Evidence migration requires a reviewed forward recovery plan')
