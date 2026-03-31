# ── GeoPipeAgent Backend ─────────────────────────────────────────────────────
# Multi-stage build: deps → application (smaller final image)
# ---------------------------------------------------------------------------

# Stage 1: Install dependencies in a builder stage
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.4 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip python3-venv \
        build-essential \
        libgeos-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python dependencies first (better caching)
COPY pyproject.toml ./
COPY src/ ./src/
COPY web/backend/requirements.txt ./web/backend/requirements.txt

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -e ".[analysis,network,web]" \
    && /opt/venv/bin/pip install --no-cache-dir -r web/backend/requirements.txt \
    && /opt/venv/bin/pip install --no-cache-dir redis rq

# Stage 2: Slim runtime image
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.4

# Only install runtime dependencies (no build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-venv \
        libgeos3.12.0 \
        libproj25 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/src /app/src
COPY --from=builder /build/pyproject.toml /app/

# Re-install in editable mode using the existing venv
RUN /opt/venv/bin/pip install --no-cache-dir -e ".[analysis,network,web]" 2>/dev/null || true

# Copy application code
COPY web/ ./web/
COPY cookbook/ ./cookbook/
COPY data/ ./data/ 2>/dev/null || true

# Ensure data directories exist
RUN mkdir -p data/conversations data/pipelines data/external_skills

# Add venv to PATH
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
