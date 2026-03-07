"""add caregiver invites

Revision ID: 8f2d9c1b7a41
Revises: 3604ce66ff79
Create Date: 2026-03-07 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8f2d9c1b7a41"
down_revision: Union[str, None] = "3604ce66ff79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "caregiver_invites",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("invited_email", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("accepted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.UUID(), nullable=True),
        sa.Column("revoked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["accepted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_caregiver_invites_patient_email", "caregiver_invites", ["patient_id", "invited_email"])
    op.create_index("ix_caregiver_invites_expires_at", "caregiver_invites", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_caregiver_invites_expires_at", table_name="caregiver_invites")
    op.drop_index("ix_caregiver_invites_patient_email", table_name="caregiver_invites")
    op.drop_table("caregiver_invites")
