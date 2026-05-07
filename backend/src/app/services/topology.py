"""Detecção de overlaps e gaps no mosaico — usa funções PostGIS via SQL."""
from sqlalchemy import text
from sqlalchemy.orm import Session


def detectar_overlaps(
    db: Session, area_minima_m2: float = 0.5
) -> list[dict]:
    """Pares (lote_a, lote_b) com sobreposição maior que `area_minima_m2`.

    Considera apenas a versão mais recente por matrícula e calcula a área
    da intersecção em UTM 23S (EPSG:31983).
    """
    sql = """
    WITH ultima_versao AS (
      SELECT DISTINCT ON (matricula_id) id, matricula_id, geometry
      FROM lote_geometria
      ORDER BY matricula_id, versao DESC
    )
    SELECT
        a.id AS lote_a, a.matricula_id AS matricula_a,
        b.id AS lote_b, b.matricula_id AS matricula_b,
        ST_Area(ST_Transform(ST_Intersection(a.geometry, b.geometry), 31983)) AS area_overlap_m2
    FROM ultima_versao a
    JOIN ultima_versao b
      ON a.id < b.id AND ST_Intersects(a.geometry, b.geometry)
    WHERE
        ST_Area(ST_Transform(ST_Intersection(a.geometry, b.geometry), 31983)) > :area_min
    ORDER BY area_overlap_m2 DESC
    """
    return [
        dict(row._mapping)
        for row in db.execute(text(sql), {"area_min": area_minima_m2})
    ]


def vizinhos_que_tocam(db: Session, lote_id: int) -> list[dict]:
    """Lotes que tocam (ST_Touches) o lote dado, com matrícula vizinha."""
    sql = """
    SELECT
        v.id AS lote_vizinho_id,
        m.id AS matricula_vizinha_id,
        m.numero AS matricula_vizinha_numero,
        m.proprietario_atual_nome
    FROM lote_geometria base
    JOIN lote_geometria v
      ON v.id <> base.id AND ST_Touches(base.geometry, v.geometry)
    JOIN matricula m ON m.id = v.matricula_id
    WHERE base.id = :base_id
    """
    return [
        dict(row._mapping)
        for row in db.execute(text(sql), {"base_id": lote_id})
    ]
