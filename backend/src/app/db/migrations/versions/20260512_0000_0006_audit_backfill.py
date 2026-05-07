"""Backfill de tenant_id em audit_log para logs antigos com user_id resolvível.

Revision ID: 0006_audit_backfill
Revises: 0005_import_jobs
Create Date: 2026-05-12

Logs criados ANTES da migration 0002_multitenant ficaram com tenant_id NULL.
Esta migration popula tenant_id quando o user_id está presente e o usuário
pertence a um tenant. Logs sem user_id (ex.: ações antes do fix do middleware
do Item 0) continuam NULL — não há como associá-los retroativamente.

Idempotente: roda só onde tenant_id IS NULL.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006_audit_backfill"
down_revision: Union[str, None] = "0005_import_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE audit_log al
        SET tenant_id = u.tenant_id
        FROM usuario u
        WHERE al.user_id = u.id
          AND al.tenant_id IS NULL
          AND u.tenant_id IS NOT NULL
        """
    )


def downgrade() -> None:
    # Não reverte: backfill é informacional, não destrutivo.
    pass
