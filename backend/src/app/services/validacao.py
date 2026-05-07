"""Validação textual rica:
   - extrai medidas em metros e compara com lados reais
   - extrai confrontantes por lado (frente, fundo, direita, esquerda)
   - sugere descrição de confrontante por lado quando o texto é claro
   - aceita números em palavras ("doze metros" → 12.0)
"""
from __future__ import annotations

import re
from typing import TypedDict

_RE_METROS = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:m|metros?)\b",
    flags=re.IGNORECASE,
)

# Números em palavras (PT-BR) suportados até 999. Cartórios raramente
# descrevem lados maiores que isso por extenso.
_NUM_PT: dict[str, int] = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2,
    "tres": 3, "três": 3, "quatro": 4, "cinco": 5, "seis": 6,
    "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11,
    "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18,
    "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40,
    "cinquenta": 50, "cinqüenta": 50, "sessenta": 60, "setenta": 70,
    "oitenta": 80, "noventa": 90, "cem": 100, "cento": 100,
    "duzentos": 200, "trezentos": 300, "quatrocentos": 400,
    "quinhentos": 500, "seiscentos": 600, "setecentos": 700,
    "oitocentos": 800, "novecentos": 900,
}

_NUM_PT_WORDS = "|".join(sorted(_NUM_PT.keys(), key=len, reverse=True))
_RE_METROS_TEXTO = re.compile(
    rf"\b((?:(?:{_NUM_PT_WORDS})(?:\s+e\s+|\s+))*(?:{_NUM_PT_WORDS}))"
    r"(?:\s+(?:vírgula|virgula)\s+((?:" + _NUM_PT_WORDS + r")(?:\s+e\s+(?:" + _NUM_PT_WORDS + r"))*))?"
    r"\s+(?:m|metros?)\b",
    flags=re.IGNORECASE,
)


def _parse_pt_number(text: str) -> int | None:
    """Converte uma sequência de palavras em PT-BR para inteiro (0-999).

    Aceita formas como "doze", "vinte e cinco", "cento e dez", "trezentos
    e quarenta e dois". Retorna None se algum token não for número válido.
    """
    tokens = [t for t in re.split(r"\s+", text.strip().lower()) if t and t != "e"]
    if not tokens:
        return None
    total = 0
    current = 0
    for tok in tokens:
        v = _NUM_PT.get(tok)
        if v is None:
            return None
        if v >= 100:
            current = v if current == 0 else current * v
        elif v >= 20:
            current += v
        else:
            current += v
    return total + current

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
    """Extrai medidas em metros do texto. Aceita "12m", "12,5 metros" e
    formas por extenso como "doze metros" ou "vinte e cinco metros e meio"
    (esta última via combinação de inteiro + fração na regex texto).
    """
    if not texto:
        return []
    out: list[float] = []
    for m in _RE_METROS.findall(texto):
        try:
            out.append(float(m.replace(",", ".")))
        except ValueError:
            continue
    for inteiro_txt, fracao_txt in _RE_METROS_TEXTO.findall(texto):
        inteiro = _parse_pt_number(inteiro_txt)
        if inteiro is None:
            continue
        valor = float(inteiro)
        if fracao_txt:
            fracao = _parse_pt_number(fracao_txt)
            if fracao is not None:
                # "doze vírgula cinco" → 12.5; "doze vírgula vinte e cinco" → 12.25
                # Usa o número de dígitos do valor inteiro de fração.
                divisor = 10 ** len(str(fracao)) if fracao > 0 else 1
                valor += fracao / divisor
        out.append(valor)
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
