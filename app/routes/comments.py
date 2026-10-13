from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.database import get_db
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.post import Post
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead

router = APIRouter(prefix="/posts", tags=["comments"])


@router.post("/{post_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    payload: CommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CommentRead:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    comment = Comment(
        user_id=current_user.id,
        post_id=post_id,
        content=payload.content.strip(),
    )
    db.add(comment)

    notification = Notification(
        user_id=post.author_id,
        actor_id=current_user.id,
        type="comment",
        reference_id=post_id,
        message=f"{current_user.email} commented on your post",
        is_read=False,
    )
    db.add(notification)

    await db.commit()
    await db.refresh(comment)

    return CommentRead(
        id=comment.id,
        post_id=comment.post_id,
        user_id=comment.user_id,
        username=current_user.username,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("/{post_id}/comments", response_model=list[CommentRead])
async def list_comments(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CommentRead]:
    result = await db.execute(
        select(Comment, User.username)
        .join(User, User.id == Comment.user_id)
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
    )
    comments = result.all()
    return [
        CommentRead(
            id=comment.id,
            post_id=comment.post_id,
            user_id=comment.user_id,
            username=username,
            content=comment.content,
            created_at=comment.created_at,
        )
        for comment, username in comments
    ]
