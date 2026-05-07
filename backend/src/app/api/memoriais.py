from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id, get_current_user
from app.db.database import get_db
from app.models.lote_geometria import LoteGeometria
from app.models.usuario import Usuario
from app.services.memorial import gerar_memorial_pdf, render_preview_png

router = APIRouter(prefix="/api/memoriais", tags=["memoriais"])
DbSession = Annotated[Session, Depends(get_db)]
AuthUser = Annotated[Usuario, Depends(get_current_user)]
TenantId = Annotated[int, Depends(get_current_tenant_id)]


def _clamp_pdf_options(
    croqui_width: int,
    croqui_height: int,
    croqui_pad: int,
    marker_size: int,
    font_size: int,
    page_margin_cm: float,
    tile_zoom_override: int | None,
) -> dict:
    cw = max(320, min(croqui_width, 1200))
    ch = max(240, min(croqui_height, 900))
    cp = max(0, min(croqui_pad, cw // 3))
    return {
        "croqui_width": cw,
        "croqui_height": ch,
        "croqui_pad": cp,
        "marker_size": max(2, min(marker_size, 20)),
        "font_size": max(6, min(font_size, 24)),
        "page_margin_cm": max(0.5, min(page_margin_cm, 5.0)),
        "tile_zoom_override": (
            None if tile_zoom_override is None else max(11, min(tile_zoom_override, 19))
        ),
    }


@router.get("/{lote_id}.pdf")
def baixar_memorial(
    lote_id: int,
    db: DbSession,
    user: AuthUser,
    tenant_id: TenantId,
    cartorio_nome: str = "Cartório de Registro de Imóveis",
    cartorio_comarca: str = "—",
    operador_nome: str | None = None,
    croqui_width: int = 620,
    croqui_height: int = 400,
    croqui_pad: int = 36,
    marker_size: int = 5,
    font_size: int = 11,
    page_margin_cm: float = 2.0,
    tile_zoom_override: int | None = None,
    usar_satelite: bool = True,
    format: Literal["pdf", "preview"] = "pdf",
):
    lote = db.get(LoteGeometria, lote_id)
    if lote is None or lote.tenant_id != tenant_id:
        raise HTTPException(404, "Lote não encontrado")

    opts = _clamp_pdf_options(
        croqui_width,
        croqui_height,
        croqui_pad,
        marker_size,
        font_size,
        page_margin_cm,
        tile_zoom_override,
    )

    if format == "preview":
        try:
            png = render_preview_png(
                db,
                lote_id,
                croqui_width=opts["croqui_width"],
                croqui_height=opts["croqui_height"],
                croqui_pad=opts["croqui_pad"],
                marker_size=opts["marker_size"],
                font_size=opts["font_size"],
                tile_zoom_override=opts["tile_zoom_override"],
                usar_satelite=usar_satelite,
            )
        except ValueError as e:
            raise HTTPException(404, str(e)) from e
        # se cairosvg ausente, render_preview_png devolve HTML — frontend lida.
        media = "image/png" if png[:8] == b"\x89PNG\r\n\x1a\n" else "text/html"
        return Response(content=png, media_type=media)

    if operador_nome is None:
        operador_nome = user.nome
    try:
        pdf = gerar_memorial_pdf(
            db,
            lote_id,
            cartorio_nome=cartorio_nome,
            cartorio_comarca=cartorio_comarca,
            operador_nome=operador_nome,
            usar_satelite=usar_satelite,
            **opts,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="memorial_{lote_id}.pdf"'
        },
    )
