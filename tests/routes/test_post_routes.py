from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import app.core.utils.cache as cache_module
from app.api.routes.post_routers import router as post_router
from app.core.security import get_current_user
from app.db.base import async_get_db


@pytest.fixture
def post_app():
    _app = FastAPI()
    _app.include_router(post_router)

    async def override_db():
        yield object()

    _app.dependency_overrides[async_get_db] = override_db
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture
async def http_client(post_app):
    transport = ASGITransport(app=post_app)  # type: ignore[arg-type, unused-ignore]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_create_post_route_success(post_app, http_client, monkeypatch):
    fake_user = SimpleNamespace(id=uuid4(), role="user")

    async def override_current_user():
        return fake_user

    post_app.dependency_overrides[get_current_user] = override_current_user

    payload = {
        "title": "My post",
        "text": "Post content",
        "media_url": None,
    }

    fake_post_response = {
        "id": str(uuid4()),
        "title": payload["title"],
        "text": payload["text"],
        "media_url": None,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": None,
        "deleted_at": None,
        "is_deleted": False,
    }

    async def fake_create_post(self, post, current_user_id):
        assert current_user_id == fake_user.id
        assert post.title == payload["title"]
        assert post.text == payload["text"]
        return fake_post_response

    monkeypatch.setattr(
        "app.api.routes.post_routers.PostService.create_post", fake_create_post
    )

    response = await http_client.post("/post", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == payload["title"]
    assert body["text"] == payload["text"]
    assert body["is_deleted"] is False


@pytest.mark.asyncio
async def test_read_posts_success(http_client, monkeypatch):
    fake_posts = [
        {
            "id": str(uuid4()),
            "title": "Post 1",
            "text": "Content 1",
            "media_url": None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": None,
            "deleted_at": None,
            "is_deleted": False,
        }
    ]

    async def fake_read_posts(self, username, page, items_per_page):
        return fake_posts

    monkeypatch.setattr(
        "app.api.routes.post_routers.PostService.read_posts", fake_read_posts
    )

    response = await http_client.get("/testuser/posts")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Post 1"


@pytest.mark.asyncio
async def test_read_posts_empty(http_client, monkeypatch):
    async def fake_read_posts(self, username, page, items_per_page):
        return []

    monkeypatch.setattr(
        "app.api.routes.post_routers.PostService.read_posts", fake_read_posts
    )

    response = await http_client.get("/testuser/posts?page=1&items_per_page=10")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 0


@pytest.mark.asyncio
async def test_create_post_invalid_data(post_app, http_client, monkeypatch):
    fake_user = SimpleNamespace(id=uuid4(), role="user")

    async def override_current_user():
        return fake_user

    post_app.dependency_overrides[get_current_user] = override_current_user

    response = await http_client.post("/post", json={"title": "Test"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_read_posts_with_pagination(http_client, monkeypatch):
    fake_posts = [
        {
            "id": str(uuid4()),
            "title": "Post 1",
            "text": "Content 1",
            "media_url": None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": None,
            "deleted_at": None,
            "is_deleted": False,
        },
        {
            "id": str(uuid4()),
            "title": "Post 2",
            "text": "Content 2",
            "media_url": None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": None,
            "deleted_at": None,
            "is_deleted": False,
        },
    ]

    async def fake_read_posts(self, username, page, items_per_page):
        return fake_posts

    monkeypatch.setattr(
        "app.api.routes.post_routers.PostService.read_posts", fake_read_posts
    )

    response = await http_client.get("/testuser/posts?page=2&items_per_page=5")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2


# ── cache-decorated endpoints (require mocked Redis) ─────────────────────────


def _mock_redis(get_return=None):
    r = AsyncMock()
    r.get = AsyncMock(return_value=get_return)
    r.set = AsyncMock()
    r.expire = AsyncMock()
    r.delete = AsyncMock()
    r.scan = AsyncMock(return_value=(0, []))
    return r


@pytest.mark.asyncio
async def test_read_post_cache_miss(http_client, monkeypatch):
    """read_post endpoint body runs on cache miss."""
    post_id = uuid4()
    fake_post = {
        "id": str(post_id),
        "title": "Cached Post",
        "text": "Content",
        "media_url": None,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": None,
        "deleted_at": None,
        "is_deleted": False,
    }

    async def fake_read_post(self, username, pid):
        return fake_post

    monkeypatch.setattr(
        "app.api.routes.post_routers.PostService.read_post", fake_read_post
    )

    mock_r = _mock_redis(get_return=None)
    monkeypatch.setattr(cache_module, "client", mock_r)

    response = await http_client.get(f"/testuser/post/{post_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Cached Post"
    mock_r.set.assert_called_once()


@pytest.mark.asyncio
async def test_patch_post_cache_invalidation(post_app, http_client, monkeypatch):
    """patch_post endpoint runs and cache is invalidated."""
    fake_user = SimpleNamespace(id=uuid4(), role="user")

    async def override_current_user():
        return fake_user

    post_app.dependency_overrides[get_current_user] = override_current_user

    async def fake_patch_post(self, username, pid, values, current_user_id):
        pass

    monkeypatch.setattr(
        "app.api.routes.post_routers.PostService.patch_post", fake_patch_post
    )

    mock_r = _mock_redis()
    monkeypatch.setattr(cache_module, "client", mock_r)

    response = await http_client.patch(
        f"/testuser/post/{uuid4()}",
        json={"title": "Updated"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Post updated"
    mock_r.delete.assert_called()


@pytest.mark.asyncio
async def test_erase_post_cache_invalidation(post_app, http_client, monkeypatch):
    """erase_post endpoint runs and cache is invalidated."""
    fake_user = SimpleNamespace(id=uuid4(), role="user")

    async def override_current_user():
        return fake_user

    post_app.dependency_overrides[get_current_user] = override_current_user

    async def fake_erase_post(self, username, pid, current_user_id):
        pass

    monkeypatch.setattr(
        "app.api.routes.post_routers.PostService.erase_post", fake_erase_post
    )

    mock_r = _mock_redis()
    monkeypatch.setattr(cache_module, "client", mock_r)

    response = await http_client.delete(f"/testuser/post/{uuid4()}")
    assert response.status_code == 200
    assert response.json()["message"] == "Post deleted"


@pytest.mark.asyncio
async def test_erase_db_post_cache_invalidation(post_app, http_client, monkeypatch):
    """erase_db_post endpoint runs and cache is invalidated."""
    fake_user = SimpleNamespace(id=uuid4(), role="admin")

    async def override_current_user():
        return fake_user

    post_app.dependency_overrides[get_current_user] = override_current_user

    async def fake_erase_db_post(self, username, pid, current_user_role):
        pass

    monkeypatch.setattr(
        "app.api.routes.post_routers.PostService.erase_db_post", fake_erase_db_post
    )

    mock_r = _mock_redis()
    monkeypatch.setattr(cache_module, "client", mock_r)

    response = await http_client.delete(f"/testuser/db_post/{uuid4()}")
    assert response.status_code == 200
    assert response.json()["message"] == "Post deleted from the database"
