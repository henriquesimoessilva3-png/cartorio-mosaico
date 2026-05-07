from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import (  # noqa: E402, F401
    audit_log,
    confrontante,
    import_job,
    lote_geometria,
    matricula,
    tenant,
    usuario,
)
