from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    image_urls: list[AnyHttpUrl] = Field(default_factory=list, max_length=10)
    excerpt: str | None = Field(default=None, max_length=250)
    category_id: int | None = None
    visibility: Literal["public", "followers", "private"] = "public"
    is_draft: bool = False


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    image_urls: list[AnyHttpUrl] | None = Field(default=None, max_length=10)
    excerpt: str | None = Field(default=None, max_length=250)
    category_id: int | None = None
    visibility: Literal["public", "followers", "private"] | None = None
    is_draft: bool | None = None


class PostRead(BaseModel):
    id: int
    title: str
    content: str
    image_urls: list[str] = Field(default_factory=list)
    excerpt: str | None = None
    category_id: int | None = None
    author_id: int
    visibility: str
    is_draft: bool
    created_at: datetime
    updated_at: datetime | None = None
    author_email: str | None = None
    author_username: str | None = None

    model_config = {"from_attributes": True}
