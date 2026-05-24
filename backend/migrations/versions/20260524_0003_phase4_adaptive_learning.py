"""Phase 4: Adaptive learning — daily reports, behavior events, report preferences

Revision ID: phase4_adaptive_learning
Revises: phase3_checkpoints
Create Date: 2026-05-24 00:00:02

Changes:
- daily_reports table (AI-generated nightly summaries)
- behavior_events table (lightweight engagement tracking)
- user_preferences: add preferred_report_style, report_enabled, report_generation_time

Why separate behavior_events from daily_reports:
- Reports are generated once per day (batch)
- Events are recorded in real-time (each UI interaction)
- Keeping them separate avoids heavy JSONB arrays that grow unboundedly
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "phase4_adaptive_learning"
down_revision: Union[str, None] = "phase3_checkpoints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── daily_reports ──────────────────────────────────────────────────────────
    op.create_table(
        "daily_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("calorie_summary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("workout_summary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("macro_summary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("consistency_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("streak_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("weekly_consistency", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("insights_text", sa.Text(), nullable=True),
        sa.Column("motivation_message", sa.Text(), nullable=True),
        sa.Column(
            "behavioral_observations",
            postgresql.JSONB(),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "report_style",
            sa.String(20),
            server_default="motivational",
            nullable=False,
        ),
        sa.Column(
            "generation_model",
            sa.String(50),
            server_default="gpt-4o-mini",
            nullable=False,
        ),
        sa.Column("was_shown", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_rating", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "report_date", name="uq_daily_reports_user_date"),
    )

    op.create_index("ix_daily_reports_user_date", "daily_reports", ["user_id", "report_date"])
    op.create_index("ix_daily_reports_id", "daily_reports", ["id"])

    # ── behavior_events ────────────────────────────────────────────────────────
    op.create_table(
        "behavior_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_index(
        "ix_behavior_events_user_type",
        "behavior_events",
        ["user_id", "event_type"],
    )
    op.create_index(
        "ix_behavior_events_user_created",
        "behavior_events",
        ["user_id", "created_at"],
    )
    op.create_index("ix_behavior_events_id", "behavior_events", ["id"])

    # NOTE: preferred_report_style, report_enabled, report_generation_time are
    # already created in phase1_initial_schema — no ALTER TABLE needed here.

    # Updated_at trigger for daily_reports
    op.execute("""
        CREATE TRIGGER update_daily_reports_updated_at
        BEFORE UPDATE ON daily_reports
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    op.execute("""
        CREATE TRIGGER update_behavior_events_updated_at
        BEFORE UPDATE ON behavior_events
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_daily_reports_updated_at ON daily_reports")
    op.execute("DROP TRIGGER IF EXISTS update_behavior_events_updated_at ON behavior_events")
    # preference columns were created in phase1 — do not drop them here
    op.drop_table("behavior_events")
    op.drop_table("daily_reports")
