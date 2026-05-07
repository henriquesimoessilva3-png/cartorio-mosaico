from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StatusGeometria(str, Enum):
    NAO_MAPEADO = "nao_mapeado"
    RASCUNHO = "rascunho"
    REVISADO = "revisado"
    VALIDADO_ART = "validado_art"


class Matricula(Base):
    __tablename__ = "matricula"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    livro_folha: Mapped[str | None] = mapped_column(String(64))
    ano_abertura: Mapped[int | None]

    proprietario_atual_nome: Mapped[str | None] = mapped_column(String(255))
    cpf_cnpj_hash: Mapped[str | None] = mapped_column(String(64))
    cpf_cnpj_ultimo_digito: Mapped[str | None] = mapped_column(String(2))

    endereco_logradouro: Mapped[str | None] = mapped_column(String(255))
    endereco_numero: Mapped[str | None] = mapped_column(String(32))
    endereco_complemento: Mapped[str | None] = mapped_column(String(128))
    endereco_bairro: Mapped[str | None] = mapped_column(String(128))

    area_descrita_texto: Mapped[str | None] = mapped_column(Text)
    area_descrita_m2: Mapped[float | None] = mapped_column(Numeric(14, 4))

    status_geometria: Mapped[str] = mapped_column(
        String(32), default=StatusGeometria.NAO_MAPEADO.value, index=True
    )
    observacoes: Mapped[str | None] = mapped_column(Text)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
