from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.database import get_db
from app.models.follow import Follow
from app.models.notification import Notification
from app.models.post import Post
from app.models.share import Share
from app.models.user import User
from app.schemas.share import ShareBatchRead, ShareCreate
from app.utils.post_access import post_access_filter

router = APIRouter(prefix="/posts", tags=["shares"])


@router.post(
    "/{post_id}/share",
    response_model=ShareBatchRead,
    status_code=status.HTTP_201_CREATED,
)
async def share_post(
    post_id: int,
    payload: ShareCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ShareBatchRead:
    post = await db.scalar(
        select(Post)
        .join(User, User.id == Post.author_id)
        .where(
            Post.id == post_id,
            Post.is_draft.is_(False),
            post_access_filter(current_user.id),
        )
    )
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    follower_result = await db.execute(
        select(User).join(Follow, Follow.follower_id == User.id).where(
            Follow.following_id == current_user.id,
            Follow.follower_id.in_(payload.recipient_ids),
            User.is_active.is_(True),
        )
    )
    recipients = list(follower_result.scalars().all())
    if {recipient.id for recipient in recipients} != set(payload.recipient_ids):
        raise HTTPException(
            status_code=422,
            detail="All recipients must be active followers",
        )

    sharer_name = current_user.username or "A Memosphere member"
    shares = [
        Share(sender_id=current_user.id, recipient_id=recipient.id, post_id=post.id)
        for recipient in recipients
    ]
    notifications = [
        Notification(
            user_id=recipient.id,
            actor_id=current_user.id,
            type="share",
            reference_id=post.id,
            message=f"{sharer_name} shared a post with you",
            is_read=False,
        )
        for recipient in recipients
    ]
    db.add_all([*shares, *notifications])
    await db.commit()

    return ShareBatchRead(shared_count=len(shares))
