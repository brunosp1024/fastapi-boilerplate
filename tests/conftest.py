import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Set test environment BEFORE any imports
os.environ["APP_ENV"] = "test"

import app.db.models  # noqa: F401, E402, I001
from app.core.config import settings  # noqa: E402
from app.db.base import async_get_db  # noqa: E402
from app.db.models.base import Base  # noqa: E402, I001
from app.main import app as fastapi_app  # noqa: E402

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AsyncTestSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# Override the async_get_db dependency to use the test database
async def override_async_get_db():
    async with AsyncTestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


fastapi_app.dependency_overrides[async_get_db] = override_async_get_db


# Cria o schema do banco uma vez por módulo e limpa as tabelas entre os testes
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Limpa as tabelas entre os testes para isolamento
@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# Create the database once per function and clean tables between tests
@pytest_asyncio.fixture
async def db_session():
    async with AsyncTestSessionLocal() as db:
        yield db


# Fixture client async
@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"  # type: ignore[arg-type, unused-ignore]
    ) as c:
        yield c


# Fixture to replace the hash_password and verify_password functions with no-op for faster tests
@pytest_asyncio.fixture
def fast_hash(monkeypatch):
    import app.core.security

    monkeypatch.setattr(
        app.core.security, "hash_password", lambda pwd: f"fakehash${pwd}"
    )
    monkeypatch.setattr(
        app.core.security,
        "verify_password",
        lambda pwd, hashed: hashed == f"fakehash${pwd}",
    )
