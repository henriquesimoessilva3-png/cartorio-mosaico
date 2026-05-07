from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import (  # noqa: E402, F401
    audit_log,
    confrontante,
    lote_geometria,
    matricula,
    usuario,
)
