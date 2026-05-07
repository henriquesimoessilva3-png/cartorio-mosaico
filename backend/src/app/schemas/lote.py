from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


Coord = Annotated[list[float], Field(min_length=2, max_length=2)]


class LoteGeometriaCreate(BaseModel):
    matricula_id: int
    vertices: list[Coord] = Field(..., min_length=3)
    notas_validacao: str | None = None


class LoteGeometriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matricula_id: int
    versao: int
    area_calculada_m2: float | None
    perimetro_m: float | None
    vertices_jsonb: list | None
    azimutes_jsonb: list | None
    notas_validacao: str | None
    hash_documento: str | None
    criado_em: datetime
