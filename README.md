# Cartório Mosaico

Cadastro técnico para reconstrução geométrica de matrículas de cartório com descrição precária. Localiza imóveis sobre imagem de satélite, gera memorial descritivo auxiliar e monta mosaico topológico da circunscrição (detecta sobreposições e gaps entre matrículas vizinhas).

## Demo (protótipo)

Protótipo HTML rodando em GitHub Pages:
**https://henriquesimoessilva3-png.github.io/cartorio-mosaico/**

Funciona sem backend — desenhe um lote sobre satélite, veja área/perímetro/azimutes em SIRGAS 2000 / UTM 23S, gere o memorial descritivo e imprima/salve em PDF pelo navegador.

## Status

V0 — scaffold + protótipo + API CRUD. Componentes implementados: estrutura de pastas, schema PostGIS via Alembic, FastAPI com CRUD de matrículas, importador CSV, protótipo HTML autônomo.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 + GeoAlchemy2, Alembic, PostgreSQL 16 + PostGIS 3.4
- **Frontend** (a fazer): Vite + React + TypeScript, MapLibre GL, Turf.js, proj4js
- **PDF**: Jinja2 + WeasyPrint
- **Padrão geodésico**: SIRGAS 2000 (EPSG:4674), UTM 23S (EPSG:31983), azimutes sexagesimais

## Como rodar (V0)

Pré-requisitos: Docker, Python 3.12, `uv` (recomendado) ou `pip`.

```bash
# 1. Sobe o Postgres+PostGIS
docker compose up -d postgres

# 2. Backend: instala deps e roda migrations
cd backend
uv sync                          # ou: pip install -e .[dev]
alembic upgrade head

# 3. Roda API
uv run uvicorn app.main:app --reload --app-dir src
# ou: uvicorn app.main:app --reload --app-dir src

# Health check
curl http://localhost:8000/health
```

## Próximos passos

1. Item 3 do plano: API CRUD matrículas
2. Item 4: Importador CSV
3. Item 5+: frontend

## Posicionamento jurídico

Saída do MVP é **documento auxiliar interno do cartório**. Não substitui ART de agrimensor nem levantamento de campo. Todo PDF gerado traz disclaimer obrigatório.

## Deploy em VPS

Guia completo em [docs/DEPLOY.md](docs/DEPLOY.md). Estimativa: ~€4/mês em Hetzner CX22 com `docker compose -f docker-compose.prod.yml up -d`.
