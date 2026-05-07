"""Validação textual: extrai medidas da descrição da matrícula e compara com lados reais."""
from __future__ import annotations

import re
from typing import TypedDict

# Captura "12m", "12 m", "12,5 m", "12.5 metros", "30 metros"
_RE_METROS = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:m|metros?)\b",
    flags=re.IGNORECASE,
)


class MatchInfo(TypedDict):
    valor_texto_m: float
    lado_real_m: float
    diff_pct: float


class ValidacaoResultado(TypedDict):
    numeros_extraidos: list[float]
    matches: list[MatchInfo]
    avisos: list[str]


def extrair_medidas_metros(texto: str) -> list[float]:
    """Retorna todas as medidas em metros encontradas no texto."""
    if not texto:
        return []
    out = []
    for m in _RE_METROS.findall(texto):
        try:
            out.append(float(m.replace(",", ".")))
        except ValueError:
            continue
    return out


def comparar_descricao_vs_lados(
    descricao: str,
    distancias_lados_m: list[float],
    tolerancia_pct: float = 15.0,
) -> ValidacaoResultado:
    """Compara medidas extraídas do texto com os lados reais do polígono.

    Para cada número no texto, encontra o lado mais próximo e verifica se a
    diferença está dentro da tolerância. Reporta avisos para divergências.
    """
    nums = extrair_medidas_metros(descricao)
    matches: list[MatchInfo] = []
    avisos: list[str] = []

    if not distancias_lados_m:
        return {"numeros_extraidos": nums, "matches": [], "avisos": []}

    for n in nums:
        nearest = min(distancias_lados_m, key=lambda d: abs(d - n))
        diff_pct = abs(nearest - n) / n * 100 if n else 0.0
        matches.append(
            {"valor_texto_m": n, "lado_real_m": nearest, "diff_pct": diff_pct}
        )
        if diff_pct > tolerancia_pct:
            avisos.append(
                f"Texto cita {n}m mas lado mais próximo tem {nearest:.2f}m "
                f"(diferença {diff_pct:.0f}%)."
            )

    return {"numeros_extraidos": nums, "matches": matches, "avisos": avisos}
