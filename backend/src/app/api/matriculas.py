from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.models.matricula import Matricula
from app.models.usuario import Usuario
from app.schemas.matricula import (
    MatriculaCreate,
    MatriculaRead,
    MatriculaUpdate,
)
from app.services.security import hash_cpf_cnpj, last_digit

router = APIRouter(prefix="/api/matriculas", tags=["matriculas"])

DbSession = Annotated[Session, Depends(get_db)]
AuthUser = Annotated[Usuario, Depends(get_current_user)]
EditorRole = Annotated[Usuario, Depends(require_role("escrivao", "escrevente"))]
AdminRole = Annotated[Usuario, Depends(require_role("admin"))]


def _apply_cpf(payload: dict) -> dict:
    if "cpf_cnpj" not in payload:
        return payload
    cpf = payload.pop("cpf_cnpj")
    payload["cpf_cnpj_hash"] = hash_cpf_cnpj(cpf) if cpf else None
    payload["cpf_cnpj_ultimo_digito"] = last_digit(cpf) if cpf else None
    return payload


@router.get("", response_model=list[MatriculaRead])
def listar(
    db: DbSession,
    _user: AuthUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
):
    stmt = select(Matricula).order_by(Matricula.numero)
    if status_filter:
        stmt = stmt.where(Matricula.status_geometria == status_filter)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{matricula_id}", response_model=MatriculaRead)
def detalhar(matricula_id: int, db: DbSession, _user: AuthUser):
    m = db.get(Matricula, matricula_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")
    return m


@router.post("", response_model=MatriculaRead, status_code=status.HTTP_201_CREATED)
def criar(payload: MatriculaCreate, db: DbSession, _user: EditorRole):
    data = _apply_cpf(payload.model_dump())
    m = Matricula(**data)
    db.add(m)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Matrícula com esse número já existe"
        )
    db.refresh(m)
    return m


@router.put("/{matricula_id}", response_model=MatriculaRead)
def atualizar(
    matricula_id: int,
    payload: MatriculaUpdate,
    db: DbSession,
    _user: EditorRole,
):
    m = db.get(Matricula, matricula_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")
    data = _apply_cpf(payload.model_dump(exclude_unset=True))
    for k, v in data.items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{matricula_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(matricula_id: int, db: DbSession, _user: AdminRole):
    m = db.get(Matricula, matricula_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")
    db.delete(m)
    db.commit()
    return None
