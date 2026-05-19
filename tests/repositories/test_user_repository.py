from datetime import datetime
from uuid import UUID as uuid

import pytest

from app.repositories.user_repository import UserRepository
from app.schemas.user_dto import UserCreateDTO, UserUpdateDTO


def make_user_data(email="repo@example.com", name="Repo", password="123456"):
    return UserCreateDTO(name=name, email=email, password=password)


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session):
    repo = UserRepository(db_session)
    id = uuid("3455e9b2-8c1a-4d5f-9c3a-123456789abc")
    result = await repo.get_by_id(id)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_email_not_found(db_session):
    repo = UserRepository(db_session)
    result = await repo.get_by_email("notfound@x.com")
    assert result is None


@pytest.mark.asyncio
async def test_update_user_not_found(db_session):
    repo = UserRepository(db_session)
    update = UserUpdateDTO(name="New Name")
    id = uuid("3455e9b2-8c1a-4d5f-9c3a-123456789abc")
    result = await repo.update(id, update)
    assert result is None


@pytest.mark.asyncio
async def test_delete_user_not_found(db_session):
    repo = UserRepository(db_session)
    id = uuid("3455e9b2-8c1a-4d5f-9c3a-123456789abc")
    result = await repo.delete(id)
    assert result is False


@pytest.mark.asyncio
async def test_update_user_password(db_session):
    repo = UserRepository(db_session)
    user = await repo.create(make_user_data(email="pwchange@x.com"))
    old_hash = user.hashed_password
    update = UserUpdateDTO(password="newpass123")
    updated = await repo.update(user.id, update)
    assert updated is not None
    assert updated.hashed_password != old_hash


@pytest.mark.asyncio
async def test_update_user_fields(db_session):
    repo = UserRepository(db_session)
    user = await repo.create(make_user_data(email="fields@x.com"))
    update = UserUpdateDTO(name="Changed", email="changed@x.com")
    updated = await repo.update(user.id, update)
    assert updated is not None
    assert updated.name == "Changed"
    assert updated.email == "changed@x.com"
    assert isinstance(updated.updated_at, datetime)


@pytest.mark.asyncio
async def test_delete_user_success(db_session):
    repo = UserRepository(db_session)
    user = await repo.create(make_user_data(email="del@x.com"))
    assert await repo.delete(user.id) is True


@pytest.mark.asyncio
async def test_create_user_sets_admin_role(db_session, monkeypatch):
    from app.core import config

    repo = UserRepository(db_session)
    # Garante que APP_DEBUG está True
    monkeypatch.setattr(config.settings, "APP_DEBUG", True)
    user = await repo.create(make_user_data(email="adminuser@x.com"))
    assert user.role == "admin"
