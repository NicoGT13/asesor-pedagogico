"""Shim de compatibilidad con el comando del SRS §9: `gunicorn main:app -k uvicorn.workers.UvicornWorker`."""
from app.main import app  # noqa: F401
