"""Tests for Pydantic schema mixin serializers — covers None/non-None branches."""

from datetime import UTC, datetime

from app.schemas.mixins import PersistentDeletion, TimestampSchema


def test_timestamp_serialize_created_at_none():
    """serialize_dt returns None when created_at is None (line 33)."""
    # Force created_at to None via model_construct (bypasses validation)
    schema = TimestampSchema.model_construct(created_at=None, updated_at=None)
    dumped = schema.model_dump(mode="json")
    assert dumped["created_at"] is None


def test_persistent_deletion_serialize_deleted_at_not_none():
    """serialize_dates returns isoformat string when deleted_at is set (line 52)."""
    now = datetime.now(UTC)
    schema = PersistentDeletion(deleted_at=now, is_deleted=True)
    dumped = schema.model_dump(mode="json")
    assert dumped["deleted_at"] is not None
    assert "T" in dumped["deleted_at"]  # ISO 8601 format
