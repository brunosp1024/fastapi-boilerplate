import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient

from app.main import app

REGISTER_PAYLOAD = {
    "name": "Test User",
    "email": "test@example.com",
    "password": "testpassword123",
}


class MockToken:
    def __init__(self, revoked=False, expired=False, user_id=1):
        self.revoked = revoked
        self.user_id = user_id
        if expired:
            self.expires_at = datetime.now(UTC) - timedelta(days=1)
        else:
            self.expires_at = datetime.now(UTC) + timedelta(days=1)


# Helper async genérico para mocks async
def async_return(result=None, factory=None, **kwargs):
    async def _mock(*args, **_):
        if factory:
            return factory(**kwargs)
        return result

    return _mock


# Mock special for success flow
class SuccessToken:
    def __init__(self):
        self.revoked = False
        self.expires_at = datetime.now(UTC) + timedelta(days=1)
        self.user_id = 123
        self.token = "dummy_token"


async def mock_get_by_token_success(self, token):
    return SuccessToken()


@pytest.mark.asyncio
async def test_register_user_success(monkeypatch):
    """Ensure that the return of /auth/register is validated by UserResponse."""
    fake_user = {
        "id": str(uuid4()),
        "name": "Usuário Teste",
        "email": "teste@email.com",
        "role": "user",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    async def fake_create_user(self, user_data):
        return fake_user

    with patch(
        "app.services.user_service.UserService.create_user", new=fake_create_user
    ):
        transport = ASGITransport(app=app)  # type: ignore[arg-type, unused-ignore]
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            payload = {
                "name": "Usuário Teste",
                "email": "teste@email.com",
                "password": "123",
            }
            response = await ac.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == fake_user["id"]
    assert data["name"] == "Usuário Teste"
    assert data["email"] == "teste@email.com"


@pytest.mark.asyncio
async def test_login_success(client, monkeypatch):
    fake_user = SimpleNamespace(id=123, email="user@example.com", role="user")

    async def fake_authenticate_user(self, username, password):
        assert username == fake_user.email
        assert password == "testpassword123"
        return fake_user

    async def fake_create_refresh_token(user_id, db):
        assert user_id == fake_user.id
        return "fake-refresh-token"

    def fake_create_access_token(data):
        assert data == {"sub": fake_user.email, "role": fake_user.role}
        return "fake.access.token"

    monkeypatch.setattr(
        "app.api.routes.auth_routes.AuthService.authenticate_user",
        fake_authenticate_user,
    )
    monkeypatch.setattr(
        "app.api.routes.auth_routes.AuthService.create_refresh_token",
        fake_create_refresh_token,
    )
    monkeypatch.setattr(
        "app.api.routes.auth_routes.create_access_token",
        fake_create_access_token,
    )

    response = await client.post(
        "/auth/token",
        data={"username": fake_user.email, "password": "testpassword123"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "access_token": "fake.access.token",
        "refresh_token": "fake-refresh-token",
        "token_type": "bearer",
    }


@pytest.mark.asyncio
async def test_register_duplicate_user(client):
    """Test registering a user with an existing email."""
    payload = {
        "name": "Test User",
        "email": "duplicate@example.com",
        "password": "testpassword123",
    }
    await client.post("/auth/register", json=payload)
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Test login with wrong password."""
    payload = REGISTER_PAYLOAD.copy()
    payload["email"] = "wrongpass@example.com"
    await client.post("/auth/register", json=payload)
    response = await client.post(
        "/auth/token",
        data={"username": payload["email"], "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_login_authenticate_user_none(monkeypatch):
    """Garante cobertura do if not user no login."""
    from fastapi import status

    async def fake_authenticate_user(self, username, password):
        return None

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.authenticate_user",
        fake_authenticate_user,
    )
    transport = ASGITransport(app=app)  # type: ignore[arg-type, unused-ignore]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/auth/token",
            data={"username": "qualquer@fail.com", "password": "fail"},
        )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    """Test refresh with invalid token."""
    response = await client.post(
        "/auth/refresh", json={"refresh_token": "invalidtoken"}
    )
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_success(client):
    """Test the successful return of the /auth/me endpoint."""
    payload = {
        "name": "Test User",
        "email": "me_success@example.com",
        "password": "password123",
    }
    await client.post("/auth/register", json=payload)
    login_response = await client.post(
        "/auth/token",
        data={"username": payload["email"], "password": payload["password"]},
    )
    token = login_response.json()["access_token"]
    # Call endpoint /auth/me
    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["name"] == payload["name"]
    assert data["role"] == "user"
    # Validate UUID
    assert re.match(r"^[0-9a-fA-F-]{36}$", data["id"])
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_access_me_without_token(client):
    """Test /auth/me without token."""
    response = await client.get("/auth/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_expired(client, monkeypatch):
    """Test refresh with expired token."""
    await client.post(
        "/auth/register",
        json={"name": "Exp User", "email": "exp@example.com", "password": "testpass"},
    )
    login_resp = await client.post(
        "/auth/token", data={"username": "exp@example.com", "password": "testpass"}
    )
    refresh_token = login_resp.json()["refresh_token"]
    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.get_by_token",
        async_return(factory=lambda: MockToken(expired=True)),
    )
    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_user_not_found(client, monkeypatch):
    """Test refresh when user does not exist."""
    await client.post(
        "/auth/register",
        json={"name": "NoUser", "email": "nouser@example.com", "password": "testpass"},
    )
    login_resp = await client.post(
        "/auth/token", data={"username": "nouser@example.com", "password": "testpass"}
    )
    refresh_token = login_resp.json()["refresh_token"]
    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.get_by_token",
        async_return(MockToken(user_id=9999)),
    )
    monkeypatch.setattr(
        "app.services.user_service.UserService.get_user_by_id",
        async_return(None),
    )
    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_not_found_returns_401(client, monkeypatch):
    async def fake_get_by_token(self, token):
        return None

    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.get_by_token",
        fake_get_by_token,
    )

    response = await client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid-refresh-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_token_revokes_old_refresh_token(client, monkeypatch):
    old_refresh_token = "old-refresh-token"

    stored_token = SimpleNamespace(
        revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        user_id=123,
    )

    user = SimpleNamespace(
        id=123,
        email="user@example.com",
        role="user",
    )

    revoked_tokens = []

    async def fake_get_by_token(self, token):
        assert token == old_refresh_token
        return stored_token

    async def fake_get_user_by_id(self, user_id):
        assert user_id == stored_token.user_id
        return user

    def fake_create_access_token(data):
        assert data == {"sub": user.email, "role": user.role}
        return "new-access-token"

    async def fake_create_refresh_token(user_id, db):
        assert user_id == user.id
        return "new-refresh-token"

    async def fake_revoke(self, token):
        revoked_tokens.append(token)
        return True

    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.get_by_token",
        fake_get_by_token,
    )
    monkeypatch.setattr(
        "app.services.user_service.UserService.get_user_by_id",
        fake_get_user_by_id,
    )
    monkeypatch.setattr(
        "app.api.routes.auth_routes.create_access_token",
        fake_create_access_token,
    )
    monkeypatch.setattr(
        "app.api.routes.auth_routes.AuthService.create_refresh_token",
        fake_create_refresh_token,
    )
    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.revoke",
        fake_revoke,
    )

    response = await client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "token_type": "bearer",
    }

    assert revoked_tokens == [old_refresh_token]


def test_verify_token_valid_and_invalid():
    from app.core.security import create_access_token, verify_token

    # Token válido
    token = create_access_token({"sub": "test@example.com", "role": "user"})
    assert verify_token(token) == "test@example.com"
    # Token inválido
    import pytest

    with pytest.raises(HTTPException):
        verify_token("invalid.token.here")


@pytest.mark.asyncio
async def test_refresh_token_success(client, monkeypatch):
    """Test refresh token flow with success, cobrindo revoke e retorno."""
    # Registra e faz login para obter refresh_token
    await client.post(
        "/auth/register",
        json={
            "name": "User Success",
            "email": "success@example.com",
            "password": "testpass",
        },
    )
    login_resp = await client.post(
        "/auth/token", data={"username": "success@example.com", "password": "testpass"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Mocka o repo e user_service para fluxo de sucesso
    from uuid import uuid4 as uuid

    class DummyUser:
        email = "success@example.com"
        role = "user"
        id = uuid()

    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.get_by_token",
        mock_get_by_token_success,
    )
    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.revoke",
        async_return(None),
    )
    monkeypatch.setattr(
        "app.services.user_service.UserService.get_user_by_id",
        async_return(result=DummyUser()),
    )
    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_value_error(monkeypatch):
    """Garante que ValueError genérico retorna 400 no /auth/register."""
    from fastapi import status

    async def fake_create_user(self, user_data):
        raise ValueError("Erro genérico de validação")

    with patch(
        "app.services.user_service.UserService.create_user", new=fake_create_user
    ):
        transport = ASGITransport(app=app)  # type: ignore[arg-type, unused-ignore]
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            payload = {"name": "X", "email": "x@email.com", "password": "123"}
            response = await ac.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Erro genérico de validação" in response.json()["detail"]
