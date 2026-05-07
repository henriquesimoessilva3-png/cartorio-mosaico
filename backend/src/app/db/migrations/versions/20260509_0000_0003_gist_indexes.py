"""GIST index em lote_geometria.geometry para acelerar inferência e topologia

Revision ID: 0003_gist_indexes
Revises: 0002_multitenant
Create Date: 2026-05-09

Sem este índice, ST_DWithin / ST_Intersects fazem seq scan. Com ele,
queries de vizinhança em PostGIS escalam para dezenas de milhares de lotes.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003_gist_indexes"
down_revision: Union[str, None] = "0002_multitenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lote_geometria_geometry_gist "
        "ON lote_geometria USING gist (geometry)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_lote_geometria_geometry_gist")
