"""add applied_promotion_ids to cart_items

Revision ID: 002
Revises: 001
Create Date: 2026-05-28

"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cart_items",
        sa.Column("applied_promotion_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cart_items", "applied_promotion_ids")
