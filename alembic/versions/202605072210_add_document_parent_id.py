"""Add document parent hierarchy.

Revision ID: 202605072210
Revises: 202605071235
Create Date: 2026-05-07 22:10:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202605072210"
down_revision: str | None = "202605071235"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("parent_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_documents_parent_id_documents",
        "documents",
        "documents",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_documents_parent_id", "documents", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_parent_id", table_name="documents")
    op.drop_constraint("fk_documents_parent_id_documents", "documents", type_="foreignkey")
    op.drop_column("documents", "parent_id")
