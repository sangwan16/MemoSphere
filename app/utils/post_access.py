from sqlalchemy import and_, exists, or_, select

from app.models.follow import Follow
from app.models.post import Post
from app.models.user import User


def post_access_filter(viewer_id: int):
    follows_author = exists(
        select(Follow.id).where(
            Follow.follower_id == viewer_id,
            Follow.following_id == Post.author_id,
        )
    )
    owns_post = Post.author_id == viewer_id
    return and_(
        or_(owns_post, User.is_public.is_(True), follows_author),
        or_(
            owns_post,
            Post.visibility == "public",
            and_(Post.visibility == "followers", follows_author),
        ),
    )
