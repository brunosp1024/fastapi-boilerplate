from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.post import Post
from app.repositories.base_repository import BaseRepository
from app.schemas.post_dto import PostCreate


class PostRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def get_post_by_id(self, post_id: UUID) -> Post | None:
        result = await self.db.execute(
            select(Post).where(Post.id == post_id, Post.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def create_post(self, post_data: PostCreate, created_by: UUID) -> Post:
        db_post = Post(
            title=post_data.title,
            text=post_data.text,
            media_url=post_data.media_url,
            created_by=created_by,
        )
        self.db.add(db_post)
        await self._safe_commit()
        await self.db.refresh(db_post)
        return db_post

    async def list_by_user(
        self, user_id: UUID, page: int, items_per_page: int
    ) -> list[Post]:
        offset = (page - 1) * items_per_page
        result = await self.db.execute(
            select(Post)
            .where(Post.created_by == user_id, Post.is_deleted.is_(False))
            .offset(offset)
            .limit(items_per_page)
        )
        return list(result.scalars().all())

    async def get_by_id_and_user(self, post_id: UUID, user_id: UUID) -> Post | None:
        result = await self.db.execute(
            select(Post).where(
                Post.id == post_id,
                Post.created_by == user_id,
                Post.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(self, post_id: UUID) -> Post | None:
        result = await self.db.execute(
            select(Post).where(Post.id == post_id, Post.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def update_post(self, post: Post, update_data: dict[str, object]) -> None:
        for key, value in update_data.items():
            setattr(post, key, value)
        await self._safe_commit()

    async def soft_delete(self, post: Post) -> None:
        post.is_deleted = True
        await self._safe_commit()

    async def hard_delete(self, post: Post) -> None:
        await self.db.delete(post)
        await self._safe_commit()
