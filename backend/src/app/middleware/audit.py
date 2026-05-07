"""Middleware de audit log — grava toda mutação (POST/PUT/PATCH/DELETE) na tabela audit_log."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.database import SessionLocal
from app.models.audit_log import AuditLog

logger = logging.getLogger("audit")

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


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
            with SessionLocal() as db:
                db.add(
                    AuditLog(
                        user_id=None,
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
