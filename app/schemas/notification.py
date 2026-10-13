from datetime import datetime

from pydantic import BaseModel, Field


class NotificationRead(BaseModel):
    id: int
    user_id: int
    actor_id: int | None = None
    type: str
    reference_id: int | None = None
    message: str
    is_read: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    user_id: int
    actor_id: int | None = None
    type: str = Field(..., min_length=1, max_length=40)
    reference_id: int | None = None
    message: str = Field(..., min_length=1, max_length=255)
