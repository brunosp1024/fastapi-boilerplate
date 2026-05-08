from datetime import UTC, datetime, timedelta

from fastapi import HTTPException


class MockToken:
    def __init__(self, revoked=False, expired=False, user_id=1):
        self.revoked = revoked
        self.user_id = user_id
        if expired:
            self.expires_at = datetime.now(UTC) - timedelta(days=1)
        else:
            self.expires_at = datetime.now(UTC) + timedelta(days=1)


def test_register_user(client):
    """Test user registration."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert "id" in data


def test_login(client):
    """Test user login."""
    # First register a user
    client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )

    # Then login
    response = client.post(
        "/auth/token",
        data={"username": "test@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_get_current_user(client):
    """Test getting current user info."""
    # Register and login
    client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )

    login_response = client.post(
        "/auth/token",
        data={"username": "test@example.com", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]

    # Get current user
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


def test_register_duplicate_user(client):
    """Test registering a user with an existing email."""
    payload = {
        "name": "Test User",
        "email": "duplicate@example.com",
        "password": "testpassword123",
    }
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login_wrong_password(client):
    """Test login with wrong password."""
    payload = {
        "name": "Test User",
        "email": "wrongpass@example.com",
        "password": "testpassword123",
    }
    client.post("/auth/register", json=payload)
    response = client.post(
        "/auth/token",
        data={"username": "wrongpass@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Test login with nonexistent user."""
    response = client.post(
        "/auth/token",
        data={"username": "notfound@example.com", "password": "irrelevant"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_refresh_token_invalid(client):
    """Test refresh with invalid token."""
    response = client.post("/auth/refresh", json={"refresh_token": "invalidtoken"})
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


def test_access_me_without_token(client):
    """Test /auth/me without token."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_refresh_token_expired(client, monkeypatch):
    """Test refresh with expired token."""
    client.post(
        "/auth/register",
        json={"name": "Exp User", "email": "exp@example.com", "password": "testpass"},
    )
    login_resp = client.post(
        "/auth/token", data={"username": "exp@example.com", "password": "testpass"}
    )
    refresh_token = login_resp.json()["refresh_token"]
    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.get_by_token",
        lambda self, token: MockToken(expired=True),
    )
    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


def test_refresh_token_user_not_found(client, monkeypatch):
    """Test refresh when user does not exist."""
    client.post(
        "/auth/register",
        json={"name": "NoUser", "email": "nouser@example.com", "password": "testpass"},
    )
    login_resp = client.post(
        "/auth/token", data={"username": "nouser@example.com", "password": "testpass"}
    )
    refresh_token = login_resp.json()["refresh_token"]
    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.get_by_token",
        lambda self, token: MockToken(user_id=9999),
    )
    monkeypatch.setattr(
        "app.services.user_service.UserService.get_user_by_id",
        lambda self, user_id: None,
    )
    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_refresh_token_revoked(client, monkeypatch):
    """Test refresh with revoked token."""
    client.post(
        "/auth/register",
        json={
            "name": "Revoked",
            "email": "revoked@example.com",
            "password": "testpass",
        },
    )
    login_resp = client.post(
        "/auth/token", data={"username": "revoked@example.com", "password": "testpass"}
    )
    refresh_token = login_resp.json()["refresh_token"]
    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.get_by_token",
        lambda self, token: MockToken(revoked=True),
    )
    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


def test_verify_token_valid_and_invalid():
    from app.core.security import create_access_token, verify_token

    # Token válido
    token = create_access_token({"sub": "test@example.com", "role": "user"})
    assert verify_token(token) == "test@example.com"
    # Token inválido
    import pytest

    with pytest.raises(HTTPException):
        verify_token("invalid.token.here")


def test_refresh_token_success(client, monkeypatch):
    """Test refresh token flow with success, cobrindo revoke e retorno."""
    # Registra e faz login para obter refresh_token
    client.post(
        "/auth/register",
        json={
            "name": "User Success",
            "email": "success@example.com",
            "password": "testpass",
        },
    )
    login_resp = client.post(
        "/auth/token", data={"username": "success@example.com", "password": "testpass"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Mocka o repo e user_service para fluxo de sucesso
    class SuccessToken:
        def __init__(self):
            self.revoked = False
            self.expires_at = datetime.now(UTC) + timedelta(days=1)
            self.user_id = 123

    class DummyUser:
        email = "success@example.com"
        role = "user"
        id = 123

    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.get_by_token",
        lambda self, token: SuccessToken(),
    )
    monkeypatch.setattr(
        "app.repositories.refresh_token_repository.RefreshTokenRepository.revoke",
        lambda self, token: None,
    )
    monkeypatch.setattr(
        "app.services.user_service.UserService.get_user_by_id",
        lambda self, user_id: DummyUser(),
    )
    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
