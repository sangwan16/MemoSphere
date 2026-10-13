from datetime import datetime

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class CommentRead(BaseModel):
    id: int
    post_id: int
    user_id: int
    username: str | None
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
