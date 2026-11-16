#!/usr/bin/env sh
# Arranque de producción (Render / Docker).
# 1) prestart en UN solo proceso: crea tablas + seed (evita condiciones de carrera entre workers)
# 2) Gunicorn como gestor de procesos con workers Uvicorn (ASGI)
set -e
python -m app.seed
exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WEB_CONCURRENCY:-2}" \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --forwarded-allow-ips="*" \
  --access-logfile - \
  --error-logfile -
