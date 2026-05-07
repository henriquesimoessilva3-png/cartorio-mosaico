from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import Token, UsuarioCreate, UsuarioRead
from app.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]


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
def register(
    payload: UsuarioCreate,
    db: DbSession,
    _: Annotated[Usuario, Depends(require_role("admin"))],
):
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
