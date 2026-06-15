from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _safe_commit(self) -> None:
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
