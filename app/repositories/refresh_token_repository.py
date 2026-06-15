import uuid as uuid_pkg
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.refresh_token import RefreshToken
from app.repositories.base_repository import BaseRepository


class RefreshTokenRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(
        self, user_id: uuid_pkg.UUID, token: str, expires_at: datetime
    ) -> RefreshToken:
        refresh_token = RefreshToken(
            token=token, user_id=user_id, expires_at=expires_at
        )
        self.db.add(refresh_token)
        await self._safe_commit()
        await self.db.refresh(refresh_token)
        return refresh_token

    async def get_by_token(self, token: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: str) -> bool:
        refresh_token = await self.get_by_token(token)
        if not refresh_token:
            return False
        refresh_token.revoked = True
        await self._safe_commit()
        return True
