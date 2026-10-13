from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.database import get_db
from app.models.bookmark import Bookmark
from app.models.post import Post
from app.models.user import User
from app.schemas.bookmark import BookmarkRead

router = APIRouter(prefix="/posts", tags=["bookmarks"])


@router.post("/{post_id}/bookmark", response_model=BookmarkRead, status_code=status.HTTP_201_CREATED)
async def bookmark_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BookmarkRead:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = await db.scalar(
        select(Bookmark).where(Bookmark.user_id == current_user.id, Bookmark.post_id == post_id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Post already bookmarked")

    bookmark = Bookmark(user_id=current_user.id, post_id=post_id)
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)

    return BookmarkRead(
        id=bookmark.id,
        user_id=bookmark.user_id,
        post_id=bookmark.post_id,
        created_at=bookmark.created_at,
    )


@router.delete("/{post_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    bookmark = await db.scalar(
        select(Bookmark).where(Bookmark.user_id == current_user.id, Bookmark.post_id == post_id)
    )
    if bookmark is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.delete(bookmark)
    await db.commit()
