from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.database import get_db
from app.models.follow import Follow
from app.models.notification import Notification
from app.models.post import Post
from app.models.user import User
from app.schemas.follow import FollowRead, FollowRequest, FollowUserRead, ProfileStatsRead

router = APIRouter(prefix="/social", tags=["social"])


@router.get("/me", response_model=ProfileStatsRead)
async def get_my_profile_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProfileStatsRead:
    posts_count = await db.scalar(
        select(func.count(Post.id)).where(
            Post.author_id == current_user.id,
            Post.is_draft.is_(False),
        )
    )
    followers_count = await db.scalar(
        select(func.count(Follow.id)).where(Follow.following_id == current_user.id)
    )
    following_count = await db.scalar(
        select(func.count(Follow.id)).where(Follow.follower_id == current_user.id)
    )
    return ProfileStatsRead(
        posts_count=posts_count or 0,
        followers_count=followers_count or 0,
        following_count=following_count or 0,
    )


@router.get("/me/followers", response_model=list[FollowUserRead])
async def list_my_followers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[FollowUserRead]:
    result = await db.execute(
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.following_id == current_user.id)
        .order_by(Follow.created_at.desc())
    )
    return [FollowUserRead.model_validate(user) for user in result.scalars().all()]


@router.get("/me/following", response_model=list[FollowUserRead])
async def list_my_following(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[FollowUserRead]:
    result = await db.execute(
        select(User)
        .join(Follow, Follow.following_id == User.id)
        .where(Follow.follower_id == current_user.id)
        .order_by(Follow.created_at.desc())
    )
    return [FollowUserRead.model_validate(user) for user in result.scalars().all()]


@router.post("/follow", response_model=FollowRead, status_code=status.HTTP_201_CREATED)
async def follow_user(
    payload: FollowRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FollowRead:
    if payload.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    target_user = await db.get(User, payload.user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await db.scalar(
        select(Follow).where(
            Follow.follower_id == current_user.id,
            Follow.following_id == payload.user_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Already following this user")

    follow = Follow(follower_id=current_user.id, following_id=payload.user_id)
    db.add(follow)

    notification = Notification(
        user_id=payload.user_id,
        actor_id=current_user.id,
        type="follow",
        reference_id=current_user.id,
        message=f"{current_user.email} followed you",
        is_read=False,
    )
    db.add(notification)

    await db.commit()
    await db.refresh(follow)

    return FollowRead(
        follower_id=follow.follower_id,
        following_id=follow.following_id,
        created_at=follow.created_at,
    )


@router.delete("/follow/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    follow = await db.scalar(
        select(Follow).where(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id,
        )
    )
    if follow is None:
        raise HTTPException(status_code=404, detail="Follow relationship not found")

    await db.delete(follow)
    await db.commit()
