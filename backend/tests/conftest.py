"""Fixtures de integração — Postgres+PostGIS via testcontainers.

Os testes marcados com `@pytest.mark.integration` exigem Docker rodando.
Rode com:
    uv run pytest -m integration

Os smoke tests (test_smoke.py) não dependem destas fixtures e rodam sempre.
"""
from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: requer Docker para subir Postgres+PostGIS via testcontainers",
    )


@pytest.fixture(scope="session")
def postgres_container():
    pytest.importorskip("testcontainers.postgres", reason="testcontainers não instalado")
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgis/postgis:16-3.4", driver=None) as pg:
        yield pg


@pytest.fixture(scope="session")
def engine(postgres_container):
    from sqlalchemy import create_engine, text

    from app.db import database as db_module
    from app.db.base import Base

    raw = postgres_container.get_connection_url()
    url = raw.replace("postgresql+psycopg2", "postgresql+psycopg")

    eng = create_engine(url)
    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    Base.metadata.create_all(eng)

    # Patch globals para que serviços e middleware usem este engine
    from sqlalchemy.orm import sessionmaker

    db_module.engine = eng
    db_module.SessionLocal = sessionmaker(bind=eng)

    yield eng
    eng.dispose()


@pytest.fixture
def reset_db(engine):
    from sqlalchemy import text

    yield
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE audit_log, confrontante, lote_geometria, matricula, usuario "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def client(engine, reset_db):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.db.database import get_db
    from app.main import app

    Session = sessionmaker(bind=engine)

    def override_get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(engine, reset_db):
    """Client com admin já logado (Authorization header default)."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.db.database import get_db
    from app.main import app
    from app.models.usuario import Usuario
    from app.services.auth import hash_password

    Session = sessionmaker(bind=engine)

    with Session() as db:
        admin = Usuario(
            nome="Admin Test",
            email="admin@test.com",
            password_hash=hash_password("admin-test-1234"),
            role="admin",
            ativo=True,
        )
        db.add(admin)
        db.commit()

    def override_get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        r = c.post(
            "/api/auth/login",
            data={
                "username": "admin@test.com",
                "password": "admin-test-1234",
            },
        )
        assert r.status_code == 200, r.text
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        yield c

    app.dependency_overrides.clear()
