"""Leitura do audit_log (admin-only). Lista paginada + detalhe com sanitização de PII."""
from datetime import datetime
import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id, require_role
from app.db.database import get_db
from app.models.audit_log import AuditLog
from app.models.usuario import Usuario
from app.schemas.auditoria import (
    AuditoriaDetail,
    AuditoriaListItem,
    AuditoriaListResponse,
)

router = APIRouter(prefix="/api/auditorias", tags=["auditorias"])
DbSession = Annotated[Session, Depends(get_db)]
AdminOnly = Annotated[Usuario, Depends(require_role("admin"))]
TenantId = Annotated[int, Depends(get_current_tenant_id)]

# Lista expansível: chaves cujo valor é PII e devem ser removidas do payload
# antes de devolver a auditoria pro frontend. Manter em sync com novos campos
# sensíveis criados em endpoints novos.
_PII_KEY_PATTERN = re.compile(r"cpf|cnpj|rg|email|password|senha", re.IGNORECASE)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _sanitize(v) for k, v in value.items() if not _PII_KEY_PATTERN.search(k)
        }
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


def _scope(stmt, current: Usuario, tenant_id: int):
    """Admin global (tenant_id=None) usa o tenant escolhido via header.
    Admin de tenant é restrito ao seu tenant.
    """
    if current.tenant_id is None:
        return stmt.where(AuditLog.tenant_id == tenant_id)
    return stmt.where(AuditLog.tenant_id == current.tenant_id)


@router.get("", response_model=AuditoriaListResponse)
def listar(
    db: DbSession,
    current: AdminOnly,
    tenant_id: TenantId,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: int | None = None,
    acao: str | None = None,
    entidade: str | None = None,
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = None,
):
    stmt = select(AuditLog, Usuario.nome).outerjoin(
        Usuario, Usuario.id == AuditLog.user_id
    )
    stmt = _scope(stmt, current, tenant_id)

    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if acao:
        stmt = stmt.where(AuditLog.acao == acao)
    if entidade:
        stmt = stmt.where(AuditLog.entidade.ilike(f"%{entidade}%"))
    if from_:
        stmt = stmt.where(AuditLog.criado_em >= from_)
    if to:
        stmt = stmt.where(AuditLog.criado_em <= to)

    count_stmt = _scope(
        select(func.count(AuditLog.id)), current, tenant_id
    )
    if user_id is not None:
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)
    if acao:
        count_stmt = count_stmt.where(AuditLog.acao == acao)
    if entidade:
        count_stmt = count_stmt.where(AuditLog.entidade.ilike(f"%{entidade}%"))
    if from_:
        count_stmt = count_stmt.where(AuditLog.criado_em >= from_)
    if to:
        count_stmt = count_stmt.where(AuditLog.criado_em <= to)
    total = db.execute(count_stmt).scalar_one()

    rows = db.execute(
        stmt.order_by(AuditLog.criado_em.desc()).offset(offset).limit(limit)
    ).all()
    items = [
        AuditoriaListItem(
            id=log.id,
            user_id=log.user_id,
            user_nome=user_nome,
            acao=log.acao,
            entidade=log.entidade,
            entidade_id=log.entidade_id,
            criado_em=log.criado_em,
        )
        for log, user_nome in rows
    ]
    return AuditoriaListResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get("/{audit_id}", response_model=AuditoriaDetail)
def detalhar(
    audit_id: int,
    db: DbSession,
    current: AdminOnly,
    tenant_id: TenantId,
):
    log = db.get(AuditLog, audit_id)
    if log is None:
        raise HTTPException(404, "Auditoria não encontrada")
    # Scope check
    expected_tid = current.tenant_id if current.tenant_id is not None else tenant_id
    if log.tenant_id is not None and log.tenant_id != expected_tid:
        raise HTTPException(404, "Auditoria não encontrada")

    user_nome = None
    if log.user_id:
        u = db.get(Usuario, log.user_id)
        user_nome = u.nome if u else None

    return AuditoriaDetail(
        id=log.id,
        user_id=log.user_id,
        user_nome=user_nome,
        acao=log.acao,
        entidade=log.entidade,
        entidade_id=log.entidade_id,
        criado_em=log.criado_em,
        payload_jsonb=_sanitize(log.payload_jsonb),
    )
