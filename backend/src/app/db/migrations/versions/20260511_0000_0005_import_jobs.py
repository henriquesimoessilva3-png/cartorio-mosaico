"""Tabela import_job para registrar execuções do importador (CSV, vendors).

Revision ID: 0005_import_jobs
Revises: 0004_audit_index
Create Date: 2026-05-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_import_jobs"
down_revision: Union[str, None] = "0004_audit_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "import_job",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer,
            sa.ForeignKey("tenant.id"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("params_jsonb", postgresql.JSONB),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("inserted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors_jsonb", postgresql.JSONB),
        sa.Column(
            "criado_por_user_id",
            sa.Integer,
            sa.ForeignKey("usuario.id"),
            nullable=True,
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finalizado_em", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_import_job_tenant_criado",
        "import_job",
        ["tenant_id", sa.text("criado_em DESC")],
    )
    op.create_index("ix_import_job_status", "import_job", ["status"])


def downgrade() -> None:
    op.drop_index("ix_import_job_status", table_name="import_job")
    op.drop_index("ix_import_job_tenant_criado", table_name="import_job")
    op.drop_table("import_job")
