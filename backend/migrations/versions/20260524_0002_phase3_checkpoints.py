"""Phase 3: Progress checkpoints and photo management

Revision ID: phase3_checkpoints
Revises: phase2_search_indexes
Create Date: 2026-05-24 00:00:01

Changes:
- progress_checkpoints table (date, weight, body fat, notes, tags)
- progress_photos table (storage_key, dimensions, display_order)
- Indexes for checkpoint date queries and photo ordering
- Storage config columns in config (no DB changes needed — config.py only)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "phase3_checkpoints"
down_revision: Union[str, None] = "phase2_search_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── progress_checkpoints ───────────────────────────────────────────────────
    op.create_table(
        "progress_checkpoints",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_date", sa.Date(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("body_fat_percentage", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(50)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )

    op.create_index(
        "ix_progress_checkpoints_user_date",
        "progress_checkpoints",
        ["user_id", "checkpoint_date"],
    )
    op.create_index(
        "ix_progress_checkpoints_id",
        "progress_checkpoints",
        ["id"],
    )
    op.create_index(
        "ix_progress_checkpoints_is_deleted",
        "progress_checkpoints",
        ["is_deleted"],
    )

    # ── progress_photos ────────────────────────────────────────────────────────
    op.create_table(
        "progress_photos",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column(
            "content_type",
            sa.String(50),
            server_default="image/jpeg",
            nullable=False,
        ),
        sa.Column("file_size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("width_px", sa.Integer(), server_default="0", nullable=False),
        sa.Column("height_px", sa.Integer(), server_default="0", nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("label", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["checkpoint_id"], ["progress_checkpoints.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )

    op.create_index(
        "ix_progress_photos_checkpoint",
        "progress_photos",
        ["checkpoint_id", "display_order"],
    )
    op.create_index(
        "ix_progress_photos_user",
        "progress_photos",
        ["user_id"],
    )
    op.create_index(
        "ix_progress_photos_id",
        "progress_photos",
        ["id"],
    )

    # Updated_at trigger for progress_checkpoints
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)

    op.execute("""
        CREATE TRIGGER update_progress_checkpoints_updated_at
        BEFORE UPDATE ON progress_checkpoints
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS update_progress_checkpoints_updated_at "
        "ON progress_checkpoints"
    )
    op.drop_table("progress_photos")
    op.drop_table("progress_checkpoints")
