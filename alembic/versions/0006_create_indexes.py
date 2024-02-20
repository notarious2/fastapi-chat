"""create indexes

Revision ID: 0006
Revises: 0005
Create Date: 2024-02-20 23:11:06.364557

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("COMMIT")
    # chat participant

    # chat
    op.create_index(
        index_name="idx_chat_on_is_deleted_chat_type_updated_at",
        table_name="chat",
        schema="chat",
        columns=["is_deleted", "chat_type", "updated_at"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )

    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_partial_on_updated_at ON chat.chat (updated_at DESC)
        WHERE is_deleted IS FALSE AND chat_type = 'DIRECT';
    """
    )

    op.create_index(
        index_name="idx_chat_on_guid",
        table_name="chat",
        schema="chat",
        columns=["guid"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )

    op.create_index(
        index_name="idx_chat_on_chat_type_is_deleted",
        table_name="chat",
        schema="chat",
        columns=["chat_type", "is_deleted"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )

    # user
    op.create_index(
        index_name="idx_user_on_email_username",
        table_name="user",
        schema="chat",
        columns=["email", "username"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )

    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_partial_on_email_not_deleted ON chat.user (email)
        WHERE is_deleted IS FALSE;
    """
    )

    # read status
    op.create_index(
        index_name="idx_read_status_on_chat_id",
        table_name="read_status",
        schema="chat",
        columns=["chat_id"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )

    op.create_index(
        index_name="idx_read_status_on_user_id",
        table_name="read_status",
        schema="chat",
        columns=["user_id"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )

    op.create_index(
        index_name="idx_read_status_on_user_id_chat_id",
        table_name="read_status",
        schema="chat",
        columns=["user_id", "chat_id"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )

    # message
    op.create_index(
        index_name="idx_message_on_chat_id",
        table_name="message",
        schema="chat",
        columns=["chat_id"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )

    op.create_index(
        index_name="idx_message_on_user_id",
        table_name="message",
        schema="chat",
        columns=["user_id"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )

    op.create_index(
        index_name="idx_message_on_user_id_chat_id",
        table_name="message",
        schema="chat",
        columns=["user_id", "chat_id"],
        if_not_exists=True,
        postgresql_concurrently=True,
    )


def downgrade() -> None:
    op.drop_index("idx_chat_on_is_deleted_chat_type_updated_at", schema="chat", if_exists=True)
    op.drop_index("idx_chat_on_guid", schema="chat", if_exists=True)
    op.drop_index("idx_chat_on_chat_type_is_deleted", schema="chat", if_exists=True)
    op.drop_index("idx_chat_partial_on_updated_at", schema="chat", if_exists=True)
    op.drop_index("idx_message_on_chat_id", schema="chat", if_exists=True)
    op.drop_index("idx_message_on_user_id", schema="chat", if_exists=True)
    op.drop_index("idx_message_on_user_id_chat_id", schema="chat", if_exists=True)
    op.drop_index("idx_read_status_on_chat_id", schema="chat", if_exists=True)
    op.drop_index("idx_read_status_on_user_id_chat_id", schema="chat", if_exists=True)
    op.drop_index("idx_user_on_email_username", schema="chat", if_exists=True)
    op.drop_index("idx_user_partial_on_email_not_deleted", schema="chat", if_exists=True)
