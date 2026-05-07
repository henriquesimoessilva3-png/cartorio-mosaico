from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Confrontante(Base):
    __tablename__ = "confrontante"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), index=True)
    lote_geometria_id: Mapped[int] = mapped_column(
        ForeignKey("lote_geometria.id"), index=True
    )
    vertice_inicio: Mapped[str] = mapped_column(String(16))
    vertice_fim: Mapped[str] = mapped_column(String(16))
    tipo: Mapped[str] = mapped_column(String(32))
    matricula_vizinha_id: Mapped[int | None] = mapped_column(
        ForeignKey("matricula.id")
    )
    descricao_textual: Mapped[str | None] = mapped_column(Text)
