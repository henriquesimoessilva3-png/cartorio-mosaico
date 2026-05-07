from fastapi import FastAPI

app = FastAPI(
    title="Cartório Mosaico API",
    version="0.1.0",
    description=(
        "Cadastro técnico para reconstrução geométrica de matrículas com descrição precária. "
        "Saída é documento auxiliar interno — não substitui ART de agrimensor."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
