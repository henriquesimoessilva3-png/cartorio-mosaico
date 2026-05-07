"""Inferência automática de confrontantes via análise de fronteiras dos lotes vizinhos."""
from __future__ import annotations

from typing import TypedDict

from geoalchemy2.shape import to_shape
from shapely.geometry import LineString
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.confrontante import Confrontante
from app.models.lote_geometria import LoteGeometria
from app.models.matricula import Matricula

TOLERANCIA_OVERLAP_M = 0.5


class ConfrontanteData(TypedDict):
    vertice_inicio: str
    vertice_fim: str
    tipo: str
    matricula_vizinha_id: int | None
    descricao_textual: str


def inferir_para_lote(db: Session, lote_id: int) -> list[ConfrontanteData]:
    """Identifica vizinhos de cada lado e (re)cria as linhas de Confrontante.

    Para cada par de vértices consecutivos do polígono, encontra o outro lote
    cujo limite tem maior interseção com aquele lado e marca como confrontante.
    Lados sem vizinho conhecido recebem placeholder.
    """
    lote = db.get(LoteGeometria, lote_id)
    if lote is None:
        raise ValueError(f"Lote {lote_id} não encontrado")

    my_poly = to_shape(lote.geometry)
    coords = list(my_poly.exterior.coords)
    if coords[0] == coords[-1]:
        coords = coords[:-1]
    n = len(coords)

    # Carrega todos os outros lotes (versão mais recente por matrícula)
    others_sql = (
        select(LoteGeometria, Matricula)
        .join(Matricula, Matricula.id == LoteGeometria.matricula_id)
        .where(LoteGeometria.id != lote_id)
    )
    others = db.execute(others_sql).all()
    others_geom = [(lg, m, to_shape(lg.geometry)) for lg, m, *_ in others]

    vertices_data = lote.vertices_jsonb or []

    def marco(idx: int) -> str:
        if idx < len(vertices_data):
            return vertices_data[idx]["marco"]
        return f"M{idx}"

    novas: list[ConfrontanteData] = []
    for i in range(n):
        a = coords[i]
        b = coords[(i + 1) % n]
        side = LineString([a, b])

        best_overlap = 0.0
        best_match: tuple[Matricula, int] | None = None
        for _other_lote, other_matricula, other_poly in others_geom:
            inter = side.intersection(other_poly.boundary)
            length = getattr(inter, "length", 0)
            if length > best_overlap:
                best_overlap = length
                best_match = (other_matricula, other_matricula.id)

        if best_match and best_overlap > TOLERANCIA_OVERLAP_M:
            other_matricula, _vizinha_id = best_match
            descricao = (
                f"Matrícula nº {other_matricula.numero}"
                + (
                    f" ({other_matricula.proprietario_atual_nome})"
                    if other_matricula.proprietario_atual_nome
                    else ""
                )
            )
            novas.append(
                {
                    "vertice_inicio": marco(i),
                    "vertice_fim": marco((i + 1) % n),
                    "tipo": "matricula",
                    "matricula_vizinha_id": other_matricula.id,
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
        db.add(Confrontante(lote_geometria_id=lote_id, **c))
    db.commit()

    return novas
