from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


SourceType = Literal["csv", "eprotocolo", "cri"]


class ImportJobCreate(BaseModel):
    source_type: SourceType
    params: dict[str, Any] = {}


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    source_type: str
    params_jsonb: dict[str, Any] | None
    status: str
    total: int
    inserted: int
    updated: int
    skipped: int
    errors_jsonb: list[Any] | None
    criado_por_user_id: int | None
    criado_em: datetime
    finalizado_em: datetime | None
