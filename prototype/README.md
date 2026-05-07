# Protótipo HTML — Cartório Mosaico

Um único arquivo HTML autônomo para validar o conceito sem precisar subir backend.

## Como abrir

Duplo clique no `index.html`, ou no terminal:

```bash
open ~/projetos/cartorio-mosaico/prototype/index.html
```

Uma cópia também fica em `Projeto Memorial Descritivo Google Maps/prototipo.html` (no Drive) para acesso fácil pelo Finder.

## O que faz

- Mapa centrado em Ferros, MG, com imagem de satélite Esri.
- Busca de endereço via Nominatim (OpenStreetMap).
- Desenho de polígono clicando no mapa.
- Métricas em tempo real: área (m² e ha), perímetro, distância de cada lado e azimute em SIRGAS 2000 / UTM 23S (sexagesimal `DDD°MM'SS"`).
- Formulário de matrícula (número, proprietário, endereço, descrição textual).
- Geração inline do memorial descritivo formatado, com tabela de coordenadas UTM e geodésicas.
- Imprimir / Salvar como PDF via diálogo de impressão do navegador.
- Persistência local de lotes salvos (localStorage do navegador).
- Exportação de todos os lotes salvos em GeoJSON.

## Limitações

- Sem backend, sem multi-usuário, sem audit log.
- Lotes ficam salvos só no navegador deste dispositivo (localStorage). Limpar dados do navegador apaga.
- Confrontantes ficam como `________________` no memorial (a preencher manualmente).
- Esri tiles têm uso permitido para protótipos / educacional. Para produção, ver ToS.

## Stack (CDN)

- MapLibre GL JS 4.7
- Turf.js 7
- proj4js 2.11
