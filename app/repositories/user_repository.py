from datetime import UTC, datetime
from uuid import UUID as uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User
from app.schemas.user_dto import UserCreateDTO, UserUpdateDTO


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_data: UserCreateDTO) -> User:
        hashed_pw = hash_password(user_data.password)
        user = User(
            name=user_data.name, email=user_data.email, hashed_password=hashed_pw
        )

        if settings.APP_DEBUG and ("admin" in user_data.email):
            user.role = "admin"

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list(self) -> list[User]:
        result = await self.db.execute(select(User))
        return list(result.scalars().all())

    async def update(self, user_id: uuid, user_data: UserUpdateDTO) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        update_data = user_data.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))
        for key, value in update_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: uuid) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        await self.db.delete(user)
        await self.db.commit()
        return True
