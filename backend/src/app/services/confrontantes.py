"""Inferência automática de confrontantes via PostGIS.

Para cada par de vértices consecutivos do polígono do lote alvo, procura o lote
vizinho cujo limite (boundary) tem maior interseção com aquele lado. Usa SQL
puro com índice GIST; escala para dezenas de milhares de lotes.

Tolerância em metros (UTM 23S) define quão pequena pode ser a interseção para
ainda contar como confrontante.
"""
from __future__ import annotations

from typing import TypedDict

from geoalchemy2.shape import to_shape
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.models.confrontante import Confrontante
from app.models.lote_geometria import LoteGeometria

TOLERANCIA_OVERLAP_M = 0.5
# Bounding-box pad em graus (~1.1 m a 20°S — folga generosa pro filtro GIST).
TOLERANCIA_BBOX_DEG = 1e-5


class ConfrontanteData(TypedDict):
    vertice_inicio: str
    vertice_fim: str
    tipo: str
    matricula_vizinha_id: int | None
    descricao_textual: str


_INFERIR_SQL = text(
    """
    WITH me AS (
      SELECT id, tenant_id, geometry
      FROM lote_geometria
      WHERE id = :lote_id
    ),
    pontos AS (
      SELECT
        (ST_DumpPoints(ST_ExteriorRing(geometry))).path[1] AS vertex_idx,
        (ST_DumpPoints(ST_ExteriorRing(geometry))).geom AS vertex,
        tenant_id
      FROM me
    ),
    sides AS (
      SELECT
        (vertex_idx - 1)::int AS side_idx,
        ST_MakeLine(
          vertex,
          LEAD(vertex) OVER (ORDER BY vertex_idx)
        ) AS side_geom,
        tenant_id
      FROM pontos
    ),
    candidatos AS (
      SELECT
        s.side_idx,
        other.matricula_id AS other_matricula_id,
        ST_Length(
          ST_Transform(
            ST_Intersection(s.side_geom, ST_Boundary(other.geometry)),
            31983
          )
        ) AS overlap_m
      FROM sides s
      JOIN lote_geometria other
        ON other.id != :lote_id
       AND other.tenant_id = s.tenant_id
       AND ST_DWithin(s.side_geom, other.geometry, :bbox_pad_deg)
      WHERE s.side_geom IS NOT NULL
    ),
    melhores AS (
      SELECT DISTINCT ON (side_idx)
        side_idx, other_matricula_id, overlap_m
      FROM candidatos
      WHERE overlap_m > :tolerancia_m
      ORDER BY side_idx, overlap_m DESC
    )
    SELECT
      mb.side_idx,
      mb.overlap_m,
      m.id AS matricula_id,
      m.numero,
      m.proprietario_atual_nome
    FROM melhores mb
    JOIN matricula m ON m.id = mb.other_matricula_id
    ORDER BY mb.side_idx
    """
)


def inferir_para_lote(db: Session, lote_id: int) -> list[ConfrontanteData]:
    """Identifica vizinhos de cada lado e (re)cria as linhas de Confrontante."""
    lote = db.get(LoteGeometria, lote_id)
    if lote is None:
        raise ValueError(f"Lote {lote_id} não encontrado")

    my_poly = to_shape(lote.geometry)
    coords = list(my_poly.exterior.coords)
    if coords[0] == coords[-1]:
        coords = coords[:-1]
    n = len(coords)

    rows = db.execute(
        _INFERIR_SQL,
        {
            "lote_id": lote_id,
            "tolerancia_m": TOLERANCIA_OVERLAP_M,
            "bbox_pad_deg": TOLERANCIA_BBOX_DEG,
        },
    ).all()
    matches_by_side: dict[int, dict] = {
        int(r.side_idx): {
            "matricula_id": int(r.matricula_id),
            "numero": r.numero,
            "proprietario": r.proprietario_atual_nome,
        }
        for r in rows
    }

    vertices_data = lote.vertices_jsonb or []

    def marco(idx: int) -> str:
        if idx < len(vertices_data):
            return vertices_data[idx]["marco"]
        return f"M{idx}"

    novas: list[ConfrontanteData] = []
    for i in range(n):
        match = matches_by_side.get(i)
        if match is not None:
            descricao = f"Matrícula nº {match['numero']}"
            if match["proprietario"]:
                descricao += f" ({match['proprietario']})"
            novas.append(
                {
                    "vertice_inicio": marco(i),
                    "vertice_fim": marco((i + 1) % n),
                    "tipo": "matricula",
                    "matricula_vizinha_id": match["matricula_id"],
                    "descricao_textual": descricao,
                }
            )
        else:
            novas.append(
                {
                    "vertice_inicio": marco(i),
                    "vertice_fim": marco((i + 1) % n),
                    "tipo": "outro",
                    "matricula_vizinha_id": None,
                    "descricao_textual": "________________",
                }
            )

    db.execute(
        delete(Confrontante).where(Confrontante.lote_geometria_id == lote_id)
    )
    for c in novas:
        db.add(Confrontante(tenant_id=lote.tenant_id, lote_geometria_id=lote_id, **c))
    db.commit()

    return novas
