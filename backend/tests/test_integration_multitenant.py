"""Multi-tenant: garante que dados de tenant A não vazam para tenant B.

Cobre: criação de tenant + user por tenant, listagem isolada de matrículas/lotes/
mosaico, header X-Tenant-Id pra admin global, e que mesmo número de matrícula
pode existir em 2 tenants distintos.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.integration


@pytest.fixture
def two_tenant_clients(engine, reset_db):
    from app.db.database import get_db
    from app.main import app
    from app.models.tenant import Tenant
    from app.models.usuario import Usuario
    from app.services.auth import hash_password

    Session = sessionmaker(bind=engine)
    with Session() as db:
        a = Tenant(slug="tenant-a", nome="Tenant A")
        b = Tenant(slug="tenant-b", nome="Tenant B")
        db.add_all([a, b])
        db.commit()
        db.refresh(a)
        db.refresh(b)
        tenant_a_id = a.id
        tenant_b_id = b.id

        users = [
            Usuario(
                tenant_id=tenant_a_id,
                nome="Admin A",
                email="a@test.com",
                password_hash=hash_password("senha-a-12345"),
                role="admin",
                ativo=True,
            ),
            Usuario(
                tenant_id=tenant_b_id,
                nome="Admin B",
                email="b@test.com",
                password_hash=hash_password("senha-b-12345"),
                role="admin",
                ativo=True,
            ),
            # Admin global (tenant_id=None)
            Usuario(
                tenant_id=None,
                nome="Admin Global",
                email="g@test.com",
                password_hash=hash_password("senha-g-12345"),
                role="admin",
                ativo=True,
            ),
        ]
        db.add_all(users)
        db.commit()

    def override_get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db

    def login_as(c: TestClient, email: str, password: str) -> str:
        r = c.post(
            "/api/auth/login",
            data={"username": email, "password": password},
        )
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    with TestClient(app) as c:
        token_a = login_as(c, "a@test.com", "senha-a-12345")
        token_b = login_as(c, "b@test.com", "senha-b-12345")
        token_g = login_as(c, "g@test.com", "senha-g-12345")
        yield {
            "client": c,
            "token_a": token_a,
            "token_b": token_b,
            "token_g": token_g,
            "tenant_a_id": tenant_a_id,
            "tenant_b_id": tenant_b_id,
        }

    app.dependency_overrides.clear()


def _h(token: str, tenant_id: int | None = None) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if tenant_id is not None:
        h["X-Tenant-Id"] = str(tenant_id)
    return h


def test_listar_matriculas_isola_tenants(two_tenant_clients):
    c = two_tenant_clients["client"]
    ta, tb = two_tenant_clients["token_a"], two_tenant_clients["token_b"]

    # A cria matrícula no seu tenant
    r = c.post("/api/matriculas", json={"numero": "X001"}, headers=_h(ta))
    assert r.status_code == 201, r.text

    # B não vê matrícula de A
    r = c.get("/api/matriculas", headers=_h(tb))
    assert r.status_code == 200
    assert r.json() == []

    # A vê só a sua
    r = c.get("/api/matriculas", headers=_h(ta))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_mesmo_numero_em_tenants_distintos(two_tenant_clients):
    c = two_tenant_clients["client"]
    ta, tb = two_tenant_clients["token_a"], two_tenant_clients["token_b"]

    r1 = c.post("/api/matriculas", json={"numero": "DUP"}, headers=_h(ta))
    r2 = c.post("/api/matriculas", json={"numero": "DUP"}, headers=_h(tb))
    assert r1.status_code == 201
    assert r2.status_code == 201, r2.text


def test_acesso_cruzado_retorna_404(two_tenant_clients):
    c = two_tenant_clients["client"]
    ta, tb = two_tenant_clients["token_a"], two_tenant_clients["token_b"]

    created = c.post(
        "/api/matriculas", json={"numero": "PRIV"}, headers=_h(ta)
    ).json()
    # B tenta acessar matrícula do A → 404
    r = c.get(f"/api/matriculas/{created['id']}", headers=_h(tb))
    assert r.status_code == 404


def test_admin_global_precisa_header(two_tenant_clients):
    c = two_tenant_clients["client"]
    tg = two_tenant_clients["token_g"]

    r = c.get("/api/matriculas", headers=_h(tg))
    assert r.status_code == 400
    assert "X-Tenant-Id" in r.json()["detail"]


def test_admin_global_com_header_acessa_tenant(two_tenant_clients):
    c = two_tenant_clients["client"]
    ta = two_tenant_clients["token_a"]
    tg = two_tenant_clients["token_g"]
    tenant_a_id = two_tenant_clients["tenant_a_id"]

    c.post("/api/matriculas", json={"numero": "G001"}, headers=_h(ta))

    r = c.get("/api/matriculas", headers=_h(tg, tenant_a_id))
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["numero"] == "G001"


def test_mosaico_isola_tenants(two_tenant_clients):
    c = two_tenant_clients["client"]
    ta, tb = two_tenant_clients["token_a"], two_tenant_clients["token_b"]

    m_a = c.post("/api/matriculas", json={"numero": "MA"}, headers=_h(ta)).json()
    m_b = c.post("/api/matriculas", json={"numero": "MB"}, headers=_h(tb)).json()

    coords = [
        [-43.0220, -19.2340],
        [-43.0219, -19.2340],
        [-43.0219, -19.2342],
        [-43.0220, -19.2342],
    ]
    c.post(
        "/api/lotes",
        json={"matricula_id": m_a["id"], "vertices": coords},
        headers=_h(ta),
    )
    c.post(
        "/api/lotes",
        json={"matricula_id": m_b["id"], "vertices": coords},
        headers=_h(tb),
    )

    r = c.get("/api/mosaico", headers=_h(ta))
    assert r.status_code == 200
    fc = r.json()
    # cada tenant vê só 1 feature
    assert len(fc["features"]) == 1
    assert fc["features"][0]["properties"]["matricula_numero"] == "MA"

    r = c.get("/api/mosaico", headers=_h(tb))
    assert len(r.json()["features"]) == 1


def test_lote_cross_tenant_404(two_tenant_clients):
    c = two_tenant_clients["client"]
    ta, tb = two_tenant_clients["token_a"], two_tenant_clients["token_b"]

    m = c.post("/api/matriculas", json={"numero": "L1"}, headers=_h(ta)).json()
    coords = [
        [-43.0220, -19.2340],
        [-43.0219, -19.2340],
        [-43.0219, -19.2342],
        [-43.0220, -19.2342],
    ]
    lote = c.post(
        "/api/lotes",
        json={"matricula_id": m["id"], "vertices": coords},
        headers=_h(ta),
    ).json()

    # B não pode baixar memorial do lote de A
    r = c.get(f"/api/memoriais/{lote['id']}.pdf", headers=_h(tb))
    assert r.status_code == 404

    # nem ver detalhe
    r = c.get(f"/api/lotes/{lote['id']}", headers=_h(tb))
    assert r.status_code == 404
