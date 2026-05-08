from app.db import base


# Testa init_db e get_db de app.db.base
def test_init_db_and_get_db(monkeypatch):
    # Força modo debug para testar drop_all/create_all
    monkeypatch.setattr(base.settings, "APP_DEBUG", True)
    called = {}

    class DummyMeta:
        def drop_all(self, bind=None):
            called["drop"] = True

        def create_all(self, bind=None):
            called["create"] = True

    monkeypatch.setattr(base, "Base", type("Base", (), {"metadata": DummyMeta()})())
    base.init_db()
    assert called["drop"] and called["create"]

    # Testa get_db generator
    class DummyDB:
        def close(self):
            pass

    db = DummyDB()
    monkeypatch.setattr(base, "SessionLocal", lambda: db)
    gen = base.get_db()
    assert next(gen) is db
    try:
        next(gen)
    except StopIteration:
        pass
