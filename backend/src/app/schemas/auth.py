from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["admin", "escrivao", "escrevente", "leitura"]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioCreate(BaseModel):
    nome: str = Field(..., max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Role = "leitura"
    # Apenas admin global (tenant_id=None) pode setar; senão é ignorado e herda do criador.
    tenant_id: int | None = None


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int | None = None
    nome: str
    email: str
    role: str
    ativo: bool
    criado_em: datetime


class UsuarioUpdate(BaseModel):
    nome: str | None = Field(None, max_length=255)
    role: Role | None = None
    ativo: bool | None = None
    password: str | None = Field(None, min_length=8)


class TenantInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    nome: str


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    role: str
    ativo: bool
    criado_em: datetime
    tenant_id: int | None = None
    tenant: TenantInfo | None = None
