"""Increase password column length in user table"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '<timestamp>'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None


def upgrade():
    # Increase the length of the password column to 256 characters
    op.alter_column('user', 'password',
                    existing_type=sa.VARCHAR(length=128),
                    type_=sa.VARCHAR(length=256),
                    existing_nullable=False)


def downgrade():
    # Revert the password column length back to 128 characters
    op.alter_column('user', 'password',
                    existing_type=sa.VARCHAR(length=256),
                    type_=sa.VARCHAR(length=128),
                    existing_nullable=False)
