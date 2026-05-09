"""use document status enum

Revision ID: 843f0780652b
Revises: 202605072210
Create Date: 2026-05-09 20:37:28.639167
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '843f0780652b'
down_revision: Union[str, None] = '202605072210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

document_status = sa.Enum("active", "archived", name="documentstatus")

def upgrade() -> None:
    document_status.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "documents",
        "status",
        existing_type=sa.String(length=32),
        type_=document_status,
        existing_nullable=False,
        postgresql_using="lower(status)::documentstatus",
    )



def downgrade() -> None:
    op.alter_column(
        "documents",
        "status",
        existing_type=document_status,
        type_=sa.String(length=32),
        existing_nullable=False,
        postgresql_using="status::text",
    )
    document_status.drop(op.get_bind(), checkfirst=True)
