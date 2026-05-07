from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin_imports,
    auditorias,
    auth,
    lotes,
    matriculas,
    memoriais,
    mosaico,
)
from app.config import settings
from app.middleware.audit import AuditMiddleware

app = FastAPI(
    title="Cartório Mosaico API",
    version="0.2.0",
    description=(
        "Cadastro técnico para reconstrução geométrica de matrículas com descrição precária. "
        "Saída é documento auxiliar interno — não substitui ART de agrimensor."
    ),
)

# CORS — separado por vírgula no env CORS_ORIGINS. Vazio = mesma origem
# do backend (caso default em dev local).
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(AuditMiddleware)

app.include_router(auth.router)
app.include_router(matriculas.router)
app.include_router(lotes.router)
app.include_router(mosaico.router)
app.include_router(memoriais.router)
app.include_router(auditorias.router)
app.include_router(admin_imports.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
