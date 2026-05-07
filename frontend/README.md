# Frontend — Cartório Mosaico

V0.1: Vite + React + TS, mapa MapLibre + Esri Satellite, indicador de status do backend.

## Setup

```bash
cd frontend
npm install              # ou pnpm install / yarn
npm run dev              # http://localhost:5173
```

O proxy do Vite em `vite.config.ts` redireciona `/api/*` e `/health` para `http://localhost:8000` — basta o backend estar rodando local.

## Cliente da API

`src/api/client.ts` já tem helpers tipados para:

- `healthCheck()`
- `listarMatriculas()`, `criarMatricula()`
- `criarLote()`
- `memorialPdfUrl(loteId)`
- `buscarMosaico()` (FeatureCollection)

## Próximos passos (não implementados)

Portar do `prototype/index.html`:

- `MapEditor.tsx` — busca de endereço (Nominatim), mapa base
- `PolygonEditor.tsx` — clique para vértice + drag de vértices existentes; cálculo live via Turf+proj4
- `Mosaico.tsx` — `GET /api/mosaico` + camada com cores por status; clique no lote → detalhes
- `MatriculaForm.tsx` — CRUD UI consumindo `/api/matriculas`
- `Conflitos.tsx` — `GET /api/mosaico/conflitos` em painel lateral

Auth com JWT (HS256) — fluxo de login antes de qualquer mutação.
