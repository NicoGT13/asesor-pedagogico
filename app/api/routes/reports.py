"""Módulos 5, 6 y 7 – Informe integrado, mapa mental y presentación institucional."""
from __future__ import annotations

import json
import unicodedata
import uuid
from urllib.parse import quote
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, StaffUser, is_staff
from app.models.models import AuditLog, Role, User
from app.services.analytics import cohorts_overview, competency_mindmap, student_report
from app.services.pdf_report import render_report_pdf

router = APIRouter(prefix="/api", tags=["Informes y Mapa Mental"])
project_router = APIRouter(prefix="/api/project", tags=["Proyecto y Equipo"])

PROJECT_FILE = Path(__file__).resolve().parents[2] / "data" / "project.json"


async def _resolve_student(db, user: User, student_id: uuid.UUID | None) -> User:
    if student_id is None or student_id == user.id:
        if user.role != Role.ESTUDIANTE:
            raise HTTPException(422, "Indique student_id para consultar el informe de un estudiante.")
        return user
    if not is_staff(user):
        raise HTTPException(403, "Sólo puede consultar su propio informe.")
    st = await db.get(User, student_id)
    if not st or st.role != Role.ESTUDIANTE:
        raise HTTPException(404, "Estudiante no encontrado.")
    return st


@router.get("/reports/student", summary="Informe Integrado del Aprendizaje (JSON)")
async def report_json(db: DB, user: CurrentUser, student_id: uuid.UUID | None = None, include_pending: bool = False):
    st = await _resolve_student(db, user, student_id)
    return await student_report(db, st, include_pending=include_pending and is_staff(user))


@router.get("/reports/student/pdf", summary="Informe Integrado del Aprendizaje (PDF descargable)")
async def report_pdf(db: DB, user: CurrentUser, student_id: uuid.UUID | None = None, include_pending: bool = False):
    st = await _resolve_student(db, user, student_id)
    data = render_report_pdf(await student_report(db, st, include_pending=include_pending and is_staff(user)))
    fname = f"informe_integrado_{st.full_name.replace(' ', '_')}.pdf"
    ascii_name = unicodedata.normalize("NFKD", fname).encode("ascii", "ignore").decode().replace('"', "")
    # RFC 6266/5987: nombre ASCII de respaldo + nombre UTF-8 codificado (los headers HTTP son latin-1)
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(fname)}"
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": disposition})


@router.get("/reports/overview", summary="Panorama analítico de Cohorte 1 y Cohorte 2")
async def overview(db: DB, _: StaffUser):
    return await cohorts_overview(db)


@router.get("/mindmap", summary="Mapa mental interactivo de competencias en IA")
async def mindmap(db: DB, user: CurrentUser, student_id: uuid.UUID | None = None):
    if not is_staff(user):
        student_id = user.id
    return await competency_mindmap(db, student_id)


@router.get("/audit", summary="Bitácora de trazabilidad (docente/admin)")
async def audit_log(db: DB, _: StaffUser, limit: int = 100):
    rows = (await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500)))).scalars().all()
    return [{"id": r.id, "user_id": str(r.user_id) if r.user_id else None, "action": r.action, "entity": r.entity,
             "entity_id": r.entity_id, "detail": r.detail, "created_at": r.created_at.isoformat()} for r in rows]


@project_router.get("", summary="Abstract institucional y equipo desarrollador (público)")
async def project_info():
    return json.loads(PROJECT_FILE.read_text(encoding="utf-8"))
