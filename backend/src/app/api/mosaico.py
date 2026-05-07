import json
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.usuario import Usuario
from app.services.topology import detectar_overlaps

router = APIRouter(prefix="/api/mosaico", tags=["mosaico"])
DbSession = Annotated[Session, Depends(get_db)]
AuthUser = Annotated[Usuario, Depends(get_current_user)]


@router.get("")
def mosaico(db: DbSession, _user: AuthUser) -> dict:
    """FeatureCollection GeoJSON com a versão mais recente de cada matrícula."""
    sql = """
    SELECT DISTINCT ON (lg.matricula_id)
        lg.id, lg.matricula_id, lg.versao, lg.area_calculada_m2,
        ST_AsGeoJSON(lg.geometry) AS geom_json,
        m.numero, m.status_geometria, m.proprietario_atual_nome
    FROM lote_geometria lg
    JOIN matricula m ON m.id = lg.matricula_id
    ORDER BY lg.matricula_id, lg.versao DESC
    """
    rows = db.execute(text(sql)).all()
    features = [
        {
            "type": "Feature",
            "geometry": json.loads(r.geom_json),
            "properties": {
                "lote_id": r.id,
                "matricula_id": r.matricula_id,
                "matricula_numero": r.numero,
                "proprietario": r.proprietario_atual_nome,
                "versao": r.versao,
                "area_m2": float(r.area_calculada_m2 or 0),
                "status": r.status_geometria,
            },
        }
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}


@router.get("/conflitos")
def conflitos(db: DbSession, _user: AuthUser) -> dict:
    return {"overlaps": detectar_overlaps(db)}
