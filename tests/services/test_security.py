from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_token,
)
from app.schemas.user_dto import UserResponse


def test_hash_and_verify_password():
    password = "mysecret"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_verify_password_invalid_hash_returns_false():
    assert not verify_password("mysecret", "not-a-valid-bcrypt-hash")


def test_create_and_verify_access_token():
    data = {"sub": "user@example.com", "role": "user"}
    token = create_access_token(data)
    assert isinstance(token, str)
    # Token válido
    assert verify_token(token) == "user@example.com"


def test_verify_token_invalid():
    with pytest.raises(HTTPException) as exc:
        verify_token("invalidtoken")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_verify_token_missing_sub(monkeypatch):
    # Gera um token válido mas sem 'sub'
    payload = {"role": "user"}
    token = jwt.encode(
        payload, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_verify_token_jwt_error(monkeypatch):
    # Simula jwt.decode lançando JWTError
    monkeypatch.setattr(
        "app.core.security.jwt.decode",
        lambda *a, **kw: (_ for _ in ()).throw(JWTError()),
    )
    with pytest.raises(HTTPException):
        verify_token("anytoken")


@pytest.mark.asyncio
async def test_get_current_user_success(monkeypatch):
    email = "success@example.com"
    token = create_access_token({"sub": email})

    # Patch jwt.decode to return the correct payload
    monkeypatch.setattr("app.core.security.jwt.decode", lambda *a, **kw: {"sub": email})

    class DummyUser:
        def __init__(self, email):
            self.id = uuid4()
            self.name = "Test User"
            self.email = email
            self.role = "user"
            self.created_at = datetime.now()
            self.updated_at = datetime.now()

    mock_db = AsyncMock(spec=AsyncSession)
    mock_scalars = AsyncMock()
    mock_scalars.first = lambda: DummyUser(email)
    mock_result = AsyncMock()
    mock_result.scalars = lambda: mock_scalars

    async def execute(*args, **kwargs):
        return mock_result

    mock_db.execute.side_effect = execute

    user = await get_current_user(token=token, db=mock_db)
    assert isinstance(user, UserResponse)
    assert user.email == email
    assert user.role == "user"


@pytest.mark.asyncio
async def test_get_current_user_missing_sub(monkeypatch):
    # Mocka jwt.decode para retornar payload sem 'sub'
    monkeypatch.setattr(
        "app.core.security.jwt.decode", lambda *a, **kw: {"role": "user"}
    )

    class DummyDB:
        def query(self, *a, **kw):
            class DummyQ:
                def filter(self, *a, **kw):
                    return DummyQ()

                def first(self):
                    return None

            return DummyQ()

    with pytest.raises(HTTPException) as exc:
        await get_current_user(token="token", db=AsyncMock(spec=AsyncSession))
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(monkeypatch):
    monkeypatch.setattr(
        "app.core.security.jwt.decode", lambda *a, **kw: {"sub": "user@example.com"}
    )

    mock_db = AsyncMock(spec=AsyncSession)
    mock_scalars = AsyncMock()
    mock_scalars.first = lambda: None
    mock_result = AsyncMock()
    mock_result.scalars = lambda: mock_scalars

    async def execute(*args, **kwargs):
        return mock_result

    mock_db.execute.side_effect = execute

    with pytest.raises(HTTPException) as exc:
        await get_current_user(token="token", db=mock_db)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_jwt_error(monkeypatch):
    # Simula jwt.decode lançando JWTError
    monkeypatch.setattr(
        "app.core.security.jwt.decode",
        lambda *a, **kw: (_ for _ in ()).throw(JWTError()),
    )

    with pytest.raises(HTTPException):
        await get_current_user(token="token", db=AsyncMock(spec=AsyncSession))


def test_create_access_token_with_expiry():
    data = {"sub": "user@example.com", "role": "user"}
    token = create_access_token(data, expires_delta=timedelta(seconds=1))
    assert isinstance(token, str)
