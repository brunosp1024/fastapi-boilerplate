import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment BEFORE any imports
os.environ["APP_ENV"] = "test"

from app.db.models.base import Base  # noqa: I001
import app.db.models  # noqa: F401, I001

# Use a named in-memory database that can be shared
SQLALCHEMY_DATABASE_URL = "sqlite:///file:testdb?mode=memory&cache=shared&uri=true"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "uri": True}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Cria o banco uma vez por módulo e limpa as tabelas entre os testes
@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def clean_tables(db_session):
    # Limpa todas as tabelas antes de cada teste
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()

@pytest.fixture(scope="module")
def client(db_session):
    """Create a test client with database dependency override."""
    # Import app after setting test environment
    from app.main import app  # noqa: I001
    from app.db.base import get_db  # noqa: I001

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def fast_hash(monkeypatch):
    # Substitui o hash_password e verify_password por funções rápidas
    import app.core.security
    monkeypatch.setattr(app.core.security, "hash_password", lambda pwd: f"fakehash${pwd}")
    monkeypatch.setattr(app.core.security, "verify_password", lambda pwd, hashed: hashed == f"fakehash${pwd}")
