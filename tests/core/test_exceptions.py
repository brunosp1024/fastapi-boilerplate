"""Tests for exception class instantiation — covers missing __init__ bodies."""

from app.core.exceptions.http_exceptions import (
    BadRequestException,
    CustomException,
    DuplicateValueException,
    RateLimitException,
    UnauthorizedException,
    UnprocessableEntityException,
)

# ── http exceptions ───────────────────────────────────────────────────────────


def test_custom_exception_default():
    ex = CustomException()
    assert "custom exception" in ex.message.lower()
    assert str(ex) == ex.message


def test_bad_request_exception_default():
    ex = BadRequestException()
    assert ex.message == "Bad request."


def test_unauthorized_exception_default():
    ex = UnauthorizedException()
    assert "Unauthorized" in ex.message


def test_unprocessable_entity_exception_default():
    ex = UnprocessableEntityException()
    assert "Unprocessable" in ex.message


def test_duplicate_value_exception_default():
    ex = DuplicateValueException()
    assert "Duplicate" in ex.message


def test_rate_limit_exception_default():
    ex = RateLimitException()
    assert "Rate limit" in ex.message
