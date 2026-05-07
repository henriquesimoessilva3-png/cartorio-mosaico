"""Importador CLI de matrículas a partir de CSV.

Uso:
    python scripts/import_matriculas.py [--tenant <slug>] <csv_path>

Schema do CSV (cabeçalho na 1ª linha; somente `numero` é obrigatório):
    numero, livro_folha, ano_abertura, proprietario_atual_nome,
    cpf_cnpj, endereco_logradouro, endereco_numero, endereco_complemento,
    endereco_bairro, area_descrita_texto, area_descrita_m2, observacoes

Comportamento:
- Upsert por (tenant_id, numero) — linhas com numero já existente no tenant
  são ATUALIZADAS.
- `cpf_cnpj` em texto plano é hashado (HMAC-SHA256 + SECRET_KEY) +
  `cpf_cnpj_ultimo_digito` para conferência humana.
- `area_descrita_m2` aceita decimal BR ("12.345,67") ou ponto.

Migrations precisam estar aplicadas (`alembic upgrade head`).
"""
from __future__ import annotations

import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
BACKEND_SRC = THIS_DIR.parent / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from sqlalchemy import select  # noqa: E402

from app.db.database import SessionLocal  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.services.importers import CsvSource, run_import  # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    tenant_slug = "default"
    if len(args) >= 2 and args[0] == "--tenant":
        tenant_slug = args[1]
        args = args[2:]
    if len(args) != 1:
        print(
            "Uso: python scripts/import_matriculas.py [--tenant <slug>] <csv_path>",
            file=sys.stderr,
        )
        return 2

    path = Path(args[0])
    if not path.exists():
        print(f"Arquivo não encontrado: {path}", file=sys.stderr)
        return 1

    print(f"Importando {path} para tenant '{tenant_slug}'...")

    with SessionLocal() as db:
        tenant = db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        ).scalar_one_or_none()
        if tenant is None:
            print(
                f"Tenant slug='{tenant_slug}' não encontrado — rode alembic upgrade head",
                file=sys.stderr,
            )
            return 1

        try:
            source = CsvSource(path)
            summary = run_import(db, source, tenant_id=tenant.id)
        except (FileNotFoundError, ValueError) as e:
            print(f"Erro: {e}", file=sys.stderr)
            return 1

    print(f"  inseridas:   {summary.inserted}")
    print(f"  atualizadas: {summary.updated}")
    print(f"  ignoradas:   {summary.skipped}")
    if summary.errors:
        print(f"  erros:       {len(summary.errors)}")
        for err in summary.errors[:10]:
            print(f"    {err}")
        if len(summary.errors) > 10:
            print(f"    ... ({len(summary.errors) - 10} mais)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
