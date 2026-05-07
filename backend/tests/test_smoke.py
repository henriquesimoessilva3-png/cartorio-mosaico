"""Smoke tests — não exigem banco rodando.

Verificam que o app importa, rotas estão registradas e /health responde.
Testes de CRUD reais virão depois com fixture de DB (testcontainers ou similar).
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_matriculas_routes_registered() -> None:
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/matriculas" in paths
    assert "/api/matriculas/{matricula_id}" in paths


def test_auth_routes_registered() -> None:
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/auth/login" in paths
    assert "/api/auth/me" in paths
    assert "/api/auth/register" in paths


def test_jwt_roundtrip() -> None:
    from app.services.auth import (
        create_access_token,
        decode_access_token,
        hash_password,
        verify_password,
    )

    h = hash_password("uma-senha-forte-123")
    assert h != "uma-senha-forte-123"
    assert verify_password("uma-senha-forte-123", h)
    assert not verify_password("errada", h)

    token = create_access_token(42, "admin")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"

    assert decode_access_token("nao-eh-um-token-valido") is None


def test_cpf_hash_is_deterministic_and_keyed() -> None:
    from app.services.security import hash_cpf_cnpj, last_digit

    h1 = hash_cpf_cnpj("123.456.789-09")
    h2 = hash_cpf_cnpj("12345678909")
    assert h1 == h2
    assert len(h1) == 64
    assert last_digit("123.456.789-09") == "9"
    assert hash_cpf_cnpj("") == ""
