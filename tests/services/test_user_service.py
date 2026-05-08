from app.db.models.user import User
from app.schemas.user_dto import UserCreateDTO, UserUpdateDTO
from app.services.user_service import UserService


def make_user_data(email="user@example.com", name="User", password="123456"):
    return UserCreateDTO(name=name, email=email, password=password)


def test_get_user_by_id_not_found(db_session):
    service = UserService(db_session)
    assert service.get_user_by_id(9999) is None


def test_update_user_not_found(db_session):
    service = UserService(db_session)
    update = UserUpdateDTO(name="New Name")
    assert service.update_user(9999, update) is None


def test_delete_user_not_found(db_session):
    service = UserService(db_session)
    assert service.delete_user(9999) is False


def test_list_users_empty(db_session):
    service = UserService(db_session)
    assert service.list_users() == []


def test_create_and_delete_user(db_session):
    service = UserService(db_session)
    user = service.create_user(make_user_data())
    assert isinstance(user, User)
    assert service.delete_user(user.id) is True


def test_update_user(db_session):
    service = UserService(db_session)
    user = service.create_user(make_user_data(email="update@example.com"))
    update = UserUpdateDTO(name="Updated")
    updated = service.update_user(user.id, update)
    assert updated.name == "Updated"


def test_list_users(db_session):
    service = UserService(db_session)
    user = service.create_user(make_user_data(email="list@example.com"))  # noqa: F841
    users = service.list_users()
    assert any(u.email == "list@example.com" for u in users)
