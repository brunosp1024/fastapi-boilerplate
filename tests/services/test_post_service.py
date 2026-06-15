from uuid import uuid4

import pytest

from app.core.exceptions.http_exceptions import ForbiddenException, NotFoundException
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.post_dto import PostCreate, PostUpdate
from app.schemas.user_dto import UserCreateDTO
from app.services.post_service import PostService


@pytest.mark.asyncio
async def test_create_post_success(db_session, fast_hash):
    # Create user first
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test@example.com",
            password="test_password",
        )
    )

    service = PostService(db_session)
    post_data = PostCreate(title="Test", text="Content", media_url=None)
    result = await service.create_post(post_data, user.id)

    assert result.title == "Test"
    assert result.text == "Content"
    assert result.created_by == user.id


@pytest.mark.asyncio
async def test_create_post_user_not_found(db_session):
    service = PostService(db_session)
    post_data = PostCreate(title="Test", text="Content", media_url=None)
    user_id = uuid4()

    with pytest.raises(NotFoundException, match="User not found"):
        await service.create_post(post_data, user_id)


@pytest.mark.asyncio
async def test_read_posts_success(db_session, fast_hash):
    # Create user and posts
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test2@example.com",
            password="test_password",
        )
    )

    post_repo = PostRepository(db_session)
    _ = await post_repo.create_post(
        PostCreate(title="Post 1", text="Content 1", media_url=None), user.id
    )
    _ = await post_repo.create_post(
        PostCreate(title="Post 2", text="Content 2", media_url=None), user.id
    )
    assert user.name is not None
    service = PostService(db_session)
    result = await service.read_posts(user.name, page=1, items_per_page=10)

    assert len(result) == 2
    assert result[0].title == "Post 1"
    assert result[1].title == "Post 2"


@pytest.mark.asyncio
async def test_read_posts_user_not_found(db_session):
    service = PostService(db_session)

    with pytest.raises(NotFoundException, match="User not found"):
        await service.read_posts("nonexistent", page=1, items_per_page=10)


@pytest.mark.asyncio
async def test_read_post_success(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test3@example.com",
            password="test_password",
        )
    )

    post_repo = PostRepository(db_session)
    post = await post_repo.create_post(
        PostCreate(title="Post", text="Content", media_url=None), user.id
    )

    assert user.name is not None
    service = PostService(db_session)
    result = await service.read_post(user.name, post.id)

    assert result.id == post.id
    assert result.title == "Post"


@pytest.mark.asyncio
async def test_read_post_not_found(db_session, fast_hash):
    # Create user but no post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test4@example.com",
            password="test_password",
        )
    )

    assert user.name is not None
    service = PostService(db_session)
    post_id = uuid4()

    with pytest.raises(NotFoundException, match="Post not found"):
        await service.read_post(user.name, post_id)


@pytest.mark.asyncio
async def test_patch_post_success(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test5@example.com",
            password="test_password",
        )
    )

    post_repo = PostRepository(db_session)
    post = await post_repo.create_post(
        PostCreate(title="Original", text="Content", media_url=None), user.id
    )

    assert user.name is not None
    service = PostService(db_session)
    update_data = PostUpdate(title="Updated", text="Updated content", media_url=None)
    await service.patch_post(user.name, post.id, update_data, user.id)

    updated_post = await post_repo.get_by_id_and_user(post.id, user.id)
    assert updated_post is not None
    assert updated_post.title == "Updated"


@pytest.mark.asyncio
async def test_patch_post_forbidden(db_session, fast_hash):
    # Create two users
    user_repo = UserRepository(db_session)
    user1 = await user_repo.create(
        UserCreateDTO(
            name="User 1",
            email="user1@example.com",
            password="test_password",
        )
    )
    user2 = await user_repo.create(
        UserCreateDTO(
            name="User 2",
            email="user2@example.com",
            password="test_password",
        )
    )

    post_repo = PostRepository(db_session)
    post = await post_repo.create_post(
        PostCreate(title="Post", text="Content", media_url=None), user1.id
    )

    assert user1.name is not None
    service = PostService(db_session)
    update_data = PostUpdate(title="Updated", text=None, media_url=None)

    with pytest.raises(ForbiddenException):
        await service.patch_post(user1.name, post.id, update_data, user2.id)


