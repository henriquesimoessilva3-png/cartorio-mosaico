"""Source CSV: lê arquivo no schema documentado em scripts/import_matriculas.py."""
from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from pathlib import Path

from app.schemas.matricula import MatriculaCreate

REQUIRED_COLUMNS = {"numero"}


def _parse_decimal_br(s: str | None) -> float | None:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    return float(s.replace(".", "").replace(",", ".") if "," in s else s)


def _parse_int(s: str | None) -> int | None:
    if s is None or not s.strip():
        return None
    return int(s.strip())


def _clean(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.strip()
    return s or None


class CsvSource:
    """Itera linhas de um CSV produzindo MatriculaCreate. Linhas inválidas
    são puladas (caller pode capturar via Pydantic ValidationError).
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)

    def iter_records(self) -> Iterable[MatriculaCreate]:
        return self._iter()

    def _iter(self) -> Iterator[MatriculaCreate]:
        with self.path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cols = set(reader.fieldnames or [])
            missing = REQUIRED_COLUMNS - cols
            if missing:
                raise ValueError(f"Colunas obrigatórias faltando: {sorted(missing)}")

            for row in reader:
                numero = _clean(row.get("numero"))
                if not numero:
                    # Pula linha sem número silenciosamente — caller pode
                    # validar antes se quiser registrar como erro.
                    continue
                yield MatriculaCreate(
                    numero=numero,
                    livro_folha=_clean(row.get("livro_folha")),
                    ano_abertura=_parse_int(row.get("ano_abertura")),
                    proprietario_atual_nome=_clean(row.get("proprietario_atual_nome")),
                    cpf_cnpj=_clean(row.get("cpf_cnpj")),
                    endereco_logradouro=_clean(row.get("endereco_logradouro")),
                    endereco_numero=_clean(row.get("endereco_numero")),
                    endereco_complemento=_clean(row.get("endereco_complemento")),
                    endereco_bairro=_clean(row.get("endereco_bairro")),
                    area_descrita_texto=_clean(row.get("area_descrita_texto")),
                    area_descrita_m2=_parse_decimal_br(row.get("area_descrita_m2")),
                    observacoes=_clean(row.get("observacoes")),
                )
