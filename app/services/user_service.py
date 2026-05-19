from uuid import UUID as uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_dto import UserCreateDTO, UserUpdateDTO

USER_NOT_FOUND = "User not found"


class UserService:
    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def create_user(self, user_data: UserCreateDTO) -> User:
        existing_user = await self.repository.get_by_email(user_data.email)
        if existing_user:
            raise ValueError("A user with this email already exists.")
        return await self.repository.create(user_data)

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.repository.get_by_email(email)

    async def get_user_by_id(self, user_id: uuid) -> User | None:
        return await self.repository.get_by_id(user_id)

    async def list_users(self) -> list[User]:
        return await self.repository.list()

    async def update_user(self, user_id: uuid, user_data: UserUpdateDTO) -> User | None:
        return await self.repository.update(user_id, user_data)

    async def delete_user(self, user_id: uuid) -> bool:
        return await self.repository.delete(user_id)
