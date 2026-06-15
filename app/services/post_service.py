from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.http_exceptions import ForbiddenException, NotFoundException
from app.db.models.post import Post
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.post_dto import PostCreate, PostUpdate


class PostService:
    def __init__(self, db: AsyncSession):
        self.post_repo = PostRepository(db)
        self.user_repo = UserRepository(db)

    async def _get_user_by_id(self, user_id: UUID):
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundException("User not found")
        return user

    async def _get_user_by_username(self, username: str):
        user = await self.user_repo.get_by_name(username)
        if user is None:
            raise NotFoundException("User not found")
        return user

    async def create_post(
        self,
        post: PostCreate,
        current_user_id: UUID,
    ) -> Post:
        user = await self._get_user_by_id(current_user_id)
        if current_user_id != user.id:
            raise ForbiddenException()

        return await self.post_repo.create_post(post, user.id)

    async def read_posts(
        self, username: str, page: int, items_per_page: int
    ) -> list[Post]:
        user = await self._get_user_by_username(username)
        return await self.post_repo.list_by_user(user.id, page, items_per_page)

    async def read_post(self, username: str, post_id: UUID) -> Post:
        user = await self._get_user_by_username(username)
        db_post = await self.post_repo.get_by_id_and_user(post_id, user.id)
        if db_post is None:
            raise NotFoundException("Post not found")
        return db_post

    async def patch_post(
        self,
        username: str,
        post_id: UUID,
        values: PostUpdate,
        current_user_id: UUID,
    ) -> None:
        user = await self._get_user_by_username(username)
        if current_user_id != user.id:
            raise ForbiddenException()

        db_post = await self.post_repo.get_by_id_and_user(post_id, user.id)
        if db_post is None:
            raise NotFoundException("Post not found")

        update_data = values.model_dump(exclude_unset=True)
        await self.post_repo.update_post(db_post, update_data)

    async def erase_post(
        self, username: str, post_id: UUID, current_user_id: UUID
    ) -> None:
        user = await self._get_user_by_username(username)
        if current_user_id != user.id:
            raise ForbiddenException()

        db_post = await self.post_repo.get_by_id_and_user(post_id, user.id)
        if db_post is None:
            raise NotFoundException("Post not found")

        await self.post_repo.soft_delete(db_post)

    async def erase_db_post(
        self, username: str, post_id: UUID, current_user_role: str
    ) -> None:
        await self._get_user_by_username(username)
        if current_user_role != "admin":
            raise ForbiddenException()

        db_post = await self.post_repo.get_active_by_id(post_id)
        if db_post is None:
            raise NotFoundException("Post not found")

        await self.post_repo.hard_delete(db_post)
