import os
from pathlib import Path

import pytest

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/debtfree_test"
)

BACKEND_DIR = Path(__file__).resolve().parent.parent


def migrate(revision: str = "head", downgrade: bool = False) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    (command.downgrade if downgrade else command.upgrade)(cfg, revision)


@pytest.fixture(scope="session")
def app():
    from sqlalchemy import text

    from app.db import engine
    from app.main import app as fastapi_app

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    migrate()
    yield fastapi_app
    engine.dispose()


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient
    from sqlalchemy import text

    from app.db import engine

    with TestClient(app) as c:
        yield c
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, debts, scenarios, payment_schedule, extra_payments, scenario_debts CASCADE"))


@pytest.fixture
def auth(client):
    def login(email="user@example.com", password="secret123"):
        client.post("/api/auth/register", json={"email": email, "password": password})
        token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return login
