"""Add optional self-managed contact details; no existing rows are rewritten."""
from alembic import op
import sqlalchemy as sa

revision = '0014_user_contact_profile'
down_revision = '0013_phone_network_runs'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('contact_profile', sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError('Contact profiles must be retained; use reviewed forward recovery')
