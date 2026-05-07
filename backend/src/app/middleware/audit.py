"""Middleware de audit log — grava toda mutação (POST/PUT/PATCH/DELETE) na tabela audit_log."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.database import SessionLocal
from app.models.audit_log import AuditLog
from app.services.auth import decode_access_token

logger = logging.getLogger("audit")

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _claims_from_request(request: Request) -> tuple[int | None, int | None]:
    """Retorna (user_id, tenant_id) extraídos do JWT do header. Best-effort."""
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None, None
    try:
        payload = decode_access_token(auth.split(" ", 1)[1])
        if not payload:
            return None, None
        sub = payload.get("sub")
        user_id = int(sub) if sub is not None else None
        tid = payload.get("tenant_id")
        tenant_id = int(tid) if tid is not None else None
        return user_id, tenant_id
    except (ValueError, TypeError):
        return None, None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        if request.method not in MUTATING_METHODS:
            return response

        try:
            user_id, tenant_id = _claims_from_request(request)
            with SessionLocal() as db:
                db.add(
                    AuditLog(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        acao=request.method,
                        entidade=request.url.path,
                        entidade_id=None,
                        payload_jsonb={
                            "status": response.status_code,
                            "query": dict(request.query_params),
                        },
                    )
                )
                db.commit()
        except SQLAlchemyError as exc:
            logger.warning("Falha ao gravar audit_log: %s", exc)
        except Exception as exc:
            logger.warning("Erro inesperado em AuditMiddleware: %s", exc)

        return response
