"""Drop redundant manual GIST em lote_geometria.geometry

Revision ID: 0007_drop_redundant_gist
Revises: 0006_audit_backfill
Create Date: 2026-05-13

GeoAlchemy2 cria automaticamente `idx_lote_geometria_geometry` (também GIST)
ao declarar a coluna `Geometry(...)`. A migration 0003 criou um segundo índice
`ix_lote_geometria_geometry_gist` que é funcionalmente idêntico. Mantém só
o auto-criado para reduzir overhead de escrita e tamanho em disco.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007_drop_redundant_gist"
down_revision: Union[str, None] = "0006_audit_backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_lote_geometria_geometry_gist")


def downgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lote_geometria_geometry_gist "
        "ON lote_geometria USING gist (geometry)"
    )
