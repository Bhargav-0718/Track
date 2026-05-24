"""Phase 1: Initial schema — all base tables

Revision ID: phase1_initial_schema
Revises:
Create Date: 2026-05-24 00:00:00

Creates:
  - users
  - user_preferences
  - nutrition_cache
  - food_memory   (with vector(1536) column)
  - food_logs     (with vector(1536) column)
  - workout_logs  (with vector(1536) column)
  - daily_summaries
  - correction_events
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision: str = "phase1_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ──────────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ── update_updated_at_column() trigger function ────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("height_cm", sa.Float, nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("activity_level", sa.String(20), nullable=False, server_default="moderate"),
        sa.Column("goal", sa.String(30), nullable=False, server_default="maintain"),
        sa.Column("target_calories", sa.Float, nullable=True),
        sa.Column("target_protein_g", sa.Float, nullable=True),
        sa.Column("target_carbs_g", sa.Float, nullable=True),
        sa.Column("target_fat_g", sa.Float, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.execute("""
        CREATE TRIGGER trg_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    # Functional index for case-insensitive email lookup
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_email_lower ON users (lower(email))
    """)

    # ── user_preferences ───────────────────────────────────────────────────────
    op.create_table(
        "user_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, unique=True, index=True),
        sa.Column("dietary_restrictions", ARRAY(sa.String), nullable=False,
                  server_default="{}"),
        sa.Column("cuisine_preferences", ARRAY(sa.String), nullable=False,
                  server_default="{}"),
        sa.Column("disliked_foods", ARRAY(sa.String), nullable=False,
                  server_default="{}"),
        sa.Column("logging_reminders", JSONB, nullable=False, server_default="{}"),
        sa.Column("reminders_enabled", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("default_meal_view", sa.String(20), nullable=False,
                  server_default="daily"),
        sa.Column("show_macros", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("calorie_display_format", sa.String(20), nullable=False,
                  server_default="rounded"),
        # Phase 4 report preferences
        sa.Column("preferred_report_style", sa.String(20), nullable=False,
                  server_default="motivational"),
        sa.Column("report_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("report_generation_time", sa.String(10), nullable=False,
                  server_default="21:00"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.execute("""
        CREATE TRIGGER trg_user_preferences_updated_at
        BEFORE UPDATE ON user_preferences
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # ── nutrition_cache ────────────────────────────────────────────────────────
    op.create_table(
        "nutrition_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="usda"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("food_name", sa.String(255), nullable=False, index=True),
        sa.Column("calories_per_100g", sa.Float, nullable=False),
        sa.Column("protein_per_100g", sa.Float, nullable=True),
        sa.Column("carbs_per_100g", sa.Float, nullable=True),
        sa.Column("fat_per_100g", sa.Float, nullable=True),
        sa.Column("fiber_per_100g", sa.Float, nullable=True),
        sa.Column("sodium_per_100g", sa.Float, nullable=True),
        sa.Column("sugar_per_100g", sa.Float, nullable=True),
        sa.Column("raw_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source", "external_id",
                            name="uq_nutrition_cache_source_id"),
    )
    op.execute("""
        CREATE TRIGGER trg_nutrition_cache_updated_at
        BEFORE UPDATE ON nutrition_cache
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # ── food_memory ────────────────────────────────────────────────────────────
    op.create_table(
        "food_memory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("aliases", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("avg_calories", sa.Float, nullable=False),
        sa.Column("avg_portion_grams", sa.Float, nullable=True),
        sa.Column("avg_protein_g", sa.Float, nullable=True),
        sa.Column("avg_carbs_g", sa.Float, nullable=True),
        sa.Column("avg_fat_g", sa.Float, nullable=True),
        sa.Column("log_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("correction_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_logged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.5"),
        # vector(1536) for semantic similarity search
        sa.Column("embedding", sa.Text, nullable=True),   # placeholder; real type set below
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "canonical_name",
                            name="uq_food_memory_user_food"),
    )
    # Replace placeholder text column with real vector column
    op.execute("ALTER TABLE food_memory DROP COLUMN embedding")
    op.execute("ALTER TABLE food_memory ADD COLUMN embedding vector(1536)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_food_memory_last_logged
        ON food_memory (user_id, last_logged_at)
    """)
    op.execute("""
        CREATE TRIGGER trg_food_memory_updated_at
        BEFORE UPDATE ON food_memory
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # ── food_logs ──────────────────────────────────────────────────────────────
    op.create_table(
        "food_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("nutrition_cache_id", UUID(as_uuid=True),
                  sa.ForeignKey("nutrition_cache.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("memory_id", UUID(as_uuid=True),
                  sa.ForeignKey("food_memory.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("raw_input", sa.Text, nullable=True),
        sa.Column("meal_type", sa.String(20), nullable=False, server_default="snack"),
        sa.Column("food_name", sa.String(255), nullable=False),
        sa.Column("brand_name", sa.String(255), nullable=True),
        sa.Column("portion_description", sa.String(255), nullable=True),
        sa.Column("portion_grams", sa.Float, nullable=True),
        sa.Column("calories", sa.Float, nullable=False),
        sa.Column("protein_g", sa.Float, nullable=True),
        sa.Column("carbs_g", sa.Float, nullable=True),
        sa.Column("fat_g", sa.Float, nullable=True),
        sa.Column("fiber_g", sa.Float, nullable=True),
        sa.Column("estimation_source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("confidence_level", sa.String(20), nullable=False, server_default="confirmed"),
        sa.Column("assumptions", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_corrected", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("original_calories", sa.Float, nullable=True),
        sa.Column("original_portion_grams", sa.Float, nullable=True),
        sa.Column("image_url", sa.Text, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False,
                  server_default="false", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.execute("ALTER TABLE food_logs ADD COLUMN embedding vector(1536)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_food_logs_user_date
        ON food_logs (user_id, logged_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_food_logs_user_meal_type
        ON food_logs (user_id, meal_type)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_food_logs_estimation_source
        ON food_logs (estimation_source)
    """)
    op.execute("""
        CREATE TRIGGER trg_food_logs_updated_at
        BEFORE UPDATE ON food_logs
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # ── workout_logs ───────────────────────────────────────────────────────────
    op.create_table(
        "workout_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("logged_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("workout_type", sa.String(20), nullable=False, server_default="other"),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("intensity", sa.String(20), nullable=False, server_default="moderate"),
        sa.Column("calories_burned", sa.Float, nullable=True),
        sa.Column("calories_source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("exercises", JSONB, nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("raw_input", sa.Text, nullable=True),
        sa.Column("health_connect_id", sa.String(255), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False,
                  server_default="false", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.execute("ALTER TABLE workout_logs ADD COLUMN embedding vector(1536)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_workout_logs_user_date
        ON workout_logs (user_id, logged_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_workout_logs_user_type
        ON workout_logs (user_id, workout_type)
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_workout_logs_health_connect_id
        ON workout_logs (health_connect_id)
        WHERE health_connect_id IS NOT NULL
    """)
    op.execute("""
        CREATE TRIGGER trg_workout_logs_updated_at
        BEFORE UPDATE ON workout_logs
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # ── daily_summaries ────────────────────────────────────────────────────────
    op.create_table(
        "daily_summaries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("total_calories_in", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_protein_g", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_carbs_g", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_fat_g", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_fiber_g", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("food_log_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_calories_out", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("workout_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("steps", sa.Integer, nullable=True),
        sa.Column("active_minutes", sa.Integer, nullable=True),
        sa.Column("activity_calories", sa.Float, nullable=True),
        sa.Column("net_calories", sa.Float, nullable=True),
        sa.Column("health_connect_synced", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_summary_user_date"),
    )
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_daily_summaries_user_date
        ON daily_summaries (user_id, date)
    """)
    op.execute("""
        CREATE TRIGGER trg_daily_summaries_updated_at
        BEFORE UPDATE ON daily_summaries
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # ── correction_events ──────────────────────────────────────────────────────
    op.create_table(
        "correction_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("food_log_id", UUID(as_uuid=True),
                  sa.ForeignKey("food_logs.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        sa.Column("correction_type", sa.String(20), nullable=False),
        sa.Column("original_value", sa.Float, nullable=True),
        sa.Column("corrected_value", sa.Float, nullable=True),
        sa.Column("delta", sa.Float, nullable=True),
        sa.Column("original_text", sa.String(255), nullable=True),
        sa.Column("corrected_text", sa.String(255), nullable=True),
        sa.Column("original_estimation_source", sa.String(20), nullable=True),
        sa.Column("original_confidence_score", sa.Float, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_correction_events_user_created
        ON correction_events (user_id, created_at)
    """)


def downgrade() -> None:
    op.drop_table("correction_events")
    op.drop_table("daily_summaries")
    op.drop_table("workout_logs")
    op.drop_table("food_logs")
    op.drop_table("food_memory")
    op.drop_table("nutrition_cache")
    op.drop_table("user_preferences")
    op.drop_table("users")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
