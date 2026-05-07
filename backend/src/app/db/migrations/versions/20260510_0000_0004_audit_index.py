"""Índice composto em audit_log (criado_em DESC, entidade) para a tela de auditoria.

Revision ID: 0004_audit_index
Revises: 0003_gist_indexes
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004_audit_index"
down_revision: Union[str, None] = "0003_gist_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_log_criado_entidade "
        "ON audit_log (criado_em DESC, entidade)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_log_criado_entidade")
