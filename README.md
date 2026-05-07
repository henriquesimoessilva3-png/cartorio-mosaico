# Cartório Mosaico

Cadastro técnico para reconstrução geométrica de matrículas de cartório com descrição precária. Localiza imóveis sobre imagem de satélite, gera memorial descritivo auxiliar e monta mosaico topológico da circunscrição (detecta sobreposições e gaps entre matrículas vizinhas).

## Status

V0 — scaffold. Componentes implementados: estrutura de pastas, schema PostGIS via Alembic, esqueleto FastAPI.

Plano técnico completo: `~/.claude/plans/quero-criar-um-servico-deep-beacon.md`

## Documentos do projeto (não-código)

`/Users/henriquesimoessilva/Meu Drive/arquivos pessoais/Projeto Memorial Descritivo Google Maps/`

Use essa pasta para anexar memoriais descritivos reais do acervo, briefings, propostas. **Não colocar código lá** — Drive sincronizando node_modules estoura cota.

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
