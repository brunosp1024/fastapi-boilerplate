"""Tests for exception class instantiation — covers missing __init__ bodies."""

from app.core.exceptions.cache_exceptions import (
    CacheIdentificationInferenceError,
    InvalidRequestError,
    MissingClientError,
)
from app.core.exceptions.http_exceptions import (
    BadRequestException,
    CustomException,
    DuplicateValueException,
    RateLimitException,
    UnauthorizedException,
    UnprocessableEntityException,
)

# ── cache exceptions ──────────────────────────────────────────────────────────


def test_cache_identification_inference_error_custom_message():
    ex = CacheIdentificationInferenceError("custom id error")
    assert ex.message == "custom id error"
    assert str(ex) == "custom id error"


def test_invalid_request_error_custom_message():
    ex = InvalidRequestError("custom request error")
    assert ex.message == "custom request error"


def test_missing_client_error_custom_message():
    ex = MissingClientError("custom client error")
    assert ex.message == "custom client error"


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
