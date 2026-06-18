# ============================================================
# Stage 1 — Build Next.js static export
# ============================================================
FROM node:22-slim AS frontend-builder

WORKDIR /build/frontend

# Copy package manifests first for layer caching
COPY frontend/package*.json ./

RUN npm ci --prefer-offline

# Copy rest of frontend source
COPY frontend/ ./

# Produce static export into frontend/out/
RUN npm run build


# ============================================================
# Stage 2 — Python runtime
# ============================================================
FROM python:3.12-slim AS runtime

# Install uv (fast Python package manager)
RUN pip install --no-cache-dir uv==0.5.29

WORKDIR /app

# Copy backend project files
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./

# Sync production dependencies only (no dev extras)
# --frozen ensures we use the locked versions exactly
RUN uv sync --frozen --no-dev

# Copy backend application source
COPY backend/app ./app

# Copy the Next.js static export into backend/static so FastAPI can serve it
COPY --from=frontend-builder /build/frontend/out ./static

# Create the db directory (runtime volume mount point)
RUN mkdir -p /app/db

# Environment defaults — override via --env-file or -e at runtime
ENV DATABASE_PATH=/app/db/finally.db \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Run uvicorn from /app (backend dir) so relative imports resolve correctly
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
