FROM python:3.12-slim AS base

# Dependências nativas do WeasyPrint (Pango/Cairo) + libs PostGIS client
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir uv==0.5.0

COPY backend/pyproject.toml /app/
RUN uv pip install --system --no-cache .

COPY backend/src /app/src
COPY backend/alembic.ini /app/
COPY templates /app/templates
COPY scripts /app/scripts

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Em produção: aplica migrations e sobe uvicorn (single-worker;
# para escalar use --workers ou rode atrás de gunicorn)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir src"]
