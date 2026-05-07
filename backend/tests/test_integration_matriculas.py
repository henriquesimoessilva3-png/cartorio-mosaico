"""Integração CRUD de matrículas + auth + lotes + mosaico + memorial.

Requer Docker. Roda com: uv run pytest -m integration
"""
import pytest

pytestmark = pytest.mark.integration


def test_matricula_crud(client):
    # Listar vazio
    r = client.get("/api/matriculas")
    assert r.status_code == 200
    assert r.json() == []

    # Criar
    r = client.post(
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
    assert created["proprietario_atual_nome"] == "João Teste"
    assert created["status_geometria"] == "nao_mapeado"
    # Hash CPF não retornado
    assert "cpf_cnpj" not in created
    assert created["cpf_cnpj_ultimo_digito"] == "9"

    # Duplicado falha 409
    r2 = client.post("/api/matriculas", json={"numero": "T001"})
    assert r2.status_code == 409

    # Get
    r3 = client.get(f"/api/matriculas/{created['id']}")
    assert r3.status_code == 200
    assert r3.json()["numero"] == "T001"

    # Update
    r4 = client.put(
        f"/api/matriculas/{created['id']}",
        json={"observacoes": "atualizado"},
    )
    assert r4.status_code == 200
    assert r4.json()["observacoes"] == "atualizado"

    # Delete
    r5 = client.delete(f"/api/matriculas/{created['id']}")
    assert r5.status_code == 204

    r6 = client.get(f"/api/matriculas/{created['id']}")
    assert r6.status_code == 404


def test_lote_create_geometria(client):
    # cria matrícula
    m = client.post("/api/matriculas", json={"numero": "L001"}).json()

    # Polígono retangular ~10m x 20m (em Ferros)
    coords = [
        [-43.0220, -19.2340],
        [-43.0219, -19.2340],
        [-43.0219, -19.2342],
        [-43.0220, -19.2342],
    ]
    r = client.post(
        "/api/lotes",
        json={"matricula_id": m["id"], "vertices": coords},
    )
    assert r.status_code == 201, r.text
    lote = r.json()
    assert lote["matricula_id"] == m["id"]
    assert lote["versao"] == 1
    assert lote["area_calculada_m2"] is not None
    assert lote["area_calculada_m2"] > 0
    assert lote["perimetro_m"] is not None
    assert len(lote["vertices_jsonb"]) == 4
    assert len(lote["azimutes_jsonb"]) == 4

    # Status atualizado
    m_updated = client.get(f"/api/matriculas/{m['id']}").json()
    assert m_updated["status_geometria"] == "rascunho"


def test_validacao_textual(client):
    m = client.post(
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
    lote = client.post(
        "/api/lotes",
        json={"matricula_id": m["id"], "vertices": coords},
    ).json()

    r = client.get(f"/api/lotes/{lote['id']}/validacao-textual")
    assert r.status_code == 200
    data = r.json()
    assert "12.0" in [str(n) for n in data["numeros_extraidos"]] or 12.0 in data[
        "numeros_extraidos"
    ]
    assert isinstance(data["matches"], list)
    assert isinstance(data["avisos"], list)


def test_mosaico_lista_lotes(client):
    m1 = client.post("/api/matriculas", json={"numero": "M001"}).json()
    m2 = client.post("/api/matriculas", json={"numero": "M002"}).json()
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
    client.post("/api/lotes", json={"matricula_id": m1["id"], "vertices": coords1})
    client.post("/api/lotes", json={"matricula_id": m2["id"], "vertices": coords2})

    r = client.get("/api/mosaico")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 2
    numeros = {f["properties"]["matricula_numero"] for f in fc["features"]}
    assert numeros == {"M001", "M002"}


def test_auth_register_login_me(client):
    # Bootstrap admin direto pelo DB (não há rota pública pra primeiro admin)
    from sqlalchemy.orm import sessionmaker

    from app.db.database import engine
    from app.models.usuario import Usuario
    from app.services.auth import hash_password

    Session = sessionmaker(bind=engine)
    with Session() as db:
        admin = Usuario(
            nome="Admin",
            email="admin@test.com",
            password_hash=hash_password("senha-1234"),
            role="admin",
            ativo=True,
        )
        db.add(admin)
        db.commit()

    # Login
    r = client.post(
        "/api/auth/login",
        data={"username": "admin@test.com", "password": "senha-1234"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]

    # /me autenticado
    r2 = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.status_code == 200
    assert r2.json()["email"] == "admin@test.com"
    assert r2.json()["role"] == "admin"

    # /me sem token = 401
    r3 = client.get("/api/auth/me")
    assert r3.status_code == 401

    # Admin registra outro usuário
    r4 = client.post(
        "/api/auth/register",
        json={
            "nome": "Escrivão",
            "email": "escrivao@test.com",
            "password": "outra-senha-456",
            "role": "escrivao",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r4.status_code == 201
    assert r4.json()["role"] == "escrivao"


def test_memorial_pdf_gera(client):
    m = client.post("/api/matriculas", json={"numero": "P001"}).json()
    coords = [
        [-43.0220, -19.2340],
        [-43.0219, -19.2340],
        [-43.0219, -19.2342],
        [-43.0220, -19.2342],
    ]
    lote = client.post(
        "/api/lotes",
        json={"matricula_id": m["id"], "vertices": coords},
    ).json()

    r = client.get(f"/api/memoriais/{lote['id']}.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1000
