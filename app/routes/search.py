import base64
import binascii
import json
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.security import get_current_user
from app.db.database import get_db
from app.models.post import Post
from app.models.user import User
from app.schemas.search import (
    SearchPostPage,
    SearchPostRead,
    SearchResponse,
    SearchUserPage,
    SearchUserRead,
)
from app.utils.post_access import post_access_filter

router = APIRouter(prefix="/search", tags=["search"])


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _encode_search_cursor(
    kind: str,
    query_key: str,
    sort_value: str,
    item_id: int,
) -> str:
    value = json.dumps(
        {"kind": kind, "query": query_key, "sort": sort_value, "id": item_id},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode_search_cursor(
    cursor: str,
    expected_kind: str,
    query_key: str,
) -> tuple[str | datetime, int]:
    try:
        padded_cursor = cursor + "=" * (-len(cursor) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded_cursor).decode())
        if (
            not isinstance(decoded, dict)
            or decoded.get("kind") != expected_kind
            or decoded.get("query") != query_key
        ):
            raise ValueError

        sort_value = decoded.get("sort")
        item_id = decoded.get("id")
        if not isinstance(sort_value, str) or not isinstance(item_id, int) or item_id <= 0:
            raise ValueError

        if expected_kind == "posts":
            return datetime.fromisoformat(sort_value), item_id
        return sort_value, item_id
    except (
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ):
        raise HTTPException(status_code=400, detail="Invalid search cursor") from None


@router.get("", response_model=SearchResponse)
async def search(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    q: Annotated[str, Query(min_length=2, max_length=100)],
    section: Annotated[Literal["users", "posts"] | None, Query()] = None,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> SearchResponse:
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Search query must contain at least 2 characters")
    if cursor is not None and section is None:
        raise HTTPException(status_code=400, detail="A search section is required with a cursor")

    query_key = query.casefold()
    pattern = f"%{_escape_like(query)}%"
    users_page: SearchUserPage | None = None
    posts_page: SearchPostPage | None = None

    if section in (None, "users"):
        user_filters = [
            User.is_active.is_(True),
            User.username.is_not(None),
            User.username.ilike(pattern, escape="\\"),
        ]
        if cursor is not None and section == "users":
            cursor_username, cursor_id = _decode_search_cursor(cursor, "users", query_key)
            if not isinstance(cursor_username, str):
                raise HTTPException(status_code=400, detail="Invalid search cursor")
            username_order = func.lower(User.username)
            user_filters.append(
                or_(
                    username_order > cursor_username,
                    and_(username_order == cursor_username, User.id > cursor_id),
                )
            )

        user_result = await db.execute(
            select(User)
            .where(*user_filters)
            .order_by(func.lower(User.username).asc(), User.id.asc())
            .limit(limit + 1)
        )
        matched_users = list(user_result.scalars().all())
        has_more_users = len(matched_users) > limit
        matched_users = matched_users[:limit]
        user_items = [
            SearchUserRead(id=user.id, username=user.username)
            for user in matched_users
            if user.username is not None
        ]
        next_user_cursor = (
            _encode_search_cursor(
                "users",
                query_key,
                matched_users[-1].username.casefold(),
                matched_users[-1].id,
            )
            if has_more_users and matched_users and matched_users[-1].username is not None
            else None
        )
        users_page = SearchUserPage(items=user_items, next_cursor=next_user_cursor)

    if section in (None, "posts"):
        post_filters = [
            Post.is_draft.is_(False),
            post_access_filter(current_user.id),
            or_(
                Post.title.ilike(pattern, escape="\\"),
                Post.content.ilike(pattern, escape="\\"),
                Post.excerpt.ilike(pattern, escape="\\"),
            ),
        ]
        if cursor is not None and section == "posts":
            cursor_created_at, cursor_id = _decode_search_cursor(cursor, "posts", query_key)
            if not isinstance(cursor_created_at, datetime):
                raise HTTPException(status_code=400, detail="Invalid search cursor")
            post_filters.append(
                or_(
                    Post.created_at < cursor_created_at,
                    and_(Post.created_at == cursor_created_at, Post.id < cursor_id),
                )
            )

        post_result = await db.execute(
            select(Post)
            .join(User, User.id == Post.author_id)
            .options(selectinload(Post.author))
            .where(*post_filters)
            .order_by(Post.created_at.desc(), Post.id.desc())
            .limit(limit + 1)
        )
        matched_posts = list(post_result.scalars().all())
        has_more_posts = len(matched_posts) > limit
        matched_posts = matched_posts[:limit]
        post_items = [
            SearchPostRead(
                id=post.id,
                title=post.title,
                content=post.content,
                image_urls=post.image_urls,
                excerpt=post.excerpt,
                category_id=post.category_id,
                author_id=post.author_id,
                visibility=post.visibility,
                is_draft=post.is_draft,
                created_at=post.created_at,
                updated_at=post.updated_at,
                author_username=post.author.username if post.author else None,
            )
            for post in matched_posts
        ]
        next_post_cursor = (
            _encode_search_cursor(
                "posts",
                query_key,
                matched_posts[-1].created_at.isoformat(),
                matched_posts[-1].id,
            )
            if has_more_posts and matched_posts
            else None
        )
        posts_page = SearchPostPage(items=post_items, next_cursor=next_post_cursor)

    return SearchResponse(users=users_page, posts=posts_page)
