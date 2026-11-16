# =============================================================================
# Asesor Pedagógico Inteligente — imagen de producción (multi-stage)
# =============================================================================

# ---------- Etapa 1: construir wheels (aísla compiladores de la imagen final)
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---------- Etapa 2: runtime mínimo, usuario sin privilegios
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production \
    INIT_DB_ON_STARTUP=false \
    UPLOAD_DIR=/app/uploads \
    PORT=8000

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* && rm -rf /wheels \
    && groupadd --system app && useradd --system --gid app --home /app app

COPY --chown=app:app app ./app
COPY --chown=app:app frontend ./frontend
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app main.py ./
RUN mkdir -p /app/uploads && chown -R app:app /app/uploads && chmod +x scripts/start.sh

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health', timeout=4)" || exit 1

CMD ["./scripts/start.sh"]
