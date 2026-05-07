"""Geração de PDF do memorial descritivo — Jinja2 + WeasyPrint."""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
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
    croqui_width: int = 620,
    croqui_height: int = 400,
    croqui_pad: int = 36,
    marker_size: int = 5,
    font_size: int = 11,
    page_margin_cm: float = 2.0,
    tile_zoom_override: int | None = None,
    usar_satelite: bool = True,
) -> bytes:
    lote, croqui_svg, croqui_satellite_b64 = _render_croquis(
        db,
        lote_id,
        croqui_width=croqui_width,
        croqui_height=croqui_height,
        croqui_pad=croqui_pad,
        marker_size=marker_size,
        font_size=font_size,
        tile_zoom_override=tile_zoom_override,
        usar_satelite=usar_satelite,
    )
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
        gerado_em=datetime.now(timezone.utc),
        hash_documento="",
        texto_disclaimer=texto_disclaimer,
        page_margin_cm=page_margin_cm,
    )

    pdf_bytes = HTML(string=html_content).write_pdf()
    lote.hash_documento = hashlib.sha256(pdf_bytes).hexdigest()
    db.commit()
    return pdf_bytes


def _render_croquis(
    db: Session,
    lote_id: int,
    *,
    croqui_width: int,
    croqui_height: int,
    croqui_pad: int,
    marker_size: int,
    font_size: int,
    tile_zoom_override: int | None,
    usar_satelite: bool,
) -> tuple[LoteGeometria, str, str]:
    lote = db.get(LoteGeometria, lote_id)
    if lote is None:
        raise ValueError(f"Lote {lote_id} não encontrado")

    vertices = lote.vertices_jsonb or []
    coords_utm = [(v["e_utm"], v["n_utm"]) for v in vertices if "e_utm" in v]
    coords_lonlat = [(v["lon"], v["lat"]) for v in vertices if "lon" in v]

    croqui_svg = ""
    if coords_utm:
        croqui_svg = render_croqui_svg(
            coords_utm,
            width=croqui_width,
            height=croqui_height,
            pad=croqui_pad,
            marker_size=marker_size,
            font_size=font_size,
        )

    croqui_satellite_b64 = ""
    if usar_satelite and coords_lonlat:
        png = render_croqui_satellite_png(
            coords_lonlat,
            width=croqui_width,
            height=croqui_height,
            marker_size=marker_size,
            font_size=font_size,
            tile_zoom_override=tile_zoom_override,
        )
        if png:
            croqui_satellite_b64 = base64.b64encode(png).decode("ascii")

    return lote, croqui_svg, croqui_satellite_b64


def render_preview_png(
    db: Session,
    lote_id: int,
    *,
    croqui_width: int = 620,
    croqui_height: int = 400,
    croqui_pad: int = 36,
    marker_size: int = 5,
    font_size: int = 11,
    tile_zoom_override: int | None = None,
    usar_satelite: bool = False,
) -> bytes:
    """Retorna PNG do croqui para preview interativo no frontend.

    Default: SVG → PNG via render_svg_to_png. Se usar_satelite=True, renderiza
    direto com tile-stitching (mais lento; rate-limit no frontend).
    """
    lote = db.get(LoteGeometria, lote_id)
    if lote is None:
        raise ValueError(f"Lote {lote_id} não encontrado")
    vertices = lote.vertices_jsonb or []
    coords_lonlat = [(v["lon"], v["lat"]) for v in vertices if "lon" in v]

    if usar_satelite and coords_lonlat:
        png = render_croqui_satellite_png(
            coords_lonlat,
            width=croqui_width,
            height=croqui_height,
            marker_size=marker_size,
            font_size=font_size,
            tile_zoom_override=tile_zoom_override,
        )
        if png:
            return png

    # Fallback: rasteriza SVG via WeasyPrint num HTML mínimo.
    coords_utm = [(v["e_utm"], v["n_utm"]) for v in vertices if "e_utm" in v]
    if not coords_utm:
        raise ValueError(f"Lote {lote_id} sem coordenadas UTM para preview")
    svg = render_croqui_svg(
        coords_utm,
        width=croqui_width,
        height=croqui_height,
        pad=croqui_pad,
        marker_size=marker_size,
        font_size=font_size,
    )
    html = (
        f'<html><body style="margin:0">{svg}</body></html>'
    )
    # WeasyPrint escreve PDF; pra PNG usamos cairosvg quando disponível,
    # caso contrário retornamos o SVG como bytes (frontend renderiza inline).
    try:
        import cairosvg  # type: ignore

        return cairosvg.svg2png(bytestring=svg.encode("utf-8"))
    except Exception:
        return html.encode("utf-8")
