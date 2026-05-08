from datetime import timedelta

import pytest
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_token,
)


def test_hash_and_verify_password():
    password = "mysecret"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


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


def test_get_current_user_missing_sub(monkeypatch):
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
        get_current_user(token="token", db=DummyDB())
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_user_not_found(monkeypatch):
    # Mocka jwt.decode para retornar payload com sub
    monkeypatch.setattr(
        "app.core.security.jwt.decode", lambda *a, **kw: {"sub": "user@example.com"}
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
        get_current_user(token="token", db=DummyDB())
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_jwt_error(monkeypatch):
    # Simula jwt.decode lançando JWTError
    monkeypatch.setattr(
        "app.core.security.jwt.decode",
        lambda *a, **kw: (_ for _ in ()).throw(JWTError()),
    )

    class DummyDB:
        def query(self, *a, **kw):
            return self

        def filter(self, *a, **kw):
            return self

        def first(self):
            return None

    with pytest.raises(HTTPException):
        get_current_user(token="token", db=DummyDB())


def test_create_access_token_with_expiry():
    data = {"sub": "user@example.com", "role": "user"}
    token = create_access_token(data, expires_delta=timedelta(seconds=1))
    assert isinstance(token, str)
