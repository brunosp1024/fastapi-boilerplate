from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models.user import User
from app.services.auth_service import AuthService


@pytest.fixture
def db():
    return AsyncMock()


@pytest.fixture
def user():
    user = MagicMock(spec=User)
    user.email = "test@example.com"
    user.hashed_password = "hashedpass"
    user.role = "user"
    user.id = 1
    return user


@pytest.mark.asyncio
async def test_create_refresh_token(db):
    repo_mock = AsyncMock()

    async def create(user_id, token, expires_at):
        return None

    repo_mock.create.side_effect = create
    with patch(
        "app.services.auth_service.RefreshTokenRepository", return_value=repo_mock
    ):
        token = await AuthService.create_refresh_token(uuid4(), db)
    assert isinstance(token, str)
    assert len(token) == 64
    assert repo_mock.create.await_count == 1


async def async_get_by_email_factory(return_value):
    async def get_by_email(email):
        return return_value

    return get_by_email


@pytest.mark.asyncio
async def test_authenticate_user_success(monkeypatch, db, user):
    user_repo_mock = AsyncMock()
    user_repo_mock.get_by_email.side_effect = await async_get_by_email_factory(user)
    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository", lambda db: user_repo_mock
    )
    monkeypatch.setattr(
        "app.services.auth_service.verify_password", lambda pw, hpw: True
    )
    service = AuthService(db)
    service.user_repository = user_repo_mock  # Patch instância
    result = await service.authenticate_user("test@example.com", "password")
    assert result == user


@pytest.mark.asyncio
async def test_authenticate_user_invalid_email(monkeypatch, db):
    user_repo_mock = AsyncMock()
    user_repo_mock.get_by_email.side_effect = await async_get_by_email_factory(None)
    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository", lambda db: user_repo_mock
    )
    service = AuthService(db)
    service.user_repository = user_repo_mock  # Patch instância
    result = await service.authenticate_user("notfound@example.com", "password")
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(monkeypatch, db, user):
    user_repo_mock = AsyncMock()
    user_repo_mock.get_by_email.side_effect = await async_get_by_email_factory(user)
    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository", lambda db: user_repo_mock
    )
    monkeypatch.setattr(
        "app.services.auth_service.verify_password", lambda pw, hpw: False
    )
    service = AuthService(db)
    service.user_repository = user_repo_mock  # Patch instância
    result = await service.authenticate_user("test@example.com", "wrongpass")
    assert result is None
