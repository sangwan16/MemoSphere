from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.database import get_db
from app.models.like import Like
from app.models.notification import Notification
from app.models.post import Post
from app.models.user import User
from app.schemas.like import LikeRead

router = APIRouter(prefix="/posts", tags=["likes"])


@router.post("/{post_id}/like", response_model=LikeRead, status_code=status.HTTP_201_CREATED)
async def like_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LikeRead:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = await db.scalar(
        select(Like).where(Like.user_id == current_user.id, Like.post_id == post_id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Post already liked")

    like = Like(user_id=current_user.id, post_id=post_id)
    db.add(like)

    notification = Notification(
        user_id=post.author_id,
        actor_id=current_user.id,
        type="like",
        reference_id=post_id,
        message=f"{current_user.email} liked your post",
        is_read=False,
    )
    db.add(notification)

    await db.commit()
    await db.refresh(like)

    return LikeRead(
        id=like.id,
        user_id=like.user_id,
        post_id=like.post_id,
        created_at=like.created_at,
    )


@router.delete("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def unlike_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    like = await db.scalar(
        select(Like).where(Like.user_id == current_user.id, Like.post_id == post_id)
    )
    if like is None:
        raise HTTPException(status_code=404, detail="Like not found")

    await db.delete(like)
    await db.commit()
