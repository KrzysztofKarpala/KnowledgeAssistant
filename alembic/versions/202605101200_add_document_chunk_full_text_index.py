"""add document chunk full text index

Revision ID: 202605101200
Revises: 202605092115
Create Date: 2026-05-10 12:00:00
"""

from typing import Sequence

from alembic import op

revision: str = "202605101200"
down_revision: str | None = "202605092115"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_content_tsv
        ON document_chunks
        USING gin (to_tsvector('english', content));
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_tsv")
