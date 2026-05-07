from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.memorial import gerar_memorial_pdf

router = APIRouter(prefix="/api/memoriais", tags=["memoriais"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{lote_id}.pdf")
def baixar_memorial(
    lote_id: int,
    db: DbSession,
    cartorio_nome: str = "Cartório de Registro de Imóveis",
    cartorio_comarca: str = "—",
    operador_nome: str = "Sistema",
):
    try:
        pdf = gerar_memorial_pdf(
            db,
            lote_id,
            cartorio_nome=cartorio_nome,
            cartorio_comarca=cartorio_comarca,
            operador_nome=operador_nome,
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
