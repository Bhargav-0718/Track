"""
UserFoodItem request/response schemas.
"""
from uuid import UUID

from pydantic import Field

from app.schemas.common import TrackBaseSchema


class UserFoodItemResponse(TrackBaseSchema):
    """A saved personal food portion."""
    id: UUID
    food_name: str
    display_name: str
    unit_label: str
    portion_description: str
    calories: float
    portion_grams: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    use_count: int


class UserFoodItemUpsert(TrackBaseSchema):
    """Body for PUT /api/v1/food-items/ — creates or updates a saved portion.

    A portion is uniquely identified by (food_name, unit_label) for the user —
    upserting with the same pair updates the existing entry.
    """
    food_name: str = Field(min_length=1, max_length=100)
    unit_label: str = Field(min_length=1, max_length=50)
    portion_description: str = Field(min_length=1, max_length=150)
    calories: float = Field(ge=0, le=10000)
    portion_grams: float | None = Field(default=None, ge=0, le=5000)
    protein_g: float | None = Field(default=None, ge=0, le=1000)
    carbs_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=1000)
    fiber_g: float | None = Field(default=None, ge=0, le=1000)
