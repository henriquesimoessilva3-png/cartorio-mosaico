from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import Token, UsuarioCreate, UsuarioRead, UsuarioUpdate
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
    token = create_access_token(user.id, user.role)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UsuarioRead)
def me(user: Annotated[Usuario, Depends(get_current_user)]):
    return user


@router.post(
    "/register",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UsuarioCreate, db: DbSession, _: AdminOnly):
    if db.execute(
        select(Usuario).where(Usuario.email == payload.email)
    ).scalar_one_or_none():
        raise HTTPException(409, "Email já cadastrado")
    user = Usuario(
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
def listar_usuarios(db: DbSession, _: AdminOnly):
    return db.execute(select(Usuario).order_by(Usuario.id)).scalars().all()


@router.put("/users/{user_id}", response_model=UsuarioRead)
def atualizar_usuario(
    user_id: int,
    payload: UsuarioUpdate,
    db: DbSession,
    _: AdminOnly,
):
    user = db.get(Usuario, user_id)
    if user is None:
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
    if user.id == current_user.id:
        raise HTTPException(400, "Não é possível desativar a própria conta")
    user.ativo = False
    db.commit()
    return None
