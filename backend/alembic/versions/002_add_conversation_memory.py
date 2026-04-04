"""Add conversation memory persistence tables

Revision ID: 002_add_conversation_memory
Revises: 001_create_initial_schema
Create Date: 2026-04-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "002_add_conversation_memory"
down_revision: Union[str, None] = "001_create_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("conversation_sessions"):
        op.create_table(
            "conversation_sessions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("session_id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("last_activity_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "session_id", name="uq_conversation_session_user_session"),
        )
        op.create_index("idx_conversation_session_user_activity", "conversation_sessions", ["user_id", "last_activity_at"])

    if not inspector.has_table("conversation_turns"):
        role_enum = sa.Enum("user", "assistant", "system", name="conversationturnrole")
        role_enum.create(op.get_bind(), checkfirst=True)

        op.create_table(
            "conversation_turns",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("conversation_session_id", sa.String(length=36), nullable=False),
            sa.Column("session_id", sa.String(length=36), nullable=False),
            sa.Column("role", role_enum, nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("assistant_summary", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("trace_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_session_id"], ["conversation_sessions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_conversation_turn_user_created", "conversation_turns", ["user_id", "created_at"])
        op.create_index("idx_conversation_turn_session_created", "conversation_turns", ["session_id", "created_at"])
        op.create_index("idx_conversation_turn_created", "conversation_turns", ["created_at"])
        op.create_index("ix_conversation_turns_trace_id", "conversation_turns", ["trace_id"])

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "last_session_id" not in columns:
        op.add_column("users", sa.Column("last_session_id", sa.String(length=36), nullable=True))
        op.create_index("ix_users_last_session_id", "users", ["last_session_id"])

    if "last_user_message_at" not in columns:
        op.add_column("users", sa.Column("last_user_message_at", sa.DateTime(), nullable=True))

    if "last_turn_id" not in columns:
        op.add_column("users", sa.Column("last_turn_id", sa.String(length=36), nullable=True))
        op.create_index("ix_users_last_turn_id", "users", ["last_turn_id"])


def downgrade() -> None:
    op.drop_index("ix_users_last_turn_id", table_name="users")
    op.drop_column("users", "last_turn_id")

    op.drop_column("users", "last_user_message_at")

    op.drop_index("ix_users_last_session_id", table_name="users")
    op.drop_column("users", "last_session_id")

    op.drop_index("ix_conversation_turns_trace_id", table_name="conversation_turns")
    op.drop_index("idx_conversation_turn_created", table_name="conversation_turns")
    op.drop_index("idx_conversation_turn_session_created", table_name="conversation_turns")
    op.drop_index("idx_conversation_turn_user_created", table_name="conversation_turns")
    op.drop_table("conversation_turns")

    op.drop_index("idx_conversation_session_user_activity", table_name="conversation_sessions")
    op.drop_table("conversation_sessions")

    role_enum = sa.Enum("user", "assistant", "system", name="conversationturnrole")
    role_enum.drop(op.get_bind(), checkfirst=True)
