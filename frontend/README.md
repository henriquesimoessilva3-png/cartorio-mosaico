# Frontend — Cartório Mosaico

Pendente: scaffold via Vite (item 5 do plano técnico).

```bash
npm create vite@latest . -- --template react-ts
npm install
npm install maplibre-gl @turf/turf proj4
```

Componentes-alvo:

- `MapEditor.tsx` — mapa base + busca de endereço
- `PolygonEditor.tsx` — desenho de polígono com métricas em tempo real
- `Mosaico.tsx` — vista agregada da circunscrição
