# ── GeoPipeAgent Backend ─────────────────────────────────────────────────────
# Multi-stage build: GDAL base → Python deps → application
# ---------------------------------------------------------------------------

FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.4 AS base

# System dependencies for GeoPandas / Fiona / Rasterio / Shapely
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip python3-venv \
        build-essential \
        libgeos-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install Python dependencies ──────────────────────────────────────────────

COPY pyproject.toml ./
COPY src/ ./src/
COPY web/backend/requirements.txt ./web/backend/requirements.txt

# Install the core library and web backend dependencies
RUN pip install --no-cache-dir -e ".[analysis,network,web]" \
    && pip install --no-cache-dir -r web/backend/requirements.txt \
    && pip install --no-cache-dir redis rq

# ── Copy application code ────────────────────────────────────────────────────

COPY web/ ./web/
COPY cookbook/ ./cookbook/
COPY data/ ./data/ 2>/dev/null || true

# Ensure data directories exist
RUN mkdir -p data/conversations data/pipelines data/external_skills

EXPOSE 8000

# ── Default entrypoint ───────────────────────────────────────────────────────

CMD ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
