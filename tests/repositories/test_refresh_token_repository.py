from datetime import UTC, datetime, timedelta

import pytest

from app.db.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository


@pytest.mark.asyncio
async def test_create_and_get_by_token(db_session):
    user = User(email="test@example.com", name="Test", hashed_password="123")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    repo = RefreshTokenRepository(db_session)
    token = "tok123"
    expires = datetime.now(UTC) + timedelta(days=1)
    created = await repo.create(  # noqa: F841
        user_id=user.id, token=token, expires_at=expires
    )
    found = await repo.get_by_token(token)
    assert found is not None
    assert found.token == token


@pytest.mark.asyncio
async def test_get_by_token_not_found(db_session):
    repo = RefreshTokenRepository(db_session)
    assert await repo.get_by_token("notfound") is None


@pytest.mark.asyncio
async def test_revoke_token_success(db_session):
    user = User(email="revoke@example.com", name="Revoke", hashed_password="123")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    repo = RefreshTokenRepository(db_session)
    token = "revoketok"
    expires = datetime.now(UTC) + timedelta(days=1)
    await repo.create(user_id=user.id, token=token, expires_at=expires)
    assert await repo.revoke(token) is True
    revoked = await repo.get_by_token(token)
    assert revoked is not None
    assert revoked.revoked is True


@pytest.mark.asyncio
async def test_revoke_token_not_found(db_session):
    repo = RefreshTokenRepository(db_session)
    assert await repo.revoke("notfound") is False
