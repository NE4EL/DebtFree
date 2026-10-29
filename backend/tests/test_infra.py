import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.config import DEV_SECRET, Settings
from tests.conftest import migrate


def test_health_checks_database(client):
    assert client.get("/api/health").json() == {"status": "ok", "database": "ok"}


def test_migrations_seed_strategies(app):
    from app.db import engine

    with engine.connect() as conn:
        codes = conn.execute(text("SELECT code FROM strategies ORDER BY id")).scalars().all()
    assert codes == ["avalanche", "snowball", "minimum"]


def test_migrations_downgrade_and_upgrade(app):
    from app.db import engine

    migrate("base", downgrade=True)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT to_regclass('public.debts')")).scalar() is None
    migrate()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM strategies")).scalar() == 3


def test_models_match_migrations(app):
    """Модели и миграции не расходятся: autogenerate не находит изменений."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.db import Base, engine

    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


@pytest.mark.parametrize("secret", [DEV_SECRET, "short"])
def test_production_requires_strong_secret(secret):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret=secret)


def test_production_accepts_strong_secret():
    assert Settings(environment="production", jwt_secret="x" * 32).is_production


def test_too_long_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": "пароль" * 7})
    assert r.status_code == 422
    assert r.json()["detail"].startswith("Пароль слишком длинный")
