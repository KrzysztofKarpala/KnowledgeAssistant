"""Add conversations.

Revision ID: 202605092115
Revises: 843f0780652b
Create Date: 2026-05-09 21:15:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202605092115"
down_revision: str | None = "843f0780652b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

conversation_status_column = postgresql.ENUM(
    "active",
    "archived",
    name="conversationstatus",
    create_type=False,
)
conversation_message_role_column = postgresql.ENUM(
    "user",
    "assistant",
    "system",
    name="conversationmessagerole",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE conversationstatus AS ENUM ('active', 'archived');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE conversationmessagerole AS ENUM ('user', 'assistant', 'system');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("status", conversation_status_column, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_status", "conversations", ["status"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", conversation_message_role_column, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("cited_chunk_ids", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_messages_conversation_id", "conversation_messages", ["conversation_id"])
    op.create_index("ix_conversation_messages_created_at", "conversation_messages", ["created_at"])
    op.create_index("ix_conversation_messages_role", "conversation_messages", ["role"])


def downgrade() -> None:
    op.drop_index("ix_conversation_messages_role", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_created_at", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_conversation_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_table("conversations")
    op.execute("DROP TYPE IF EXISTS conversationmessagerole")
    op.execute("DROP TYPE IF EXISTS conversationstatus")
