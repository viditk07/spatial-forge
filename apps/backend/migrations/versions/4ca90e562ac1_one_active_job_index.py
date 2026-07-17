"""enforce one active reconstruction per project

Revision ID: 4ca90e562ac1
Revises: fc981325bccf
Create Date: 2026-07-17 14:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "4ca90e562ac1"
down_revision = "fc981325bccf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("reconstruction_jobs", schema=None) as batch_op:
        batch_op.create_index(
            "uq_jobs_one_active_per_project",
            ["project_id"],
            unique=True,
            sqlite_where=sa.text("status IN ('queued', 'processing')"),
        )


def downgrade() -> None:
    with op.batch_alter_table("reconstruction_jobs", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_jobs_one_active_per_project",
            sqlite_where=sa.text("status IN ('queued', 'processing')"),
        )
