from uuid import uuid4

import pytest

from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.post_dto import PostCreate
from app.schemas.user_dto import UserCreateDTO


def make_post_data(title="Test Post", text="Test content", media_url=None):
    return PostCreate(title=title, text=text, media_url=media_url)


@pytest.mark.asyncio
async def test_get_post_by_id_not_found(db_session):
    repo = PostRepository(db_session)
    post_id = uuid4()
    result = await repo.get_post_by_id(post_id)
    assert result is None


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

    repo = PostRepository(db_session)
    post_data = make_post_data(title="New Post", text="New content")
    result = await repo.create_post(post_data, user.id)

    assert result.title == "New Post"
    assert result.text == "New content"
    assert result.created_by == user.id
    assert result.is_deleted is False


@pytest.mark.asyncio
async def test_list_by_user_success(db_session, fast_hash):
    # Create user and posts
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test2@example.com",
            password="test_password",
        )
    )

    repo = PostRepository(db_session)
    post1 = await repo.create_post(make_post_data(title="Post 1"), user.id)
    post2 = await repo.create_post(make_post_data(title="Post 2"), user.id)

    result = await repo.list_by_user(user.id, page=1, items_per_page=10)

    assert len(result) == 2
    assert result[0].id == post1.id
    assert result[1].id == post2.id


@pytest.mark.asyncio
async def test_list_by_user_pagination(db_session, fast_hash):
    # Create user and multiple posts
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test3@example.com",
            password="test_password",
        )
    )

    repo = PostRepository(db_session)
    for i in range(5):
        await repo.create_post(make_post_data(title=f"Post {i}"), user.id)

    # Test pagination
    page1 = await repo.list_by_user(user.id, page=1, items_per_page=2)
    page2 = await repo.list_by_user(user.id, page=2, items_per_page=2)

    assert len(page1) == 2
    assert len(page2) == 2


@pytest.mark.asyncio
async def test_list_by_user_empty(db_session, fast_hash):
    # Create user but no posts
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test4@example.com",
            password="test_password",
        )
    )

    repo = PostRepository(db_session)
    result = await repo.list_by_user(user.id, page=1, items_per_page=10)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_by_id_and_user_success(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test5@example.com",
            password="test_password",
        )
    )

    repo = PostRepository(db_session)
    post = await repo.create_post(make_post_data(), user.id)

    result = await repo.get_by_id_and_user(post.id, user.id)

    assert result is not None
    assert result.id == post.id
    assert result.created_by == user.id


@pytest.mark.asyncio
async def test_get_by_id_and_user_not_found(db_session, fast_hash):
    # Create user but wrong post/user combo
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

    repo = PostRepository(db_session)
    post = await repo.create_post(make_post_data(), user1.id)

    # Try to get with different user
    result = await repo.get_by_id_and_user(post.id, user2.id)

    assert result is None


@pytest.mark.asyncio
async def test_get_active_by_id_success(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test6@example.com",
            password="test_password",
        )
    )

    repo = PostRepository(db_session)
    post = await repo.create_post(make_post_data(), user.id)

    result = await repo.get_active_by_id(post.id)

    assert result is not None
    assert result.id == post.id


@pytest.mark.asyncio
async def test_get_active_by_id_deleted(db_session, fast_hash):
    # Create user and post, then soft delete
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test7@example.com",
            password="test_password",
        )
    )

    repo = PostRepository(db_session)
    post = await repo.create_post(make_post_data(), user.id)
    await repo.soft_delete(post)

    result = await repo.get_active_by_id(post.id)

    assert result is None


@pytest.mark.asyncio
async def test_update_post_success(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test8@example.com",
            password="test_password",
        )
    )

    repo = PostRepository(db_session)
    post = await repo.create_post(make_post_data(title="Original"), user.id)

    # Update the post
    update_data: dict[str, object] = {"title": "Updated"}
    await repo.update_post(post, update_data)

    result = await repo.get_by_id_and_user(post.id, user.id)
    assert result is not None
    assert result.title == "Updated"


@pytest.mark.asyncio
async def test_soft_delete_success(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test9@example.com",
            password="test_password",
        )
    )

    repo = PostRepository(db_session)
    post = await repo.create_post(make_post_data(), user.id)

    # Soft delete
    await repo.soft_delete(post)

    # Verify it's marked as deleted
    result = await repo.get_by_id_and_user(post.id, user.id)
    assert result is None


@pytest.mark.asyncio
async def test_hard_delete_success(db_session, fast_hash):
    # Create user and post
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        UserCreateDTO(
            name="Test User",
            email="test10@example.com",
            password="test_password",
        )
    )

    repo = PostRepository(db_session)
    post = await repo.create_post(make_post_data(), user.id)
    post_id = post.id

    # Hard delete
    await repo.hard_delete(post)

    # Verify it's completely removed
    result = await repo.get_post_by_id(post_id)
    assert result is None


@pytest.mark.asyncio
async def test_safe_commit_rollback_on_error(db_session):
    """Covers BaseRepository._safe_commit rollback on SQLAlchemyError (lines 12-14)."""
    from unittest.mock import AsyncMock, patch

    from sqlalchemy.exc import SQLAlchemyError

    from app.repositories.base_repository import BaseRepository

    repo = BaseRepository(db_session)
    with patch.object(db_session, "commit", side_effect=SQLAlchemyError("forced")):
        with patch.object(
            db_session, "rollback", new_callable=AsyncMock
        ) as mock_rollback:
            with pytest.raises(SQLAlchemyError):
                await repo._safe_commit()
            mock_rollback.assert_called_once()
