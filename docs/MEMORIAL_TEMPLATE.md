# Template do Memorial Descritivo — formato e parâmetros

## Status

**Pendente: anexar 1 memorial descritivo real do acervo do cartório** em
`/Users/henriquesimoessilva/Meu Drive/arquivos pessoais/Projeto Memorial Descritivo Google Maps/`

Enquanto não houver modelo real, o gerador usa o **padrão genérico Brasil** descrito abaixo.
Quando o modelo real chegar, ajusta-se apenas `templates/memorial_descritivo.html.j2`
sem mexer em código.

## Padrão genérico (default V0)

| Parâmetro | Valor |
|---|---|
| Datum | SIRGAS 2000 (EPSG:4674) |
| Projeção métrica | UTM 23S (EPSG:31983) |
| Azimute | Sexagesimal `DDD°MM'SS"` a partir do norte de quadrícula |
| Varredura | Horária a partir de M0 (marco mais próximo do logradouro) |
| Distâncias | Metros, 2 casas decimais |
| Área | m² com 4 casas decimais; apresentação extra em m² + ha |
| Coordenadas no PDF | UTM (E,N) + geodésicas (lat/lon) por vértice |

## Estrutura do PDF

1. Cabeçalho: brasão/logo do cartório, comarca, número da matrícula
2. Identificação do imóvel: proprietário, endereço, área descrita textual
3. Tabela de coordenadas: M0..Mn com (E,N,lat,lon)
4. Descrição vértice-a-vértice:
   *"Tem início no marco M0, de coordenadas (E=…, N=…); daí segue com
   azimute de DDD°MM'SS" e distância de XX,XX m até o marco M1, confrontando
   com [tipo+nome do confrontante]; ..."*
5. Área e perímetro totais
6. Croqui: imagem do polígono sobre satélite (escala visível)
7. Disclaimer obrigatório:
   *"Documento de trabalho — não substitui levantamento topográfico com ART
   nem certificação SIGEF. Coordenadas obtidas a partir de imagem orbital com
   erro posicional estimado de 1 a 5 metros."*
8. Identificação do operador, data/hora, hash do documento

## Parâmetros configuráveis (futuros)

Em `templates/memorial_descritivo.html.j2`, via Jinja2:

- `cartorio_nome`, `cartorio_endereco`, `cartorio_logo_path`
- `comarca`, `municipio`
- `incluir_croqui` (bool)
- `formato_azimute` (`sexagesimal` | `decimal`)
- `texto_disclaimer` (override)
- `assinatura_responsavel_tecnico` (bool — se true, vira modo "pronto para ART")
