from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.schemas.auth import (
    MeResponse,
    Token,
    UsuarioCreate,
    UsuarioRead,
    UsuarioUpdate,
)
from app.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
AdminOnly = Annotated[Usuario, Depends(require_role("admin"))]


@router.post("/login", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
):
    user = db.execute(
        select(Usuario).where(Usuario.email == form.username)
    ).scalar_one_or_none()
    if (
        user is None
        or not verify_password(form.password, user.password_hash)
        or not user.ativo
    ):
        raise HTTPException(401, "Credenciais inválidas")
    token = create_access_token(user.id, user.role, user.tenant_id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=MeResponse)
def me(user: Annotated[Usuario, Depends(get_current_user)], db: DbSession):
    tenant = db.get(Tenant, user.tenant_id) if user.tenant_id is not None else None
    return MeResponse(
        id=user.id,
        nome=user.nome,
        email=user.email,
        role=user.role,
        ativo=user.ativo,
        criado_em=user.criado_em,
        tenant_id=user.tenant_id,
        tenant=tenant,
    )


@router.post(
    "/register",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UsuarioCreate, db: DbSession, current: AdminOnly):
    if db.execute(
        select(Usuario).where(Usuario.email == payload.email)
    ).scalar_one_or_none():
        raise HTTPException(409, "Email já cadastrado")
    # tenant_id: usa o do payload se admin global; senão herda do criador.
    if current.tenant_id is None:
        tenant_id = payload.tenant_id
    else:
        tenant_id = current.tenant_id
    user = Usuario(
        tenant_id=tenant_id,
        nome=payload.nome,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UsuarioRead])
def listar_usuarios(db: DbSession, current: AdminOnly):
    stmt = select(Usuario).order_by(Usuario.id)
    if current.tenant_id is not None:
        stmt = stmt.where(Usuario.tenant_id == current.tenant_id)
    return db.execute(stmt).scalars().all()


@router.put("/users/{user_id}", response_model=UsuarioRead)
def atualizar_usuario(
    user_id: int,
    payload: UsuarioUpdate,
    db: DbSession,
    current: AdminOnly,
):
    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(404, "Usuário não encontrado")
    if current.tenant_id is not None and user.tenant_id != current.tenant_id:
        raise HTTPException(404, "Usuário não encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data.pop("password"))
    elif "password" in data:
        data.pop("password")
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_usuario(
    user_id: int,
    db: DbSession,
    current_user: AdminOnly,
):
    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(404, "Usuário não encontrado")
    if current_user.tenant_id is not None and user.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "Usuário não encontrado")
    if user.id == current_user.id:
        raise HTTPException(400, "Não é possível desativar a própria conta")
    user.ativo = False
    db.commit()
    return None
