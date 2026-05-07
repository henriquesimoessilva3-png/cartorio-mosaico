"""Validação textual rica:
   - extrai medidas em metros e compara com lados reais
   - extrai confrontantes por lado (frente, fundo, direita, esquerda)
   - sugere descrição de confrontante por lado quando o texto é claro
"""
from __future__ import annotations

import re
from typing import TypedDict

_RE_METROS = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:m|metros?)\b",
    flags=re.IGNORECASE,
)

# Padrões de confrontante: capturam o que vem após a expressão de lado.
# Aceitam vírgula, ponto-e-vírgula, ponto final ou " e " como delimitadores.
_DELIM = r"(?=,|;|\.|\s+e\s+|$)"
_PATTERNS_LADO: dict[str, list[str]] = {
    "frente": [
        rf"(?:de\s+)?frente\s+(?:para|com|para\s+a|para\s+o)\s+([^,;.\n]+?){_DELIM}",
        rf"pela\s+frente\s+(?:com|para|para\s+a)\s+([^,;.\n]+?){_DELIM}",
    ],
    "fundo": [
        rf"(?:nos?\s+|com\s+|aos?\s+)?fundos?\s+(?:com|para)\s+([^,;.\n]+?){_DELIM}",
        rf"pelo\s+fundo\s+(?:com|para)\s+([^,;.\n]+?){_DELIM}",
    ],
    "direita": [
        rf"(?:pela|à|a|na|do)\s+(?:lado\s+)?direita?\s+(?:com|para)\s+([^,;.\n]+?){_DELIM}",
        rf"lado\s+direito\s+(?:com|para)\s+([^,;.\n]+?){_DELIM}",
    ],
    "esquerda": [
        rf"(?:pela|à|a|na|do)\s+(?:lado\s+)?esquerd[ao]?\s+(?:com|para)\s+([^,;.\n]+?){_DELIM}",
        rf"lado\s+esquerdo\s+(?:com|para)\s+([^,;.\n]+?){_DELIM}",
    ],
}


class MatchInfo(TypedDict):
    valor_texto_m: float
    lado_real_m: float
    diff_pct: float


class ConfrontanteInferido(TypedDict):
    lado: str
    descricao: str


class ValidacaoResultado(TypedDict):
    numeros_extraidos: list[float]
    matches: list[MatchInfo]
    avisos: list[str]
    confrontantes_textuais: list[ConfrontanteInferido]


def extrair_medidas_metros(texto: str) -> list[float]:
    if not texto:
        return []
    out = []
    for m in _RE_METROS.findall(texto):
        try:
            out.append(float(m.replace(",", ".")))
        except ValueError:
            continue
    return out


def extrair_confrontantes_textuais(texto: str) -> list[ConfrontanteInferido]:
    if not texto:
        return []
    out: list[ConfrontanteInferido] = []
    for lado, patterns in _PATTERNS_LADO.items():
        for pat in patterns:
            m = re.search(pat, texto, flags=re.IGNORECASE)
            if m:
                desc = re.sub(r"\s+", " ", m.group(1)).strip(" ,.;")
                if desc:
                    out.append({"lado": lado, "descricao": desc})
                break
    return out


def comparar_descricao_vs_lados(
    descricao: str,
    distancias_lados_m: list[float],
    tolerancia_pct: float = 15.0,
) -> ValidacaoResultado:
    nums = extrair_medidas_metros(descricao)
    confrontantes = extrair_confrontantes_textuais(descricao)
    matches: list[MatchInfo] = []
    avisos: list[str] = []

    if distancias_lados_m:
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

    return {
        "numeros_extraidos": nums,
        "matches": matches,
        "avisos": avisos,
        "confrontantes_textuais": confrontantes,
    }
