"""Punto de entrada ASGI — Asesor Pedagógico Inteligente.

Local:       uvicorn app.main:app --reload
Producción:  gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:$PORT
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.routes import auth, evaluations, portfolio, reports, rubrics
from app.core.config import settings
from app.core.database import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("asesor")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.is_production and settings.SECRET_KEY.startswith("dev-insecure"):
        log.warning("⚠️  SECRET_KEY por defecto en producción. Configure una clave segura en Render.")
    if settings.INIT_DB_ON_STARTUP:  # en Docker se hace en prestart (evita carreras entre workers)
        from app.seed import init_db

        await init_db()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST del Asesor Pedagógico Inteligente — Universidad de Manizales (Profundización I · IA).",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def timing_and_security_headers(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"  # RNF-101
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"  # RNF-102
    return response


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Error no controlado: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor."})


for r in (auth.router, auth.users_router, portfolio.router, rubrics.router, evaluations.router, reports.router, reports.project_router):
    app.include_router(r)


@app.get("/api/health", tags=["Sistema"])
async def health():
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT, "ai_provider": settings.AI_PROVIDER,
            "demo_accounts": settings.SEED_DEMO_DATA}


# ------------------------------------------------------------------ Frontend (SPA)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado."})
    return FileResponse(FRONTEND_DIR / "index.html")
