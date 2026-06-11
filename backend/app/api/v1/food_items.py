"""
User food item endpoints — a personal, per-user database of confirmed
food portions (e.g. "1 plate poha" = 400 kcal, "1 bowl poha" = 250 kcal).

Routes:
  GET    /food-items/search   → Search saved portions by name (autocomplete)
  GET    /food-items/         → List all saved portions
  PUT    /food-items/         → Create or update a saved portion
  DELETE /food-items/{id}     → Remove a saved portion
"""
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserID
from app.core.exceptions import ResourceNotFoundError
from app.repositories.user_food_item_repository import UserFoodItemRepository
from app.schemas.user_food_item import UserFoodItemResponse, UserFoodItemUpsert

router = APIRouter(prefix="/food-items", tags=["food-items"])


@router.get(
    "/search",
    response_model=list[UserFoodItemResponse],
    summary="Search saved food portions by name",
)
async def search_food_items(
    current_user_id: CurrentUserID,
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=10, ge=1, le=25),
) -> list[UserFoodItemResponse]:
    """Used for autocomplete — returns all saved portion variants matching the query
    (e.g. searching "poha" returns "1 plate poha" and "1 bowl poha" separately)."""
    repo = UserFoodItemRepository()
    items = await repo.search(current_user_id, q, limit=limit)
    return [UserFoodItemResponse.model_validate(item) for item in items]


@router.get(
    "/",
    response_model=list[UserFoodItemResponse],
    summary="List all saved food portions",
)
async def list_food_items(
    current_user_id: CurrentUserID,
) -> list[UserFoodItemResponse]:
    repo = UserFoodItemRepository()
    items = await repo.list_for_user(current_user_id)
    return [UserFoodItemResponse.model_validate(item) for item in items]


@router.put(
    "/",
    response_model=UserFoodItemResponse,
    summary="Create or update a saved food portion",
)
async def upsert_food_item(
    data: UserFoodItemUpsert,
    current_user_id: CurrentUserID,
) -> UserFoodItemResponse:
    """
    Save a confirmed portion to your personal food database.

    A portion is uniquely identified by (food_name, unit_label) — saving the
    same combination again updates the existing entry instead of duplicating it.
    """
    repo = UserFoodItemRepository()
    item = await repo.upsert(
        current_user_id,
        food_name=data.food_name,
        display_name=data.food_name,
        unit_label=data.unit_label,
        portion_description=data.portion_description,
        calories=data.calories,
        portion_grams=data.portion_grams,
        protein_g=data.protein_g,
        carbs_g=data.carbs_g,
        fat_g=data.fat_g,
        fiber_g=data.fiber_g,
    )
    return UserFoodItemResponse.model_validate(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved food portion",
)
async def delete_food_item(
    item_id: UUID,
    current_user_id: CurrentUserID,
) -> None:
    repo = UserFoodItemRepository()
    item = await repo.get_by_id_for_user(item_id, current_user_id)
    if not item:
        raise ResourceNotFoundError(
            message=f"Food item {item_id} not found",
            resource_type="UserFoodItem",
            resource_id=str(item_id),
        )
    await repo.delete(item)
