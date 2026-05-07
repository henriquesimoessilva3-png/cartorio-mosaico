"""Cria o primeiro usuário admin (bootstrap).

Uso:
    python scripts/create_admin.py "Nome Completo" email@x.com senha-12345

Atenção: senha precisa ter no mínimo 8 caracteres.
"""
from __future__ import annotations

import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent / "backend" / "src"))

from sqlalchemy import select  # noqa: E402

from app.db.database import SessionLocal  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.services.auth import hash_password  # noqa: E402


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Uso: python scripts/create_admin.py 'Nome' email senha",
            file=sys.stderr,
        )
        return 2

    nome, email, senha = sys.argv[1:4]
    if len(senha) < 8:
        print("Senha precisa ter no mínimo 8 caracteres", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        existing = db.execute(
            select(Usuario).where(Usuario.email == email)
        ).scalar_one_or_none()
        if existing:
            print(f"Já existe usuário com email {email} (id={existing.id})")
            return 1

        u = Usuario(
            nome=nome,
            email=email,
            password_hash=hash_password(senha),
            role="admin",
            ativo=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        print(f"Admin criado: id={u.id} email={u.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
