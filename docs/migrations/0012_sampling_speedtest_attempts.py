"""REVIEW DRAFT: point-scoped attempts; existing measurements remain untouched."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = '0012_sampling_speedtest_attempts'
down_revision = '0011_sampling_observations'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('sampling_speedtest_attempts',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('sampling_sessions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('network_speedtests.id', ondelete='RESTRICT'), unique=True),
        sa.Column('actor_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('failure_reason', sa.Text()), sa.Column('request_payload', JSONB(), nullable=False),
        sa.CheckConstraint("(run_id IS NOT NULL AND failure_reason IS NULL) OR "
            "(run_id IS NULL AND failure_reason IS NOT NULL AND length(trim(failure_reason)) > 0)", name='ck_sampling_speedtest_evidence'))
    op.create_index('ix_sampling_speedtest_attempts_session_id', 'sampling_speedtest_attempts', ['session_id'])
    op.create_index('ix_sampling_speedtest_attempts_actor_id', 'sampling_speedtest_attempts', ['actor_id'])


def downgrade():
    raise RuntimeError('Sampling test history requires reviewed forward recovery')
