"""Integração CRUD de matrículas + auth + lotes + mosaico + memorial.

Requer Docker. Roda com: uv run pytest -m integration
"""
import pytest

pytestmark = pytest.mark.integration


def test_unauthenticated_blocked(client):
    """Endpoints mutantes e de leitura privada exigem token."""
    r = client.get("/api/matriculas")
    assert r.status_code == 401

    r = client.post("/api/matriculas", json={"numero": "X"})
    assert r.status_code == 401

    r = client.get("/api/mosaico")
    assert r.status_code == 401


def test_matricula_crud(auth_client):
    r = auth_client.get("/api/matriculas")
    assert r.status_code == 200
    assert r.json() == []

    r = auth_client.post(
        "/api/matriculas",
        json={
            "numero": "T001",
            "proprietario_atual_nome": "João Teste",
            "cpf_cnpj": "123.456.789-09",
            "endereco_logradouro": "Rua Teste",
            "endereco_numero": "100",
            "area_descrita_texto": "12m de frente por 30m de fundo",
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["numero"] == "T001"
    assert "cpf_cnpj" not in created
    assert created["cpf_cnpj_ultimo_digito"] == "9"

    r2 = auth_client.post("/api/matriculas", json={"numero": "T001"})
    assert r2.status_code == 409

    r3 = auth_client.get(f"/api/matriculas/{created['id']}")
    assert r3.status_code == 200

    r4 = auth_client.put(
        f"/api/matriculas/{created['id']}",
        json={"observacoes": "atualizado"},
    )
    assert r4.status_code == 200
    assert r4.json()["observacoes"] == "atualizado"

    r5 = auth_client.delete(f"/api/matriculas/{created['id']}")
    assert r5.status_code == 204

    r6 = auth_client.get(f"/api/matriculas/{created['id']}")
    assert r6.status_code == 404


def test_lote_create_geometria(auth_client):
    m = auth_client.post("/api/matriculas", json={"numero": "L001"}).json()

    coords = [
        [-43.0220, -19.2340],
        [-43.0219, -19.2340],
        [-43.0219, -19.2342],
        [-43.0220, -19.2342],
    ]
    r = auth_client.post(
        "/api/lotes",
        json={"matricula_id": m["id"], "vertices": coords},
    )
    assert r.status_code == 201, r.text
    lote = r.json()
    assert lote["versao"] == 1
    assert lote["area_calculada_m2"] is not None
    assert lote["area_calculada_m2"] > 0
    assert len(lote["vertices_jsonb"]) == 4

    m_updated = auth_client.get(f"/api/matriculas/{m['id']}").json()
    assert m_updated["status_geometria"] == "rascunho"


def test_validacao_textual(auth_client):
    m = auth_client.post(
        "/api/matriculas",
        json={
            "numero": "V001",
            "area_descrita_texto": "Lote com 12 metros de frente por 20m de fundo",
        },
    ).json()

    coords = [
        [-43.0220, -19.2340],
        [-43.02189, -19.2340],
        [-43.02189, -19.23418],
        [-43.0220, -19.23418],
    ]
    lote = auth_client.post(
        "/api/lotes",
        json={"matricula_id": m["id"], "vertices": coords},
    ).json()

    r = auth_client.get(f"/api/lotes/{lote['id']}/validacao-textual")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["matches"], list)
    assert isinstance(data["avisos"], list)


def test_mosaico_lista_lotes(auth_client):
    m1 = auth_client.post("/api/matriculas", json={"numero": "M001"}).json()
    m2 = auth_client.post("/api/matriculas", json={"numero": "M002"}).json()
    coords1 = [
        [-43.0220, -19.2340],
        [-43.02195, -19.2340],
        [-43.02195, -19.23405],
        [-43.0220, -19.23405],
    ]
    coords2 = [
        [-43.02195, -19.2340],
        [-43.02190, -19.2340],
        [-43.02190, -19.23405],
        [-43.02195, -19.23405],
    ]
    auth_client.post("/api/lotes", json={"matricula_id": m1["id"], "vertices": coords1})
    auth_client.post("/api/lotes", json={"matricula_id": m2["id"], "vertices": coords2})

    r = auth_client.get("/api/mosaico")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 2


def test_auth_register_via_admin(auth_client):
    r = auth_client.post(
        "/api/auth/register",
        json={
            "nome": "Escrivão",
            "email": "escrivao@test.com",
            "password": "outra-senha-456",
            "role": "escrivao",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "escrivao"


def test_role_protection(auth_client):
    """Escrivão pode criar matrícula, leitura não."""
    # Cria escrivão e leitura
    auth_client.post(
        "/api/auth/register",
        json={
            "nome": "Escrivão",
            "email": "esc@test.com",
            "password": "senha-12345",
            "role": "escrivao",
        },
    )
    auth_client.post(
        "/api/auth/register",
        json={
            "nome": "Leitor",
            "email": "leitor@test.com",
            "password": "senha-12345",
            "role": "leitura",
        },
    )

    # Login leitor
    r = auth_client.post(
        "/api/auth/login",
        data={"username": "leitor@test.com", "password": "senha-12345"},
    )
    leitor_token = r.json()["access_token"]

    # Leitor pode listar
    r = auth_client.get(
        "/api/matriculas",
        headers={"Authorization": f"Bearer {leitor_token}"},
    )
    assert r.status_code == 200

    # Leitor NÃO pode criar (precisa escrivao+)
    r = auth_client.post(
        "/api/matriculas",
        json={"numero": "X"},
        headers={"Authorization": f"Bearer {leitor_token}"},
    )
    assert r.status_code == 403


def test_memorial_pdf_gera(auth_client):
    m = auth_client.post("/api/matriculas", json={"numero": "P001"}).json()
    coords = [
        [-43.0220, -19.2340],
        [-43.0219, -19.2340],
        [-43.0219, -19.2342],
        [-43.0220, -19.2342],
    ]
    lote = auth_client.post(
        "/api/lotes",
        json={"matricula_id": m["id"], "vertices": coords},
    ).json()

    r = auth_client.get(f"/api/memoriais/{lote['id']}.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1000
