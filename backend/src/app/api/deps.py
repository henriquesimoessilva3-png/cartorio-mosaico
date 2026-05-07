"""Dependências comuns — autenticação JWT + scope de tenant."""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.usuario import Usuario
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Não autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(401, "Token inválido")
    user = db.get(Usuario, int(payload["sub"]))
    if user is None or not user.ativo:
        raise HTTPException(401, "Usuário não encontrado ou inativo")
    return user


def get_current_tenant_id(
    user: Annotated[Usuario, Depends(get_current_user)],
    x_tenant_id: Annotated[int | None, Header(alias="X-Tenant-Id")] = None,
) -> int:
    """Resolve tenant atual.

    Usuário comum → seu tenant_id. Admin global (tenant_id=None) → header
    X-Tenant-Id obrigatório. Falta de tenant_id em qualquer caminho é 400.
    """
    if user.tenant_id is not None:
        return user.tenant_id
    if x_tenant_id is None:
        raise HTTPException(
            400, "Admin global precisa especificar X-Tenant-Id no header"
        )
    return x_tenant_id


def require_role(*allowed: str):
    def check(
        user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if user.role not in allowed and user.role != "admin":
            raise HTTPException(
                403, f"Requer role: {allowed} (atual: {user.role})"
            )
        return user

    return check
