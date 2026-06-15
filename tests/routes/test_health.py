import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.health_routes import health_check


class DummyDB:
    async def execute(self, stmt):
        if stmt == "fail":
            raise OperationalError("fail", None, Exception("dummy"))

        class DummyResult:
            def scalar_one_or_none(self):
                return True

        return DummyResult()


def test_health_check_healthy():
    db = AsyncMock(spec=AsyncSession)
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = True
    db.execute.return_value = mock_result
    result = asyncio.run(health_check(db))
    assert result.status == "healthy"
    assert result.database == "healthy"
    assert result.timestamp is not None
    assert result.version == "1.0.0"


def test_health_check_unhealthy():
    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = Exception("db error")
    result = asyncio.run(health_check(db))
    assert result.status == "degraded"
    assert result.database.startswith("unhealthy:")
    assert result.timestamp is not None
    assert result.version == "1.0.0"


@pytest.mark.asyncio
async def test_root(client):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
