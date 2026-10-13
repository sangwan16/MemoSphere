from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.database import get_db
from app.models.category import Category
from app.models.user import User

router = APIRouter(prefix="/useful", tags=["useful"])

CATEGORIES = (
	("Poetry", "poetry"),
	("Movies", "movies"),
	("Legends", "legends"),
	("Books", "books"),
	("Miscellaneous", "miscellaneous"),
)


@router.post("/seed-categories")
async def seed_categories(
	db: Annotated[AsyncSession, Depends(get_db)],
	# current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, list[str]]:
	result = await db.execute(select(Category))
	existing_categories = result.scalars().all()
	existing_names = {category.name for category in existing_categories}
	existing_slugs = {category.slug for category in existing_categories}

	added: list[str] = []
	skipped: list[str] = []
	for name, slug in CATEGORIES:
		if name in existing_names or slug in existing_slugs:
			skipped.append(slug)
			continue

		db.add(Category(name=name, slug=slug))
		existing_names.add(name)
		existing_slugs.add(slug)
		added.append(slug)

	if added:
		await db.commit()

	return {"added": added, "already_present": skipped}
