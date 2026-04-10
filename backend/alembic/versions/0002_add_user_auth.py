"""add user auth

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-09 00:00:00.000000

Changes
-------
- Create ``users`` table with email / username / hashed_password / is_active
- Add nullable ``user_id`` FK column to ``watchlists``
- Add nullable ``user_id`` FK column to ``portfolios``

The FK columns are nullable so that existing rows created before the auth
system are not broken.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # --- watchlists: add user_id ---------------------------------------------
    op.add_column(
        "watchlists",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_watchlists_user_id",
        "watchlists",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])

    # --- portfolios: add user_id ---------------------------------------------
    op.add_column(
        "portfolios",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_portfolios_user_id",
        "portfolios",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])


def downgrade() -> None:
    # --- portfolios ----------------------------------------------------------
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_constraint("fk_portfolios_user_id", "portfolios", type_="foreignkey")
    op.drop_column("portfolios", "user_id")

    # --- watchlists ----------------------------------------------------------
    op.drop_index("ix_watchlists_user_id", table_name="watchlists")
    op.drop_constraint("fk_watchlists_user_id", "watchlists", type_="foreignkey")
    op.drop_column("watchlists", "user_id")

    # --- users ---------------------------------------------------------------
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
