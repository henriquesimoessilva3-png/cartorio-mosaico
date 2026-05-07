"""Importador de matrículas a partir de CSV.

Uso:
    python scripts/import_matriculas.py path/to/matriculas.csv

Schema do CSV (cabeçalho na 1ª linha; somente `numero` é obrigatório):

    numero, livro_folha, ano_abertura, proprietario_atual_nome,
    cpf_cnpj, endereco_logradouro, endereco_numero, endereco_complemento,
    endereco_bairro, area_descrita_texto, area_descrita_m2, observacoes

Comportamento:
- `numero` é a chave única; linhas com numero existente são ATUALIZADAS (upsert).
- `cpf_cnpj` em texto plano: armazenado como `cpf_cnpj_hash` (HMAC-SHA256
  com SECRET_KEY) + `cpf_cnpj_ultimo_digito` para conferência humana.
- `area_descrita_m2` aceita vírgula decimal BR ("12.345,67") ou ponto.
- Campos vazios viram NULL.
- O DB precisa estar acessível via DATABASE_URL (ver .env). Migrations
  precisam estar aplicadas (`alembic upgrade head`).

Exemplo:
    python scripts/import_matriculas.py scripts/sample_matriculas.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
BACKEND_SRC = THIS_DIR.parent / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from sqlalchemy import select  # noqa: E402

from app.db.database import SessionLocal  # noqa: E402
from app.models.matricula import Matricula  # noqa: E402
from app.services.security import hash_cpf_cnpj, last_digit  # noqa: E402

REQUIRED_COLUMNS = {"numero"}


def parse_decimal_br(s: str | None) -> float | None:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    return float(s.replace(".", "").replace(",", ".") if "," in s else s)


def parse_int(s: str | None) -> int | None:
    if s is None or not s.strip():
        return None
    return int(s.strip())


def _clean(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.strip()
    return s or None


def import_csv(csv_path: Path) -> dict:
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    inserted = updated = skipped = 0
    errors: list[tuple[int, str]] = []

    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - cols
        if missing:
            raise ValueError(f"Colunas obrigatórias faltando: {sorted(missing)}")

        with SessionLocal() as db:
            for row_num, row in enumerate(reader, start=2):
                numero = _clean(row.get("numero"))
                if not numero:
                    errors.append((row_num, "numero vazio"))
                    skipped += 1
                    continue

                try:
                    cpf = _clean(row.get("cpf_cnpj"))
                    data: dict = {
                        "livro_folha": _clean(row.get("livro_folha")),
                        "ano_abertura": parse_int(row.get("ano_abertura")),
                        "proprietario_atual_nome": _clean(
                            row.get("proprietario_atual_nome")
                        ),
                        "endereco_logradouro": _clean(row.get("endereco_logradouro")),
                        "endereco_numero": _clean(row.get("endereco_numero")),
                        "endereco_complemento": _clean(
                            row.get("endereco_complemento")
                        ),
                        "endereco_bairro": _clean(row.get("endereco_bairro")),
                        "area_descrita_texto": _clean(row.get("area_descrita_texto")),
                        "area_descrita_m2": parse_decimal_br(
                            row.get("area_descrita_m2")
                        ),
                        "observacoes": _clean(row.get("observacoes")),
                        "cpf_cnpj_hash": hash_cpf_cnpj(cpf) if cpf else None,
                        "cpf_cnpj_ultimo_digito": last_digit(cpf) if cpf else None,
                    }
                except ValueError as e:
                    errors.append((row_num, f"erro de parse: {e}"))
                    skipped += 1
                    continue

                existing = db.execute(
                    select(Matricula).where(Matricula.numero == numero)
                ).scalar_one_or_none()

                if existing is None:
                    db.add(Matricula(numero=numero, **data))
                    inserted += 1
                else:
                    for k, v in data.items():
                        setattr(existing, k, v)
                    updated += 1

            db.commit()

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python scripts/import_matriculas.py <csv_path>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    print(f"Importando {path}...")
    try:
        summary = import_csv(path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1

    print(f"  inseridas:   {summary['inserted']}")
    print(f"  atualizadas: {summary['updated']}")
    print(f"  ignoradas:   {summary['skipped']}")
    if summary["errors"]:
        print(f"  erros:       {len(summary['errors'])}")
        for row_num, msg in summary["errors"][:10]:
            print(f"    linha {row_num}: {msg}")
        if len(summary["errors"]) > 10:
            print(f"    ... ({len(summary['errors']) - 10} mais)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
