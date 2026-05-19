import secrets
import uuid as uuid_pkg
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password
from app.db.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:

    def __init__(self, db: AsyncSession):
        self.user_repository = UserRepository(db)

    @staticmethod
    async def create_refresh_token(user_id: uuid_pkg.UUID, db: AsyncSession) -> str:
        """Create a new refresh token for a user."""
        token = secrets.token_hex(32)
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        refresh_token_repo = RefreshTokenRepository(db)
        await refresh_token_repo.create(user_id, token, expires_at)
        return token

    async def authenticate_user(self, email: str, password: str) -> User | None:
        user = await self.user_repository.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
