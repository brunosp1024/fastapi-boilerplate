"""Tests for cache utility functions and the cache decorator."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.core.utils.cache as cache_module
from app.core.exceptions.cache_exceptions import (
    CacheIdentificationInferenceError,
    InvalidRequestError,
    MissingClientError,
)

# ── pure helper functions ─────────────────────────────────────────────────────


def test_infer_resource_id_int_with_id_in_name():
    result = cache_module._infer_resource_id(
        kwargs={"user_resource_id": 99, "name": "test"},
        resource_id_type=int,
    )
    assert result == 99


def test_infer_resource_id_str():
    result = cache_module._infer_resource_id(
        kwargs={"username": "alice"},
        resource_id_type=str,
    )
    assert result == "alice"


def test_infer_resource_id_not_found_raises():
    with pytest.raises(CacheIdentificationInferenceError):
        cache_module._infer_resource_id(
            kwargs={"count": 5},
            resource_id_type=str,
        )


def test_extract_data_inside_brackets():
    result = cache_module._extract_data_inside_brackets("{username}_post:{id}")
    assert result == ["username", "id"]


def test_extract_data_inside_brackets_empty():
    result = cache_module._extract_data_inside_brackets("no_brackets")
    assert result == []


def test_construct_data_dict():
    result = cache_module._construct_data_dict(
        data_inside_brackets=["username", "id"],
        kwargs={"username": "alice", "id": 1, "extra": "ignored"},
    )
    assert result == {"username": "alice", "id": 1}


def test_format_prefix():
    result = cache_module._format_prefix(
        prefix="{username}_posts",
        kwargs={"username": "bob"},
    )
    assert result == "bob_posts"


def test_format_extra_data():
    result = cache_module._format_extra_data(
        to_invalidate_extra={"{username}_posts": "{username}"},
        kwargs={"username": "bob"},
    )
    assert result == {"bob_posts": "bob"}


# ── _delete_keys_by_pattern ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_keys_by_pattern_no_client():
    """When client is None, function returns immediately without error."""
    saved = cache_module.client
    cache_module.client = None
    try:
        await cache_module._delete_keys_by_pattern("test:*")  # must not raise
    finally:
        cache_module.client = saved


@pytest.mark.asyncio
async def test_delete_keys_by_pattern_with_keys():
    mock_redis = AsyncMock()
    # First scan returns cursor=5 with keys, second scan returns cursor=0 (done)
    mock_redis.scan = AsyncMock(
        side_effect=[
            (5, [b"key1", b"key2"]),
            (0, []),
        ]
    )
    mock_redis.delete = AsyncMock()

    saved = cache_module.client
    cache_module.client = mock_redis
    try:
        await cache_module._delete_keys_by_pattern("test:*")
        mock_redis.delete.assert_called_once_with(b"key1", b"key2")
    finally:
        cache_module.client = saved


@pytest.mark.asyncio
async def test_delete_keys_by_pattern_no_keys():
    mock_redis = AsyncMock()
    mock_redis.scan = AsyncMock(return_value=(0, []))
    mock_redis.delete = AsyncMock()

    saved = cache_module.client
    cache_module.client = mock_redis
    try:
        await cache_module._delete_keys_by_pattern("empty:*")
        mock_redis.delete.assert_not_called()
    finally:
        cache_module.client = saved


# ── cache decorator via a minimal FastAPI app ─────────────────────────────────


def _make_test_app():
    """Build a minimal FastAPI app with a cached GET endpoint."""
    from fastapi import FastAPI, Request

    app = FastAPI()

    @app.get("/items/{item_id}")
    @cache_module.cache(key_prefix="items", resource_id_name="item_id")
    async def get_item(request: Request, item_id: int) -> dict:
        return {"item_id": item_id, "value": "fresh"}

    @app.patch("/items/{item_id}")
    @cache_module.cache(
        key_prefix="items",
        resource_id_name="item_id",
        to_invalidate_extra={"users_items": "{item_id}"},
    )
    async def patch_item(request: Request, item_id: int) -> dict:
        return {"updated": True}

    @app.delete("/items/{item_id}")
    @cache_module.cache(
        key_prefix="items",
        resource_id_name="item_id",
        pattern_to_invalidate_extra=["items:*"],
    )
    async def delete_item(request: Request, item_id: int) -> dict:
        return {"deleted": True}

    @app.get("/inferred/{resource_id}")
    @cache_module.cache(key_prefix="inferred", resource_id_type=int)
    async def get_inferred(request: Request, resource_id: int) -> dict:
        return {"resource_id": resource_id}

    @app.get("/invalid/{item_id}")
    @cache_module.cache(
        key_prefix="invalid",
        resource_id_name="item_id",
        to_invalidate_extra={"x": "y"},  # Not valid on GET
    )
    async def get_invalid(request: Request, item_id: int) -> dict:
        return {}

    return app


@pytest.mark.asyncio
async def test_cache_missing_client_raises():
    """cache inner raises MissingClientError when client is None."""
    from unittest.mock import MagicMock

    @cache_module.cache(key_prefix="test", resource_id_name="item_id")
    async def fake_endpoint(request, item_id: int) -> dict:
        return {"id": item_id}

    mock_request = MagicMock()
    mock_request.method = "GET"

    saved = cache_module.client
    cache_module.client = None
    try:
        with pytest.raises(MissingClientError):
            await fake_endpoint(mock_request, item_id=42)
    finally:
        cache_module.client = saved


@pytest.mark.asyncio
async def test_cache_get_cache_miss():
    """GET with a cache miss: endpoint runs and result is cached."""
    from httpx import ASGITransport, AsyncClient

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock()
    mock_redis.expire = AsyncMock()

    app = _make_test_app()
    saved = cache_module.client
    cache_module.client = mock_redis
    try:
        transport = ASGITransport(app=app)  # type: ignore[arg-type, unused-ignore]
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/items/42")
        assert response.status_code == 200
        body = response.json()
        assert body["item_id"] == 42
        mock_redis.set.assert_called_once()
        mock_redis.expire.assert_called_once()
    finally:
        cache_module.client = saved


def test_cache_uses_async_redis_client():
    assert cache_module.Redis.__module__.startswith("redis.asyncio")


@pytest.mark.asyncio
async def test_cache_get_cache_hit():
    """GET with a cache hit: returns stored JSON without calling endpoint."""
    from httpx import ASGITransport, AsyncClient

    cached_payload = json.dumps({"item_id": 7, "value": "cached"}).encode()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=cached_payload)

    app = _make_test_app()
    saved = cache_module.client
    cache_module.client = mock_redis
    try:
        transport = ASGITransport(app=app)  # type: ignore[arg-type, unused-ignore]
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/items/7")
        assert response.status_code == 200
        body = response.json()
        assert body["value"] == "cached"
    finally:
        cache_module.client = saved


@pytest.mark.asyncio
async def test_cache_get_with_to_invalidate_raises_invalid_request():
    """GET with to_invalidate_extra raises InvalidRequestError."""
    from unittest.mock import MagicMock

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    @cache_module.cache(
        key_prefix="test",
        resource_id_name="item_id",
        to_invalidate_extra={"x": "{item_id}"},
    )
    async def fake_endpoint(request, item_id: int) -> dict:
        return {}

    mock_request = MagicMock()
    mock_request.method = "GET"

    saved = cache_module.client
    cache_module.client = mock_redis
    try:
        with pytest.raises(InvalidRequestError):
            await fake_endpoint(mock_request, item_id=5)
    finally:
        cache_module.client = saved


@pytest.mark.asyncio
async def test_cache_patch_invalidates_extra():
    """PATCH: deletes cache key and extra invalidation keys."""
    from httpx import ASGITransport, AsyncClient

    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock()

    app = _make_test_app()
    saved = cache_module.client
    cache_module.client = mock_redis
    try:
        transport = ASGITransport(app=app)  # type: ignore[arg-type, unused-ignore]
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.patch("/items/3")
        assert response.status_code == 200
        assert mock_redis.delete.call_count >= 2
    finally:
        cache_module.client = saved


@pytest.mark.asyncio
async def test_cache_delete_invalidates_pattern():
    """DELETE: deletes cache key and invalidates by pattern."""
    from httpx import ASGITransport, AsyncClient

    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_redis.scan = AsyncMock(return_value=(0, []))

    app = _make_test_app()
    saved = cache_module.client
    cache_module.client = mock_redis
    try:
        transport = ASGITransport(app=app)  # type: ignore[arg-type, unused-ignore]
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.delete("/items/9")
        assert response.status_code == 200
        mock_redis.scan.assert_called()
    finally:
        cache_module.client = saved


@pytest.mark.asyncio
async def test_cache_inferred_resource_id():
    """Cache with resource_id_name=None uses _infer_resource_id."""
    from httpx import ASGITransport, AsyncClient

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock()
    mock_redis.expire = AsyncMock()

    app = _make_test_app()
    saved = cache_module.client
    cache_module.client = mock_redis
    try:
        transport = ASGITransport(app=app)  # type: ignore[arg-type, unused-ignore]
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/inferred/55")
        assert response.status_code == 200
    finally:
        cache_module.client = saved


# ── async_get_redis ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_get_redis():
    mock_pool = MagicMock()
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()

    saved_pool = cache_module.pool
    cache_module.pool = mock_pool
    try:
        with patch("app.core.utils.cache.Redis", return_value=mock_redis):
            collected = []
            async for r in cache_module.async_get_redis():
                collected.append(r)
        assert collected[0] is mock_redis
        mock_redis.aclose.assert_called_once()
    finally:
        cache_module.pool = saved_pool
