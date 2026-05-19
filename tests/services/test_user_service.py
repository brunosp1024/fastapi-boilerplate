from unittest.mock import AsyncMock
from uuid import UUID as uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.user_dto import UserCreateDTO, UserUpdateDTO
from app.services.user_service import UserService


def make_user_data(email="user@example.com", name="User", password="123456"):
    return UserCreateDTO(name=name, email=email, password=password)


class DummyRepo:
    def __init__(self, user=None):
        self._user = user
        self.called_with = None

    async def get_by_email(self, email):
        self.called_with = email
        return self._user


@pytest.mark.asyncio
async def test_get_user_by_email_found(monkeypatch):
    user_obj = object()

    async def dummy_repo_init(self, db):
        self.get_by_email = DummyRepo(user_obj).get_by_email

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.__init__",
        lambda self, db: None,
    )
    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_email",
        DummyRepo(user_obj).get_by_email,
    )
    service = UserService(AsyncMock(spec=AsyncSession))
    result = await service.get_user_by_email("test@example.com")
    assert result is user_obj


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(monkeypatch):
    async def dummy_repo_init(self, db):
        self.get_by_email = DummyRepo(None).get_by_email

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.__init__",
        lambda self, db: None,
    )
    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_email",
        DummyRepo(None).get_by_email,
    )
    service = UserService(AsyncMock(spec=AsyncSession))
    result = await service.get_user_by_email("notfound@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(db_session):
    service = UserService(db_session)
    id = uuid("3455e9b2-8c1a-4d5f-9c3a-123456789abc")
    assert await service.get_user_by_id(id) is None


@pytest.mark.asyncio
async def test_update_user_not_found(db_session):
    service = UserService(db_session)
    update = UserUpdateDTO(name="New Name")
    id = uuid("3455e9b2-8c1a-4d5f-9c3a-123456789abc")
    assert await service.update_user(id, update) is None


@pytest.mark.asyncio
async def test_delete_user_not_found(db_session):
    service = UserService(db_session)
    id = uuid("3455e9b2-8c1a-4d5f-9c3a-123456789abc")
    assert await service.delete_user(id) is False


@pytest.mark.asyncio
async def test_list_users_empty(db_session):
    service = UserService(db_session)
    assert await service.list_users() == []


@pytest.mark.asyncio
async def test_create_user_duplicate_email(db_session):
    service = UserService(db_session)
    await service.create_user(make_user_data(email="duplicate@example.com"))
    with pytest.raises(Exception) as exc_info:
        await service.create_user(make_user_data(email="duplicate@example.com"))
    assert "A user with this email already exists." in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_and_delete_user(db_session):
    service = UserService(db_session)
    user = await service.create_user(make_user_data())
    assert isinstance(user, User)
    assert await service.delete_user(user.id) is True


@pytest.mark.asyncio
async def test_update_user(db_session):
    service = UserService(db_session)
    user = await service.create_user(make_user_data(email="update@example.com"))
    update = UserUpdateDTO(name="Updated")
    updated = await service.update_user(user.id, update)
    assert updated is not None
    assert updated.name == "Updated"


@pytest.mark.asyncio
async def test_list_users(db_session):
    service = UserService(db_session)
    user = await service.create_user(  # noqa: F841
        make_user_data(email="list@example.com")
    )
    users = await service.list_users()
    assert any(u.email == "list@example.com" for u in users)
