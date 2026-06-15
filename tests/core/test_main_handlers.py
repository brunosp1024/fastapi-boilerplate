"""Tests for main.py exception handlers via HTTP — avoids importing decorated symbols."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions.http_exceptions import (
    BadRequestException,
    CustomException,
    DuplicateValueException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
    UnprocessableEntityException,
)
from app.main import app as main_app


def _route_app() -> FastAPI:
    """Minimal FastAPI app that raises each exception type, with main_app handlers."""
    test_app = FastAPI()

    # Copy all exception handlers from main_app (includes the generic Exception one)
    for exc_type, handler in main_app.exception_handlers.items():
        test_app.add_exception_handler(exc_type, handler)

    @test_app.get("/bad-request")
    async def raise_bad_request():
        raise BadRequestException("bad request test")

    @test_app.get("/not-found")
    async def raise_not_found():
        raise NotFoundException("not found test")

    @test_app.get("/forbidden")
    async def raise_forbidden():
        raise ForbiddenException("forbidden test")

    @test_app.get("/unauthorized")
    async def raise_unauthorized():
        raise UnauthorizedException("unauthorized test")

    @test_app.get("/unprocessable")
    async def raise_unprocessable():
        raise UnprocessableEntityException("unprocessable test")

    @test_app.get("/duplicate")
    async def raise_duplicate():
        raise DuplicateValueException("duplicate test")

    @test_app.get("/rate-limit")
    async def raise_rate_limit():
        raise RateLimitException("rate limit test")

    @test_app.get("/custom")
    async def raise_custom():
        raise CustomException("custom test")

    @test_app.get("/sqlalchemy")
    async def raise_sqlalchemy():
        raise SQLAlchemyError("db error")

    @test_app.get("/generic")
    async def raise_generic():
        raise RuntimeError("generic error")

    return test_app


@pytest.fixture
async def handler_client():
    transport = ASGITransport(app=_route_app(), raise_app_exceptions=False)  # type: ignore[arg-type, unused-ignore]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_bad_request_handler(handler_client):
    r = await handler_client.get("/bad-request")
    assert r.status_code == 400
    assert r.json()["detail"] == "bad request test"


@pytest.mark.asyncio
async def test_not_found_handler(handler_client):
    r = await handler_client.get("/not-found")
    assert r.status_code == 404
    assert r.json()["detail"] == "not found test"


@pytest.mark.asyncio
async def test_forbidden_handler(handler_client):
    r = await handler_client.get("/forbidden")
    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden test"


@pytest.mark.asyncio
async def test_unauthorized_handler(handler_client):
    r = await handler_client.get("/unauthorized")
    assert r.status_code == 401
    assert r.json()["detail"] == "unauthorized test"


@pytest.mark.asyncio
async def test_unprocessable_entity_handler(handler_client):
    r = await handler_client.get("/unprocessable")
    assert r.status_code == 422
    assert r.json()["detail"] == "unprocessable test"


@pytest.mark.asyncio
async def test_duplicate_value_handler(handler_client):
    r = await handler_client.get("/duplicate")
    assert r.status_code == 409
    assert r.json()["detail"] == "duplicate test"


@pytest.mark.asyncio
async def test_rate_limit_handler(handler_client):
    r = await handler_client.get("/rate-limit")
    assert r.status_code == 429
    assert r.json()["detail"] == "rate limit test"


@pytest.mark.asyncio
async def test_custom_exception_handler(handler_client):
    r = await handler_client.get("/custom")
    assert r.status_code == 400
    assert r.json()["detail"] == "custom test"


@pytest.mark.asyncio
async def test_sqlalchemy_exception_handler(handler_client):
    r = await handler_client.get("/sqlalchemy")
    assert r.status_code == 500
    assert r.json()["detail"] == "Database error"


@pytest.mark.asyncio
async def test_generic_exception_handler(handler_client):
    r = await handler_client.get("/generic")
    assert r.status_code == 500
    assert r.json()["detail"] == "Internal server error"
