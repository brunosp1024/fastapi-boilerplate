from app.core.config import settings


def test_config_defaults():
    assert settings.DB_ENGINE
    assert settings.DB_USER
    assert settings.DB_PASSWORD
    assert settings.DB_HOST
    assert settings.DB_PORT
    assert settings.DB_NAME
    assert settings.APP_SECRET_KEY
    assert settings.JWT_ALGORITHM
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS
    assert settings.APP_DEBUG in [True, False]


def test_config_database_url():
    url = settings.DATABASE_URL
    assert settings.DB_USER in url
    assert settings.DB_NAME in url
    assert settings.DB_HOST in url

def test_config_database_url_testing(monkeypatch):
    monkeypatch.setenv("TESTING", "True")
    from app.core.config import settings as test_settings
    url = test_settings.DATABASE_URL
    assert url.startswith("sqlite://") or "DATABASE_URL" in url
