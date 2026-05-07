from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatriculaBase(BaseModel):
    numero: str = Field(..., max_length=64)
    livro_folha: str | None = Field(None, max_length=64)
    ano_abertura: int | None = None
    proprietario_atual_nome: str | None = Field(None, max_length=255)
    cpf_cnpj: str | None = None
    endereco_logradouro: str | None = Field(None, max_length=255)
    endereco_numero: str | None = Field(None, max_length=32)
    endereco_complemento: str | None = Field(None, max_length=128)
    endereco_bairro: str | None = Field(None, max_length=128)
    area_descrita_texto: str | None = None
    area_descrita_m2: float | None = None
    observacoes: str | None = None


class MatriculaCreate(MatriculaBase):
    pass


class MatriculaUpdate(BaseModel):
    livro_folha: str | None = None
    ano_abertura: int | None = None
    proprietario_atual_nome: str | None = None
    cpf_cnpj: str | None = None
    endereco_logradouro: str | None = None
    endereco_numero: str | None = None
    endereco_complemento: str | None = None
    endereco_bairro: str | None = None
    area_descrita_texto: str | None = None
    area_descrita_m2: float | None = None
    observacoes: str | None = None


class MatriculaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    livro_folha: str | None
    ano_abertura: int | None
    proprietario_atual_nome: str | None
    cpf_cnpj_ultimo_digito: str | None
    endereco_logradouro: str | None
    endereco_numero: str | None
    endereco_complemento: str | None
    endereco_bairro: str | None
    area_descrita_texto: str | None
    area_descrita_m2: float | None
    status_geometria: str
    observacoes: str | None
    criado_em: datetime
    atualizado_em: datetime
