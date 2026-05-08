import asyncio

from sqlalchemy.exc import OperationalError

from app.api.routes.health_routes import health_check


class DummyDB:
    def execute(self, stmt):
        if stmt == "fail":
            raise OperationalError("fail", None, None)
        return True

def test_health_check_healthy():
    db = DummyDB()
    result = asyncio.run(health_check(db))
    assert result["status"] == "healthy"
    assert result["database"] == "healthy"
    assert "timestamp" in result
    assert result["version"] == "1.0.0"

def test_health_check_unhealthy():
    class FailingDB:
        def execute(self, stmt):
            raise Exception("db error")
    db = FailingDB()
    result = asyncio.run(health_check(db))
    assert result["status"] == "degraded"
    assert result["database"].startswith("unhealthy:")
    assert "timestamp" in result
    assert result["version"] == "1.0.0"
