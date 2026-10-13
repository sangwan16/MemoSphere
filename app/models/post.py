from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.comment import Comment
    from app.models.like import Like
    from app.models.share import Share
    from app.models.user import User


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(String(5000), nullable=False)
    image_urls: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(250), nullable=True)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visibility: Mapped[str] = mapped_column(String(30), default="public", nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    author: Mapped["User"] = relationship(back_populates="posts")
    category: Mapped["Category | None"] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(back_populates=None)
    likes: Mapped[list["Like"]] = relationship(back_populates=None)
    shares: Mapped[list["Share"]] = relationship(back_populates=None)
