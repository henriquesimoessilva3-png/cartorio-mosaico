"""Endpoints admin para disparar imports (CSV / vendor) e ver status.

Imports rodam em BackgroundTask do FastAPI — adequado pro volume típico de
cartório (~1k matrículas). Para volumes maiores (10k+/import), migrar para
RQ/Celery.
"""
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id, require_role
from app.db.database import SessionLocal, get_db
from app.models.import_job import ImportJob
from app.models.usuario import Usuario
from app.schemas.import_job import ImportJobCreate, ImportJobRead
from app.services.importers.base import run_import
from app.services.importers.cri_source import CriEletronicoSource
from app.services.importers.csv_source import CsvSource
from app.services.importers.eprotocolo_source import EProtocoloSource

router = APIRouter(prefix="/api/admin/imports", tags=["admin", "imports"])
DbSession = Annotated[Session, Depends(get_db)]
AdminOnly = Annotated[Usuario, Depends(require_role("admin"))]
TenantId = Annotated[int, Depends(get_current_tenant_id)]


def _build_source(source_type: str, params: dict):
    if source_type == "csv":
        path = params.get("path")
        if not path:
            raise HTTPException(422, "csv source requer params.path")
        return CsvSource(Path(path))
    if source_type == "eprotocolo":
        return EProtocoloSource(**params)
    if source_type == "cri":
        return CriEletronicoSource(**params)
    raise HTTPException(422, f"source_type inválido: {source_type}")


def _execute_job(job_id: int, source_type: str, params: dict, tenant_id: int) -> None:
    """Roda o import em background; abre sessão própria pra evitar usar a
    sessão do request (que pode fechar antes do término).
    """
    with SessionLocal() as db:
        job = db.get(ImportJob, job_id)
        if job is None:
            return
        try:
            source = _build_source(source_type, params)
            summary = run_import(db, source, tenant_id=tenant_id)
            job.status = "success" if not summary.errors else "partial"
            job.total = summary.inserted + summary.updated + summary.skipped
            job.inserted = summary.inserted
            job.updated = summary.updated
            job.skipped = summary.skipped
            job.errors_jsonb = summary.errors or None
        except NotImplementedError as e:
            job.status = "not_implemented"
            job.errors_jsonb = [{"msg": str(e)}]
        except Exception as e:
            job.status = "error"
            job.errors_jsonb = [{"msg": str(e)}]
        finally:
            job.finalizado_em = datetime.utcnow()
            db.commit()


@router.post("", response_model=ImportJobRead, status_code=201)
def criar_import_job(
    payload: ImportJobCreate,
    db: DbSession,
    current: AdminOnly,
    tenant_id: TenantId,
    bg: BackgroundTasks,
):
    job = ImportJob(
        tenant_id=tenant_id,
        source_type=payload.source_type,
        params_jsonb=payload.params,
        status="pending",
        criado_por_user_id=current.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    bg.add_task(_execute_job, job.id, payload.source_type, payload.params, tenant_id)
    return job


@router.get("", response_model=list[ImportJobRead])
def listar_jobs(db: DbSession, _: AdminOnly, tenant_id: TenantId):
    rows = (
        db.execute(
            select(ImportJob)
            .where(ImportJob.tenant_id == tenant_id)
            .order_by(ImportJob.criado_em.desc())
            .limit(100)
        )
        .scalars()
        .all()
    )
    return rows


@router.get("/{job_id}", response_model=ImportJobRead)
def obter_job(
    job_id: int, db: DbSession, _: AdminOnly, tenant_id: TenantId
):
    job = db.get(ImportJob, job_id)
    if job is None or job.tenant_id != tenant_id:
        raise HTTPException(404, "Import job não encontrado")
    return job
