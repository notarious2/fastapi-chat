"""increase user image text length

Revision ID: 0003
Revises: 0002
Create Date: 2023-12-27 17:57:32.554642

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "user",
        "user_image",
        existing_type=sa.VARCHAR(length=128),
        type_=sa.String(length=1000),
        existing_nullable=True,
        schema="chat",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "user",
        "user_image",
        existing_type=sa.String(length=1000),
        type_=sa.VARCHAR(length=128),
        existing_nullable=True,
        schema="chat",
    )
    # ### end Alembic commands ###
