from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditoriaListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    user_nome: str | None = None
    acao: str
    entidade: str
    entidade_id: int | None
    criado_em: datetime


class AuditoriaDetail(AuditoriaListItem):
    payload_jsonb: dict[str, Any] | None = None


class AuditoriaListResponse(BaseModel):
    items: list[AuditoriaListItem]
    total: int
    limit: int
    offset: int
