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
from app.schemas.follow import FollowRequest, FollowUserRead, ProfileStatsRead, UserProfileRead
from app.schemas.notification import NotificationRead

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


@router.delete("/me/followers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_follower(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    follow = await db.scalar(
        select(Follow).where(
            Follow.follower_id == user_id,
            Follow.following_id == current_user.id,
        )
    )
    if follow is None:
        raise HTTPException(status_code=404, detail="Follower relationship not found")

    await db.delete(follow)
    await db.commit()


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


@router.get("/users/{user_id}", response_model=UserProfileRead)
async def get_user_profile(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserProfileRead:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    is_following = False
    has_pending_request = False
    if user.id != current_user.id:
        is_following = await db.scalar(
            select(Follow.id).where(
                Follow.follower_id == current_user.id,
                Follow.following_id == user.id,
            )
        ) is not None
        if not is_following:
            has_pending_request = await db.scalar(
                select(Notification.id).where(
                    Notification.user_id == user.id,
                    Notification.actor_id == current_user.id,
                    Notification.type == "follow_request",
                )
            ) is not None

    posts_count = await db.scalar(
        select(func.count(Post.id)).where(
            Post.author_id == user.id,
            Post.is_draft.is_(False),
        )
    )
    followers_count = await db.scalar(
        select(func.count(Follow.id)).where(Follow.following_id == user.id)
    )
    following_count = await db.scalar(
        select(func.count(Follow.id)).where(Follow.follower_id == user.id)
    )
    can_view_posts = user.id == current_user.id or is_following

    return UserProfileRead(
        id=user.id,
        username=user.username,
        is_public=user.is_public,
        is_self=user.id == current_user.id,
        is_following=is_following,
        has_pending_request=has_pending_request,
        can_view_posts=can_view_posts,
        posts_count=posts_count or 0,
        followers_count=followers_count or 0,
        following_count=following_count or 0,
    )


@router.post("/follow", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
async def follow_user(
    payload: FollowRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationRead:
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

    pending_request = await db.scalar(
        select(Notification).where(
            Notification.user_id == target_user.id,
            Notification.actor_id == current_user.id,
            Notification.type == "follow_request",
        )
    )
    if pending_request is not None:
        raise HTTPException(status_code=409, detail="Follow request is already pending")

    notification = Notification(
        user_id=target_user.id,
        actor_id=current_user.id,
        type="follow_request",
        reference_id=current_user.id,
        message=f"{current_user.username or current_user.email} requested to follow you",
        is_read=False,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return NotificationRead.model_validate(notification)


@router.post("/follow-requests/{notification_id}/accept", response_model=NotificationRead)
async def accept_follow_request(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationRead:
    notification = await db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Follow request not found")
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot accept another user's follow request")
    if notification.type != "follow_request" or notification.actor_id is None:
        raise HTTPException(status_code=409, detail="Follow request is no longer pending")

    existing_follow = await db.scalar(
        select(Follow).where(
            Follow.follower_id == notification.actor_id,
            Follow.following_id == current_user.id,
        )
    )
    if existing_follow is None:
        db.add(Follow(follower_id=notification.actor_id, following_id=current_user.id))

    notification.type = "follow_accepted"
    notification.message = f"You accepted {notification.message.removesuffix(' requested to follow you')}'s follow request"
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return NotificationRead.model_validate(notification)


@router.post("/follow-requests/{notification_id}/decline", response_model=NotificationRead)
async def decline_follow_request(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationRead:
    notification = await db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Follow request not found")
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot decline another user's follow request")
    if notification.type != "follow_request":
        raise HTTPException(status_code=409, detail="Follow request is no longer pending")

    notification.type = "follow_declined"
    notification.message = "You declined a follow request"
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return NotificationRead.model_validate(notification)


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
