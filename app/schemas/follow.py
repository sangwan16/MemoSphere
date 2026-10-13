from datetime import datetime

from pydantic import BaseModel, Field


class FollowRead(BaseModel):
    follower_id: int
    following_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FollowRequest(BaseModel):
    user_id: int = Field(..., gt=0)


class FollowUserRead(BaseModel):
    id: int
    username: str | None

    model_config = {"from_attributes": True}


class ProfileStatsRead(BaseModel):
    posts_count: int
    followers_count: int
    following_count: int
