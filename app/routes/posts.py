from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.security import get_current_user
from app.db.database import get_db
from app.models.category import Category
from app.models.follow import Follow
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostCreate, PostRead, PostUpdate

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/categories", response_model=list[dict[str, object]])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, object]]:
    result = await db.execute(select(Category).order_by(Category.name.asc()))
    categories = result.scalars().all()
    return [
        {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
        }
        for category in categories
    ]


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PostRead:
    if payload.category_id is not None:
        category = await db.get(Category, payload.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")

    post = Post(
        title=payload.title.strip(),
        content=payload.content.strip(),
        image_urls=[str(image_url) for image_url in payload.image_urls],
        excerpt=(payload.excerpt.strip() if payload.excerpt else None),
        category_id=payload.category_id,
        visibility=payload.visibility,
        is_draft=payload.is_draft,
        author_id=current_user.id,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    return PostRead(
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
        author_email=current_user.email,
        author_username=current_user.username,
    )


@router.get("", response_model=list[PostRead])
async def list_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PostRead]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.category))
        .where(Post.is_draft.is_(False))
        .order_by(Post.created_at.desc())
    )
    posts = result.scalars().all()
    return [
        PostRead(
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
            author_email=post.author.email if post.author else None,
            author_username=post.author.username if post.author else None,
        )
        for post in posts
    ]


@router.get("/users/{user_id}", response_model=list[PostRead])
async def list_user_posts(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PostRead]:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    is_following = user.id == current_user.id or await db.scalar(
        select(Follow.id).where(
            Follow.follower_id == current_user.id,
            Follow.following_id == user.id,
        )
    ) is not None
    if not user.is_public and not is_following:
        raise HTTPException(status_code=403, detail="This profile is private")

    visible_post = or_(
        Post.visibility == "public",
        and_(Post.visibility == "followers", is_following),
        and_(Post.visibility == "private", Post.author_id == current_user.id),
    )
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.category))
        .where(
            Post.author_id == user.id,
            Post.is_draft.is_(False),
            visible_post,
        )
        .order_by(Post.created_at.desc())
    )
    posts = result.scalars().all()
    return [
        PostRead(
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
            author_email=post.author.email if post.author else None,
            author_username=post.author.username if post.author else None,
        )
        for post in posts
    ]


@router.get("/me", response_model=list[PostRead])
async def list_my_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PostRead]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.category))
        .where(Post.author_id == current_user.id, Post.is_draft.is_(False))
        .order_by(Post.created_at.desc())
    )
    posts = result.scalars().all()
    return [
        PostRead(
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
            author_email=current_user.email,
            author_username=current_user.username,
        )
        for post in posts
    ]


@router.get("/{post_id}", response_model=PostRead)
async def get_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostRead:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    author = await db.get(User, post.author_id)

    return PostRead(
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
        author_email=author.email if author else None,
        author_username=author.username if author else None,
    )


@router.put("/{post_id}", response_model=PostRead)
async def update_post(
    post_id: int,
    payload: PostUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PostRead:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own posts")

    if payload.category_id is not None:
        category = await db.get(Category, payload.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")

    update_values = payload.model_dump(exclude_unset=True)
    if payload.image_urls is not None:
        update_values["image_urls"] = [str(image_url) for image_url in payload.image_urls]

    for field, value in update_values.items():
        if value is not None and field != "category_id":
            setattr(post, field, value)
        elif field == "category_id":
            post.category_id = value

    if payload.title is not None:
        post.title = payload.title.strip()
    if payload.content is not None:
        post.content = payload.content.strip()
    if payload.excerpt is not None:
        post.excerpt = payload.excerpt.strip()

    await db.commit()
    await db.refresh(post)

    return PostRead(
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
        author_email=current_user.email,
        author_username=current_user.username,
    )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")

    await db.delete(post)
    await db.commit()
