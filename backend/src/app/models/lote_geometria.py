from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoteGeometria(Base):
    __tablename__ = "lote_geometria"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenant.id"), index=True)
    matricula_id: Mapped[int] = mapped_column(
        ForeignKey("matricula.id"), index=True
    )
    versao: Mapped[int] = mapped_column(Integer, default=1)

    geometry = mapped_column(Geometry(geometry_type="POLYGON", srid=4674))

    area_calculada_m2: Mapped[float | None] = mapped_column(Numeric(14, 4))
    perimetro_m: Mapped[float | None] = mapped_column(Numeric(14, 4))

    vertices_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    azimutes_jsonb: Mapped[dict | None] = mapped_column(JSONB)

    validado_por_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id")
    )
    validado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notas_validacao: Mapped[str | None] = mapped_column(Text)
    hash_documento: Mapped[str | None] = mapped_column(String(64))

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