@pytest.mark.asyncio
async def test_patch_post_not_found(db_session, fast_hash):
    # Create user but no post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test6@example.com",
            password="test_password",
        )
    )

    assert user.name is not None
    service = PostService(db_session)
    post_id = uuid4()
    update_data = PostUpdate(title="Updated", text=None, media_url=None)

    with pytest.raises(NotFoundException, match="Post not found"):
        await service.patch_post(user.name, post_id, update_data, user.id)


@pytest.mark.asyncio
async def test_erase_post_success(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test7@example.com",
            password="test_password",
        )
    )

    post_repo = PostRepository(db_session)
    post = await post_repo.create_post(
        PostCreate(title="Post", text="Content", media_url=None), user.id
    )

    assert user.name is not None
    service = PostService(db_session)
    await service.erase_post(user.name, post.id, user.id)

    deleted_post = await post_repo.get_by_id_and_user(post.id, user.id)
    assert deleted_post is None


@pytest.mark.asyncio
async def test_erase_post_forbidden(db_session, fast_hash):
    # Create two users
    user_repo = UserRepository(db_session)
    user1 = await user_repo.create(
        UserCreateDTO(
            name="User 1",
            email="user1b@example.com",
            password="test_password",
        )
    )
    user2 = await user_repo.create(
        UserCreateDTO(
            name="User 2",
            email="user2b@example.com",
            password="test_password",
        )
    )

    post_repo = PostRepository(db_session)
    post = await post_repo.create_post(
        PostCreate(title="Post", text="Content", media_url=None), user1.id
    )

    assert user1.name is not None
    service = PostService(db_session)

    with pytest.raises(ForbiddenException):
        await service.erase_post(user1.name, post.id, user2.id)


@pytest.mark.asyncio
async def test_erase_post_not_found(db_session, fast_hash):
    # Create user but no post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test8@example.com",
            password="test_password",
        )
    )

    assert user.name is not None
    service = PostService(db_session)
    post_id = uuid4()

    with pytest.raises(NotFoundException, match="Post not found"):
        await service.erase_post(user.name, post_id, user.id)


@pytest.mark.asyncio
async def test_erase_db_post_success(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test9@example.com",
            password="test_password",
        )
    )

    post_repo = PostRepository(db_session)
    post = await post_repo.create_post(
        PostCreate(title="Post", text="Content", media_url=None), user.id
    )

    assert user.name is not None
    service = PostService(db_session)
    await service.erase_db_post(user.name, post.id, "admin")

    deleted_post = await post_repo.get_active_by_id(post.id)
    assert deleted_post is None


@pytest.mark.asyncio
async def test_erase_db_post_not_admin(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test10@example.com",
            password="test_password",
        )
    )

    post_repo = PostRepository(db_session)
    post = await post_repo.create_post(
        PostCreate(title="Post", text="Content", media_url=None), user.id
    )

    assert user.name is not None
    service = PostService(db_session)

    with pytest.raises(ForbiddenException):
        await service.erase_db_post(user.name, post.id, "user")


@pytest.mark.asyncio
async def test_erase_db_post_not_found(db_session, fast_hash):
    # Create user but no post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test11@example.com",
            password="test_password",
        )
    )

    assert user.name is not None
    service = PostService(db_session)
    post_id = uuid4()

    with pytest.raises(NotFoundException, match="Post not found"):
        await service.erase_db_post(user.name, post_id, "admin")


@pytest.mark.asyncio
async def test_create_post_forbidden_when_user_id_mismatch(db_session, monkeypatch):
    """Covers the `if current_user_id != user.id: raise ForbiddenException()` branch."""
    from unittest.mock import MagicMock

    service = PostService(db_session)
    different_user_id = uuid4()
    current_user_id = uuid4()

    fake_user = MagicMock()
    fake_user.id = different_user_id  # differs from current_user_id

    async def fake_get_user_by_id(self, uid):
        return fake_user

    monkeypatch.setattr(PostService, "_get_user_by_id", fake_get_user_by_id)

    post_data = PostCreate(title="Test", text="Content", media_url=None)
    with pytest.raises(ForbiddenException):
        await service.create_post(post_data, current_user_id)
