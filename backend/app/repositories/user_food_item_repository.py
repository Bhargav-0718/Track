"""
UserFoodItem repository — data access for the user_food_items collection.
"""
import re
from uuid import UUID

from app.models.user_food_item import UserFoodItem
from app.repositories.base import BaseRepository


class UserFoodItemRepository(BaseRepository[UserFoodItem]):
    def __init__(self) -> None:
        super().__init__(UserFoodItem)

    async def search(self, user_id: UUID, query: str, limit: int = 10) -> list[UserFoodItem]:
        """Case-insensitive substring search over the user's saved foods."""
        pattern = re.escape(query.strip())
        if not pattern:
            return []
        return await UserFoodItem.find(
            UserFoodItem.user_id == user_id,
            {"food_name": {"$regex": pattern, "$options": "i"}},
        ).sort(-UserFoodItem.use_count).limit(limit).to_list()

    async def find_latest_for_food(self, user_id: UUID, food_name: str) -> UserFoodItem | None:
        """Most-used saved portion for this food — used to fill in a portion the
        user didn't specify (e.g. "Roti" -> their usual "1 roti" entry)."""
        pattern = re.escape(food_name.strip())
        if not pattern:
            return None
        return await UserFoodItem.find(
            UserFoodItem.user_id == user_id,
            {"food_name": {"$regex": pattern, "$options": "i"}},
        ).sort(-UserFoodItem.use_count, -UserFoodItem.updated_at).first_or_none()

    async def find_exact(self, user_id: UUID, food_name: str, unit_label: str) -> UserFoodItem | None:
        return await UserFoodItem.find_one(
            UserFoodItem.user_id == user_id,
            UserFoodItem.food_name == food_name.strip().lower(),
            UserFoodItem.unit_label == unit_label.strip().lower(),
        )

    async def list_for_user(self, user_id: UUID, limit: int = 200) -> list[UserFoodItem]:
        return await UserFoodItem.find(
            UserFoodItem.user_id == user_id,
        ).sort(-UserFoodItem.updated_at).limit(limit).to_list()

    async def upsert(
        self,
        user_id: UUID,
        *,
        food_name: str,
        display_name: str,
        unit_label: str,
        portion_description: str,
        calories: float,
        portion_grams: float | None = None,
        protein_g: float | None = None,
        carbs_g: float | None = None,
        fat_g: float | None = None,
        fiber_g: float | None = None,
    ) -> UserFoodItem:
        existing = await self.find_exact(user_id, food_name, unit_label)
        if existing:
            existing.display_name = display_name
            existing.portion_description = portion_description
            existing.calories = calories
            existing.portion_grams = portion_grams
            existing.protein_g = protein_g
            existing.carbs_g = carbs_g
            existing.fat_g = fat_g
            existing.fiber_g = fiber_g
            existing.use_count += 1
            await existing.save_with_ts()
            return existing

        item = UserFoodItem(
            user_id=user_id,
            food_name=food_name.strip().lower(),
            display_name=display_name.strip(),
            unit_label=unit_label.strip().lower(),
            portion_description=portion_description.strip(),
            calories=calories,
            portion_grams=portion_grams,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            fiber_g=fiber_g,
        )
        await item.insert()
        return item
