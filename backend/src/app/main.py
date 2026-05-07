from fastapi import FastAPI

from app.api import auth, lotes, matriculas, memoriais, mosaico
from app.middleware.audit import AuditMiddleware

app = FastAPI(
    title="Cartório Mosaico API",
    version="0.2.0",
    description=(
        "Cadastro técnico para reconstrução geométrica de matrículas com descrição precária. "
        "Saída é documento auxiliar interno — não substitui ART de agrimensor."
    ),
)

app.add_middleware(AuditMiddleware)

app.include_router(auth.router)
app.include_router(matriculas.router)
app.include_router(lotes.router)
app.include_router(mosaico.router)
app.include_router(memoriais.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
