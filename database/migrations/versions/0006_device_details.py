"""Optional physical/network inventory details; preserve all existing records."""
from alembic import op
import sqlalchemy as sa

revision = '0006_device_details'
down_revision = '0005_reviews'
branch_labels = None
depends_on = None


def upgrade():
    for name, length in [('brand', 100), ('model', 100), ('location', 200), ('ip_address', 45), ('mac_address', 17)]:
        op.add_column('devices', sa.Column(name, sa.String(length), nullable=True))
    op.add_column('devices', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    raise RuntimeError('Inventory details require a reviewed forward recovery plan')
