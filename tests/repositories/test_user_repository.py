from datetime import datetime

from app.repositories.user_repository import UserRepository
from app.schemas.user_dto import UserCreateDTO, UserUpdateDTO


def make_user_data(email="repo@example.com", name="Repo", password="123456"):
    return UserCreateDTO(name=name, email=email, password=password)

def test_get_by_id_not_found(db_session):
    repo = UserRepository(db_session)
    assert repo.get_by_id(9999) is None

def test_get_by_email_not_found(db_session):
    repo = UserRepository(db_session)
    assert repo.get_by_email("notfound@x.com") is None

def test_update_user_not_found(db_session):
    repo = UserRepository(db_session)
    update = UserUpdateDTO(name="New Name")
    assert repo.update(9999, update) is None

def test_delete_user_not_found(db_session):
    repo = UserRepository(db_session)
    assert repo.delete(9999) is False

def test_update_user_password(db_session):
    repo = UserRepository(db_session)
    user = repo.create(make_user_data(email="pwchange@x.com"))
    old_hash = user.hashed_password
    update = UserUpdateDTO(password="newpass123")
    updated = repo.update(user.id, update)
    assert updated.hashed_password != old_hash

def test_update_user_fields(db_session):
    repo = UserRepository(db_session)
    user = repo.create(make_user_data(email="fields@x.com"))
    update = UserUpdateDTO(name="Changed", email="changed@x.com")
    updated = repo.update(user.id, update)
    assert updated.name == "Changed"
    assert updated.email == "changed@x.com"
    assert isinstance(updated.updated_at, datetime)

def test_delete_user_success(db_session):
    repo = UserRepository(db_session)
    user = repo.create(make_user_data(email="del@x.com"))
    assert repo.delete(user.id) is True

def test_create_user_sets_admin_role(db_session, monkeypatch):
    from app.core import config
    repo = UserRepository(db_session)
    # Garante que APP_DEBUG está True
    monkeypatch.setattr(config.settings, "APP_DEBUG", True)
    user = repo.create(make_user_data(email="adminuser@x.com"))
    assert user.role == "admin"
