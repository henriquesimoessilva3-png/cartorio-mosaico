# Arquitetura — Cartório Mosaico

Resumo de alto nível. Detalhe completo no plano técnico em `~/.claude/plans/quero-criar-um-servico-deep-beacon.md`.

## Camadas

```
┌──────────────────────────────────────────────────┐
│  Browser                                         │
│   Vite + React + TS                              │
│   MapLibre GL + Esri/Mapbox tiles                │
│   Turf.js (geom client)  proj4js (datum client)  │
└────────────┬─────────────────────────────────────┘
             │ HTTPS
┌────────────▼─────────────────────────────────────┐
│  FastAPI (Python 3.12)                           │
│   /api/matriculas      CRUD                      │
│   /api/lotes           geometria + versões       │
│   /api/memoriais       gera PDF                  │
│   /api/mosaico         agregado, conflitos       │
│   services/                                      │
│     memorial.py  geo.py  topology.py             │
└────────────┬─────────────────────────────────────┘
             │ SQLAlchemy 2 + GeoAlchemy2
┌────────────▼─────────────────────────────────────┐
│  PostgreSQL 16 + PostGIS 3.4                     │
│   matricula  lote_geometria (POLYGON 4674)       │
│   confrontante  usuario  audit_log               │
└──────────────────────────────────────────────────┘
```

## Padrão geodésico

- **Datum**: SIRGAS 2000 (EPSG:4674) — armazenamento
- **Projeção métrica**: UTM 23S (EPSG:31983) — para cálculo de área e azimute
- Conversões: server-side (`pyproj`) e client-side (`proj4js`)

## Versionamento de geometria

Cada alteração cria nova linha em `lote_geometria` com `versao+1`. Memoriais antigos seguem rastreáveis via `hash_documento`.

## Roles

- `admin` — tudo
- `escrivao` — CRUD matrícula + valida geometria
- `escrevente` — desenha geometria, status=rascunho
- `leitura` — só GET

## Fluxo de geração de memorial

```
matricula + lote_geometria
    └─→ services/geo.py
         · WGS84 → SIRGAS 2000 / UTM
         · azimutes consecutivos
         · área (Gauss/UTM)
    └─→ services/memorial.py
         · Jinja2 + WeasyPrint
         · template em /templates/memorial_descritivo.html.j2
    └─→ PDF + hash_documento gravado
```

## Mosaico

- `GET /api/mosaico` retorna FeatureCollection GeoJSON
- `GET /api/mosaico/conflitos` usa `ST_Intersects` (overlap) e `ST_Difference` contra polígono da quadra (gap)
