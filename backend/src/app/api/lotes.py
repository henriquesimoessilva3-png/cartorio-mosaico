from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.lote_geometria import LoteGeometria
from app.models.matricula import Matricula
from app.schemas.lote import LoteGeometriaCreate, LoteGeometriaRead
from app.services import geo

router = APIRouter(prefix="/api/lotes", tags=["lotes"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=LoteGeometriaRead,
    status_code=status.HTTP_201_CREATED,
)
def criar(payload: LoteGeometriaCreate, db: DbSession):
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
    return lote


@router.get("/{lote_id}", response_model=LoteGeometriaRead)
def detalhar(lote_id: int, db: DbSession):
    lote = db.get(LoteGeometria, lote_id)
    if lote is None:
        raise HTTPException(404, "Lote não encontrado")
    return lote


@router.get(
    "/por-matricula/{matricula_id}",
    response_model=list[LoteGeometriaRead],
)
def por_matricula(matricula_id: int, db: DbSession):
    stmt = (
        select(LoteGeometria)
        .where(LoteGeometria.matricula_id == matricula_id)
        .order_by(LoteGeometria.versao.desc())
    )
    return db.execute(stmt).scalars().all()
