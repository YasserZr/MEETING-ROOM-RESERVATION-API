"""Add server_default to created_at column"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '<timestamp>'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None


def upgrade():
    # Add server_default to the created_at column
    op.alter_column('user', 'created_at',
                    existing_type=sa.TIMESTAMP(),
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    existing_nullable=False)


def downgrade():
    # Remove the server_default from the created_at column
    op.alter_column('user', 'created_at',
                    existing_type=sa.TIMESTAMP(),
                    server_default=None,
                    existing_nullable=False)
