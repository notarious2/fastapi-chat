"""Add type and file fields to Message

Revision ID: 0005
Revises: 0004
Create Date: 2024-01-17 08:09:18.011913

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    messagetype_enum = sa.Enum("TEXT", "FILE", name="messagetype", schema="chat", inherit_schema=True)
    messagetype_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "message", sa.Column("message_type", messagetype_enum, nullable=False, server_default="TEXT"), schema="chat"
    )
    op.add_column("message", sa.Column("file_name", sa.String(length=50), nullable=True), schema="chat")
    op.add_column("message", sa.Column("file_path", sa.String(length=1000), nullable=True), schema="chat")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("message", "file_path", schema="chat")
    op.drop_column("message", "file_name", schema="chat")
    op.drop_column("message", "message_type", schema="chat")
    sa.Enum("TEXT", "FILE", name="messagetype", schema="chat", inherit_schema=True).drop(op.get_bind())
    # ### end Alembic commands ###
