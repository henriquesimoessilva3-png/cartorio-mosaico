from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.models.lote_geometria import LoteGeometria
from app.models.matricula import Matricula
from app.models.usuario import Usuario
from app.schemas.lote import LoteGeometriaCreate, LoteGeometriaRead
from app.services import geo
from app.services.confrontantes import inferir_para_lote
from app.services.validacao import comparar_descricao_vs_lados

router = APIRouter(prefix="/api/lotes", tags=["lotes"])
DbSession = Annotated[Session, Depends(get_db)]
AuthUser = Annotated[Usuario, Depends(get_current_user)]
EditorRole = Annotated[Usuario, Depends(require_role("escrivao", "escrevente"))]


@router.post(
    "",
    response_model=LoteGeometriaRead,
    status_code=status.HTTP_201_CREATED,
)
def criar(payload: LoteGeometriaCreate, db: DbSession, _user: EditorRole):
    matricula = db.get(Matricula, payload.matricula_id)
    if matricula is None:
        raise HTTPException(404, "Matrícula não encontrada")

    coords = [(c[0], c[1]) for c in payload.vertices]
    ring = coords if coords[0] == coords[-1] else coords + [coords[0]]
    if len(ring) < 4:
        raise HTTPException(422, "Mínimo 3 vértices distintos")

    poly = Polygon(ring)
    if not poly.is_valid:
        raise HTTPException(422, "Polígono inválido (auto-intersecção?)")

    area_m2, perim_m = geo.area_perimetro_m(coords)
    vertices = geo.vertices_data(coords)
    azimutes = geo.segmentos(coords)

    last_versao = (
        db.execute(
            select(LoteGeometria.versao)
            .where(LoteGeometria.matricula_id == payload.matricula_id)
            .order_by(LoteGeometria.versao.desc())
        ).scalars().first()
        or 0
    )

    lote = LoteGeometria(
        matricula_id=payload.matricula_id,
        versao=last_versao + 1,
        geometry=from_shape(poly, srid=4674),
        area_calculada_m2=area_m2,
        perimetro_m=perim_m,
        vertices_jsonb=vertices,
        azimutes_jsonb=azimutes,
        notas_validacao=payload.notas_validacao,
    )
    db.add(lote)

    if matricula.status_geometria == "nao_mapeado":
        matricula.status_geometria = "rascunho"

    db.commit()
    db.refresh(lote)

    # Inferência automática de confrontantes (best-effort; falha não impede criação)
    try:
        inferir_para_lote(db, lote.id)
    except Exception:
        pass

    return lote


@router.post("/{lote_id}/inferir-confrontantes")
def inferir_confrontantes_endpoint(lote_id: int, db: DbSession, _user: EditorRole):
    try:
        confrontantes = inferir_para_lote(db, lote_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return {"confrontantes": confrontantes}


@router.get("/{lote_id}/validacao-textual")
def validacao_textual(lote_id: int, db: DbSession, _user: AuthUser):
    lote = db.get(LoteGeometria, lote_id)
    if lote is None:
        raise HTTPException(404, "Lote não encontrado")
    matricula = db.get(Matricula, lote.matricula_id)
    distancias = [
        s["distancia_m"] for s in (lote.azimutes_jsonb or []) if "distancia_m" in s
    ]
    return comparar_descricao_vs_lados(
        matricula.area_descrita_texto or "",
        distancias,
    )


@router.get("/{lote_id}", response_model=LoteGeometriaRead)
def detalhar(lote_id: int, db: DbSession, _user: AuthUser):
    lote = db.get(LoteGeometria, lote_id)
    if lote is None:
        raise HTTPException(404, "Lote não encontrado")
    return lote


@router.get(
    "/por-matricula/{matricula_id}",
    response_model=list[LoteGeometriaRead],
)
def por_matricula(matricula_id: int, db: DbSession, _user: AuthUser):
    stmt = (
        select(LoteGeometria)
        .where(LoteGeometria.matricula_id == matricula_id)
        .order_by(LoteGeometria.versao.desc())
    )
    return db.execute(stmt).scalars().all()
