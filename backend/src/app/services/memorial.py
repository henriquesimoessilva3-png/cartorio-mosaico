"""Geração de PDF do memorial descritivo — Jinja2 + WeasyPrint."""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.models.confrontante import Confrontante
from app.models.lote_geometria import LoteGeometria
from app.models.matricula import Matricula
from app.services.croqui import render_croqui_svg
from app.services.croqui_satellite import render_croqui_satellite_png

TEMPLATE_DIR = Path(__file__).resolve().parents[4] / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _merge_confrontantes(
    segmentos: list[dict], confrontantes: list[Confrontante]
) -> list[dict]:
    by_side = {(c.vertice_inicio, c.vertice_fim): c.descricao_textual for c in confrontantes}
    out = []
    for seg in segmentos:
        s = dict(seg)
        key = (s.get("de"), s.get("para"))
        if key in by_side and by_side[key]:
            s["confrontante"] = by_side[key]
        out.append(s)
    return out


def gerar_memorial_pdf(
    db: Session,
    lote_id: int,
    *,
    cartorio_nome: str = "Cartório de Registro de Imóveis",
    cartorio_comarca: str = "—",
    operador_nome: str = "Sistema",
    texto_disclaimer: str | None = None,
) -> bytes:
    lote = db.get(LoteGeometria, lote_id)
    if lote is None:
        raise ValueError(f"Lote {lote_id} não encontrado")
    matricula = db.get(Matricula, lote.matricula_id)
    if matricula is None:
        raise ValueError(f"Matrícula {lote.matricula_id} não encontrada")

    confrontantes = (
        db.execute(
            select(Confrontante).where(Confrontante.lote_geometria_id == lote.id)
        )
        .scalars()
        .all()
    )

    segmentos = _merge_confrontantes(lote.azimutes_jsonb or [], confrontantes)
    vertices = lote.vertices_jsonb or []

    coords_utm = [(v["e_utm"], v["n_utm"]) for v in vertices if "e_utm" in v]
    coords_lonlat = [(v["lon"], v["lat"]) for v in vertices if "lon" in v]
    croqui_svg = render_croqui_svg(coords_utm) if coords_utm else ""

    # Tenta croqui satélite (pode falhar — rede, tile vazio, etc.)
    croqui_satellite_b64 = ""
    if coords_lonlat:
        png = render_croqui_satellite_png(coords_lonlat)
        if png:
            croqui_satellite_b64 = base64.b64encode(png).decode("ascii")

    template = _env.get_template("memorial_descritivo.html.j2")
    html_content = template.render(
        matricula=matricula,
        cartorio={"nome": cartorio_nome, "comarca": cartorio_comarca},
        vertices=vertices,
        segmentos=segmentos,
        utm_zone="23S",
        area_m2=float(lote.area_calculada_m2 or 0),
        perimetro_m=float(lote.perimetro_m or 0),
        croqui_svg=croqui_svg,
        croqui_satellite_b64=croqui_satellite_b64,
        operador={"nome": operador_nome},
        gerado_em=datetime.utcnow(),
        hash_documento="",
        texto_disclaimer=texto_disclaimer,
    )

    pdf_bytes = HTML(string=html_content).write_pdf()
    lote.hash_documento = hashlib.sha256(pdf_bytes).hexdigest()
    db.commit()
    return pdf_bytes
