"""REVIEW DRAFT: append-only observations. Not an active Alembic revision."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0011_sampling_observations'
down_revision = '0010_sampling_foundation'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('sampling_observations',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('sampling_sessions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('session_version', sa.Integer(), nullable=False),
        sa.Column('visit_version', sa.Integer(), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('payload', JSONB(), nullable=False),
        sa.UniqueConstraint('session_id', 'session_version', name='uq_observation_session_version'),
        sa.CheckConstraint('session_version >= 2', name='ck_observation_session_version'),
        sa.CheckConstraint('visit_version >= 1', name='ck_observation_visit_version'))
    op.create_index('ix_sampling_observations_actor_id', 'sampling_observations', ['actor_id'])


def downgrade():
    raise RuntimeError('Observation history requires reviewed forward recovery')
