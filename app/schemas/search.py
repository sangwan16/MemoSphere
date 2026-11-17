from datetime import datetime

from pydantic import BaseModel, Field


class SearchUserRead(BaseModel):
    id: int
    username: str


class SearchPostRead(BaseModel):
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
    author_username: str | None = None


class SearchUserPage(BaseModel):
    items: list[SearchUserRead]
    next_cursor: str | None


class SearchPostPage(BaseModel):
    items: list[SearchPostRead]
    next_cursor: str | None


class SearchResponse(BaseModel):
    users: SearchUserPage | None = None
    posts: SearchPostPage | None = None
