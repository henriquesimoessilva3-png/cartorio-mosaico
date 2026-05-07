"""initial schema with PostGIS

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-07

"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="leitura"),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_usuario_email", "usuario", ["email"])

    op.create_table(
        "matricula",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("numero", sa.String(64), nullable=False, unique=True),
        sa.Column("livro_folha", sa.String(64)),
        sa.Column("ano_abertura", sa.Integer),
        sa.Column("proprietario_atual_nome", sa.String(255)),
        sa.Column("cpf_cnpj_hash", sa.String(64)),
        sa.Column("cpf_cnpj_ultimo_digito", sa.String(2)),
        sa.Column("endereco_logradouro", sa.String(255)),
        sa.Column("endereco_numero", sa.String(32)),
        sa.Column("endereco_complemento", sa.String(128)),
        sa.Column("endereco_bairro", sa.String(128)),
        sa.Column("area_descrita_texto", sa.Text),
        sa.Column("area_descrita_m2", sa.Numeric(14, 4)),
        sa.Column(
            "status_geometria",
            sa.String(32),
            nullable=False,
            server_default="nao_mapeado",
        ),
        sa.Column("observacoes", sa.Text),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_matricula_numero", "matricula", ["numero"])
    op.create_index("ix_matricula_status", "matricula", ["status_geometria"])

    op.create_table(
        "lote_geometria",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "matricula_id",
            sa.Integer,
            sa.ForeignKey("matricula.id"),
            nullable=False,
        ),
        sa.Column("versao", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(geometry_type="POLYGON", srid=4674),
            nullable=False,
        ),
        sa.Column("area_calculada_m2", sa.Numeric(14, 4)),
        sa.Column("perimetro_m", sa.Numeric(14, 4)),
        sa.Column("vertices_jsonb", postgresql.JSONB),
        sa.Column("azimutes_jsonb", postgresql.JSONB),
        sa.Column(
            "validado_por_user_id", sa.Integer, sa.ForeignKey("usuario.id")
        ),
        sa.Column("validado_em", sa.DateTime(timezone=True)),
        sa.Column("notas_validacao", sa.Text),
        sa.Column("hash_documento", sa.String(64)),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_lote_geometria_matricula", "lote_geometria", ["matricula_id"])

    op.create_table(
        "confrontante",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "lote_geometria_id",
            sa.Integer,
            sa.ForeignKey("lote_geometria.id"),
            nullable=False,
        ),
        sa.Column("vertice_inicio", sa.String(16), nullable=False),
        sa.Column("vertice_fim", sa.String(16), nullable=False),
        sa.Column("tipo", sa.String(32), nullable=False),
        sa.Column(
            "matricula_vizinha_id", sa.Integer, sa.ForeignKey("matricula.id")
        ),
        sa.Column("descricao_textual", sa.Text),
    )
    op.create_index(
        "ix_confrontante_lote", "confrontante", ["lote_geometria_id"]
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("usuario.id")),
        sa.Column("acao", sa.String(64), nullable=False),
        sa.Column("entidade", sa.String(64), nullable=False),
        sa.Column("entidade_id", sa.Integer),
        sa.Column("payload_jsonb", postgresql.JSONB),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_log_criado", "audit_log", ["criado_em"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_criado", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_confrontante_lote", table_name="confrontante")
    op.drop_table("confrontante")

    op.drop_index("ix_lote_geometria_matricula", table_name="lote_geometria")
    op.drop_table("lote_geometria")

    op.drop_index("ix_matricula_status", table_name="matricula")
    op.drop_index("ix_matricula_numero", table_name="matricula")
    op.drop_table("matricula")

    op.drop_index("ix_usuario_email", table_name="usuario")
    op.drop_table("usuario")
