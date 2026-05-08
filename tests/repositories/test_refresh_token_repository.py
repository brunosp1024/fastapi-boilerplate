from datetime import UTC, datetime, timedelta

from app.repositories.refresh_token_repository import RefreshTokenRepository


def test_create_and_get_by_token(db_session):
    repo = RefreshTokenRepository(db_session)
    token = "tok123"
    expires = datetime.now(UTC) + timedelta(days=1)
    created = repo.create(user_id=1, token=token, expires_at=expires)  # noqa: F841
    found = repo.get_by_token(token)
    assert found is not None
    assert found.token == token


def test_get_by_token_not_found(db_session):
    repo = RefreshTokenRepository(db_session)
    assert repo.get_by_token("notfound") is None


def test_revoke_token_success(db_session):
    repo = RefreshTokenRepository(db_session)
    token = "revoketok"
    expires = datetime.now(UTC) + timedelta(days=1)
    repo.create(user_id=1, token=token, expires_at=expires)
    assert repo.revoke(token) is True
    revoked = repo.get_by_token(token)
    assert revoked.revoked is True


def test_revoke_token_not_found(db_session):
    repo = RefreshTokenRepository(db_session)
    assert repo.revoke("notfound") is False
