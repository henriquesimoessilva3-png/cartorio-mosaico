"""multi-tenant: tabela tenant + tenant_id em todas as tabelas de domínio

Revision ID: 0002_multitenant
Revises: 0001_initial
Create Date: 2026-05-08

Após esta migration:
- Existe tabela `tenant` com pelo menos 1 linha (slug='default').
- Toda matrícula/lote/confrontante/audit_log existente foi associado ao tenant default.
- usuario.tenant_id é NULLABLE (NULL = admin global cross-tenant).
- audit_log.tenant_id é NULLABLE (logs antigos podem não ter tenant resolvível).
- usuario.email continua UNIQUE global — login não inclui slug do tenant.
- matricula UNIQUE de `numero` virou composto `(tenant_id, numero)` — cartórios
  podem ter mesmo número em domínios diferentes.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_multitenant"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criar tabela tenant
    op.create_table(
        "tenant",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_tenant_slug", "tenant", ["slug"])

    # 2. Seed: tenant default (id captado dinamicamente para uso em server_default)
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO tenant (slug, nome) VALUES ('default', 'Cartório Default')"
        )
    )
    default_id = bind.execute(
        sa.text("SELECT id FROM tenant WHERE slug = 'default'")
    ).scalar_one()
    default_default = sa.text(str(default_id))

    # 3. matricula.tenant_id (NOT NULL, default = tenant default)
    op.add_column(
        "matricula",
        sa.Column(
            "tenant_id",
            sa.Integer,
            sa.ForeignKey("tenant.id"),
            nullable=False,
            server_default=default_default,
        ),
    )
    op.alter_column("matricula", "tenant_id", server_default=None)
    op.create_index("ix_matricula_tenant", "matricula", ["tenant_id"])

    # Trocar UNIQUE(numero) por UNIQUE(tenant_id, numero)
    op.drop_index("ix_matricula_numero", table_name="matricula")
    op.drop_constraint("matricula_numero_key", "matricula", type_="unique")
    op.create_index("ix_matricula_numero", "matricula", ["numero"])
    op.create_unique_constraint(
        "uq_matricula_tenant_numero", "matricula", ["tenant_id", "numero"]
    )

    # 4. lote_geometria.tenant_id (NOT NULL)
    op.add_column(
        "lote_geometria",
        sa.Column(
            "tenant_id",
            sa.Integer,
            sa.ForeignKey("tenant.id"),
            nullable=False,
            server_default=default_default,
        ),
    )
    op.alter_column("lote_geometria", "tenant_id", server_default=None)
    op.create_index("ix_lote_geometria_tenant", "lote_geometria", ["tenant_id"])

    # 5. confrontante.tenant_id (NOT NULL)
    op.add_column(
        "confrontante",
        sa.Column(
            "tenant_id",
            sa.Integer,
            sa.ForeignKey("tenant.id"),
            nullable=False,
            server_default=default_default,
        ),
    )
    op.alter_column("confrontante", "tenant_id", server_default=None)
    op.create_index("ix_confrontante_tenant", "confrontante", ["tenant_id"])

    # 6. audit_log.tenant_id (NULLABLE — logs antigos podem não ter)
    op.add_column(
        "audit_log",
        sa.Column(
            "tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=True
        ),
    )
    op.create_index("ix_audit_log_tenant", "audit_log", ["tenant_id"])

    # 7. usuario.tenant_id (NULLABLE — null = admin global)
    op.add_column(
        "usuario",
        sa.Column(
            "tenant_id", sa.Integer, sa.ForeignKey("tenant.id"), nullable=True
        ),
    )
    op.create_index("ix_usuario_tenant", "usuario", ["tenant_id"])
    # Backfill: usuários existentes herdam tenant default
    bind.execute(
        sa.text(
            "UPDATE usuario SET tenant_id = :t WHERE tenant_id IS NULL"
        ),
        {"t": default_id},
    )


def downgrade() -> None:
    op.drop_index("ix_usuario_tenant", table_name="usuario")
    op.drop_column("usuario", "tenant_id")

    op.drop_index("ix_audit_log_tenant", table_name="audit_log")
    op.drop_column("audit_log", "tenant_id")

    op.drop_index("ix_confrontante_tenant", table_name="confrontante")
    op.drop_column("confrontante", "tenant_id")

    op.drop_index("ix_lote_geometria_tenant", table_name="lote_geometria")
    op.drop_column("lote_geometria", "tenant_id")

    op.drop_constraint(
        "uq_matricula_tenant_numero", "matricula", type_="unique"
    )
    op.drop_index("ix_matricula_numero", table_name="matricula")
    op.create_unique_constraint("matricula_numero_key", "matricula", ["numero"])
    op.create_index("ix_matricula_numero", "matricula", ["numero"])
    op.drop_index("ix_matricula_tenant", table_name="matricula")
    op.drop_column("matricula", "tenant_id")

    op.drop_index("ix_tenant_slug", table_name="tenant")
    op.drop_table("tenant")
