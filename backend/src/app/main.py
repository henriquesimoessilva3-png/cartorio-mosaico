from fastapi import FastAPI

from app.api import matriculas

app = FastAPI(
    title="Cartório Mosaico API",
    version="0.1.0",
    description=(
        "Cadastro técnico para reconstrução geométrica de matrículas com descrição precária. "
        "Saída é documento auxiliar interno — não substitui ART de agrimensor."
    ),
)

app.include_router(matriculas.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
