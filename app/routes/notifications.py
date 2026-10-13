from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[NotificationRead]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    notifications = result.scalars().all()
    return [
        NotificationRead(
            id=notification.id,
            user_id=notification.user_id,
            actor_id=notification.actor_id,
            type=notification.type,
            reference_id=notification.reference_id,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )
        for notification in notifications
    ]


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
async def create_notification(
    payload: NotificationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationRead:
    target_user = await db.get(User, payload.user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="Target user not found")

    notification = Notification(
        user_id=payload.user_id,
        actor_id=payload.actor_id,
        type=payload.type,
        reference_id=payload.reference_id,
        message=payload.message,
        is_read=False,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    return NotificationRead(
        id=notification.id,
        user_id=notification.user_id,
        actor_id=notification.actor_id,
        type=notification.type,
        reference_id=notification.reference_id,
        message=notification.message,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationRead:
    notification = await db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot mark another user's notification as read")

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)

    return NotificationRead(
        id=notification.id,
        user_id=notification.user_id,
        actor_id=notification.actor_id,
        type=notification.type,
        reference_id=notification.reference_id,
        message=notification.message,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )
