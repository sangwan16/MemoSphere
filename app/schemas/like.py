from datetime import datetime

from pydantic import BaseModel


class LikeRead(BaseModel):
    id: int
    user_id: int
    post_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
