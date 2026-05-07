"""Pipeline central de importação de matrículas.

Sources implementam `ImportSource.iter_records()` produzindo `MatriculaCreate`.
`run_import` valida (já feito pelo schema), aplica hash de CPF e faz upsert
por (tenant_id, numero). Reuso obrigatório de `services.security.hash_cpf_cnpj`.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.matricula import Matricula
from app.schemas.matricula import MatriculaCreate
from app.services.security import hash_cpf_cnpj, last_digit


class ImportSource(Protocol):
    """Iterável de registros a importar — cada um já validado como MatriculaCreate.

    Implementações decidem como obter os registros (CSV, vendor HTTP, etc.)
    mas devem produzir objetos `MatriculaCreate` Pydantic válidos.
    """

    def iter_records(self) -> Iterable[MatriculaCreate]: ...


@dataclass
class ImportSummary:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[dict] = field(default_factory=list)


def _payload_to_matricula_kwargs(payload: MatriculaCreate) -> dict:
    data = payload.model_dump()
    cpf = data.pop("cpf_cnpj", None)
    data["cpf_cnpj_hash"] = hash_cpf_cnpj(cpf) if cpf else None
    data["cpf_cnpj_ultimo_digito"] = last_digit(cpf) if cpf else None
    return data


def run_import(
    db: Session,
    source: ImportSource,
    tenant_id: int,
    *,
    dry_run: bool = False,
) -> ImportSummary:
    """Executa a importação. Em caso de erro por linha, registra e continua.

    Em `dry_run`, nenhum commit é feito — útil pra previewar.
    """
    summary = ImportSummary()
    try:
        records = list(source.iter_records())
    except (ValidationError, ValueError) as e:
        summary.errors.append({"stage": "iter", "msg": str(e)})
        return summary

    for idx, payload in enumerate(records, start=1):
        try:
            kwargs = _payload_to_matricula_kwargs(payload)
        except (ValidationError, ValueError) as e:
            summary.errors.append({"index": idx, "msg": str(e)})
            summary.skipped += 1
            continue

        existing = db.execute(
            select(Matricula)
            .where(Matricula.tenant_id == tenant_id)
            .where(Matricula.numero == kwargs["numero"])
        ).scalar_one_or_none()

        if existing is None:
            db.add(Matricula(tenant_id=tenant_id, **kwargs))
            summary.inserted += 1
        else:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            summary.updated += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()
    return summary
