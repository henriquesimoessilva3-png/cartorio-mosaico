"""Geração de PDF do memorial descritivo — Jinja2 + WeasyPrint."""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.models.lote_geometria import LoteGeometria
from app.models.matricula import Matricula

# project_root/templates  (resolvido a partir de src/app/services/memorial.py)
TEMPLATE_DIR = Path(__file__).resolve().parents[4] / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


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

    template = _env.get_template("memorial_descritivo.html.j2")
    html_content = template.render(
        matricula=matricula,
        cartorio={"nome": cartorio_nome, "comarca": cartorio_comarca},
        vertices=lote.vertices_jsonb or [],
        segmentos=lote.azimutes_jsonb or [],
        utm_zone="23S",
        area_m2=float(lote.area_calculada_m2 or 0),
        perimetro_m=float(lote.perimetro_m or 0),
        croqui_base64=None,
        operador={"nome": operador_nome},
        gerado_em=datetime.utcnow(),
        hash_documento="",
        texto_disclaimer=texto_disclaimer,
    )

    pdf_bytes = HTML(string=html_content).write_pdf()
    lote.hash_documento = hashlib.sha256(pdf_bytes).hexdigest()
    db.commit()
    return pdf_bytes
