"""Optional site identity/bandwidth policy; no guessed defaults or report rewrite."""
from alembic import op
import sqlalchemy as sa
revision = '0009_site_report_profile'
down_revision = '0008_network_speedtests'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('hotels', sa.Column('customer_name', sa.String(200), nullable=True))
    op.add_column('hotels', sa.Column('maintenance_profile', sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError('Site maintenance profiles require reviewed forward recovery')
