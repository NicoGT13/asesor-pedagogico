"""Módulo 2 – Entrada de información y Portafolio Académico (RF-201, RF-202)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, AdminUser, CurrentUser, StaffUser, audit, is_staff
from app.models.models import Cohort, Laboratory, Rubric, Role, Submission, User
from app.schemas.schemas import CohortCreate, CohortOut, LaboratoryCreate, LaboratoryOut, SubmissionOut
from app.services import files

router = APIRouter(prefix="/api", tags=["Portafolio Académico"])


async def _active_rubric_lab_ids(db) -> set[int]:
    return set((await db.execute(select(Rubric.laboratory_id).where(Rubric.is_active.is_(True)))).scalars().all())


@router.get("/cohorts", response_model=list[CohortOut])
async def list_cohorts(db: DB, _: CurrentUser):
    cohorts = (await db.execute(select(Cohort).options(selectinload(Cohort.laboratories)).order_by(Cohort.order))).scalars().unique().all()
    active = await _active_rubric_lab_ids(db)
    out = []
    for c in cohorts:
        co = CohortOut.model_validate(c)
        for lab in co.laboratories:
            lab.has_active_rubric = lab.id in active
        out.append(co)
    return out


@router.post("/cohorts", response_model=CohortOut, status_code=201)
async def create_cohort(body: CohortCreate, db: DB, actor: AdminUser):
    co = Cohort(**body.model_dump())
    db.add(co)
    await db.flush()
    audit(db, actor, "CREATE_COHORT", "cohort", co.id)
    await db.commit()
    return CohortOut(id=co.id, name=co.name, description=co.description, order=co.order, laboratories=[])


@router.post("/laboratories", response_model=LaboratoryOut, status_code=201)
async def create_laboratory(body: LaboratoryCreate, db: DB, actor: StaffUser):
    if not await db.get(Cohort, body.cohort_id):
        raise HTTPException(404, "Cohorte no encontrada.")
    lab = Laboratory(**body.model_dump())
    db.add(lab)
    await db.flush()
    audit(db, actor, "CREATE_LAB", "laboratory", lab.id)
    await db.commit()
    return lab


def _submission_out(s: Submission) -> SubmissionOut:
    latest = s.evaluations[-1] if s.evaluations else None
    return SubmissionOut(
        id=s.id, student_id=s.student_id, student_name=s.student.full_name,
        laboratory_id=s.laboratory_id, laboratory_title=s.laboratory.title,
        cohort_id=s.laboratory.cohort.id, cohort_name=s.laboratory.cohort.name,
        pdf_original_name=s.pdf_original_name, has_pdf=bool(s.pdf_url), pdf_text_chars=len(s.pdf_text or ""),
        repo_url=s.repo_url, has_code_zip=bool(s.code_zip_url), code_manifest=s.code_manifest or {},
        notes=s.notes, status=s.status, submitted_at=s.submitted_at,
        latest_evaluation_id=latest.id if latest else None,
        latest_score=latest.calculated_score if latest else None,
    )


def _submission_query():
    return select(Submission).options(
        selectinload(Submission.student),
        selectinload(Submission.laboratory).selectinload(Laboratory.cohort),
        selectinload(Submission.evaluations),
    )


@router.get("/submissions", response_model=list[SubmissionOut])
async def list_submissions(db: DB, user: CurrentUser, cohort_id: int | None = None, laboratory_id: int | None = None,
                           student_id: uuid.UUID | None = None):
    stmt = _submission_query().join(Laboratory).order_by(Submission.submitted_at.desc())
    if not is_staff(user):
        stmt = stmt.where(Submission.student_id == user.id)
    elif student_id:
        stmt = stmt.where(Submission.student_id == student_id)
    if cohort_id:
        stmt = stmt.where(Laboratory.cohort_id == cohort_id)
    if laboratory_id:
        stmt = stmt.where(Submission.laboratory_id == laboratory_id)
    subs = (await db.execute(stmt)).scalars().unique().all()
    result = []
    for s in subs:
        out = _submission_out(s)
        if not is_staff(user):  # el estudiante sólo ve notas aprobadas
            approved = [e for e in s.evaluations if e.teacher_approved]
            out.latest_evaluation_id = approved[-1].id if approved else None
            out.latest_score = approved[-1].calculated_score if approved else None
        result.append(out)
    return result


@router.post("/submissions", response_model=SubmissionOut, status_code=201, summary="Cargar entrega (PDF + ZIP/GitHub)")
async def create_submission(
    db: DB,
    user: CurrentUser,
    laboratory_id: int = Form(...),
    repo_url: str | None = Form(None),
    notes: str = Form(""),
    student_id: uuid.UUID | None = Form(None, description="Sólo docentes: cargar a nombre de un estudiante"),
    pdf: UploadFile | None = File(None),
    code_zip: UploadFile | None = File(None),
):
    lab = await db.get(Laboratory, laboratory_id)
    if not lab:
        raise HTTPException(404, "Laboratorio no encontrado.")

    owner_id = user.id
    if is_staff(user):
        if not student_id:
            raise HTTPException(422, "Indique el estudiante (student_id) al cargar como docente.")
        st = await db.get(User, student_id)
        if not st or st.role != Role.ESTUDIANTE:
            raise HTTPException(404, "Estudiante no encontrado.")
        owner_id = st.id
    elif student_id and student_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede cargar entregas de otro estudiante.")

    has_pdf = pdf is not None and pdf.filename
    has_zip = code_zip is not None and code_zip.filename
    repo = files.validate_repo_url(repo_url)
    if not (has_pdf or has_zip or repo):
        raise HTTPException(422, "Debe adjuntar al menos un PDF, un ZIP de código o un repositorio GitHub.")

    sub = Submission(student_id=owner_id, laboratory_id=lab.id, repo_url=repo, notes=notes.strip()[:4000])
    if has_pdf:
        data = await files.read_limited(pdf)
        sub.pdf_text = files.extract_pdf_text(data)
        sub.pdf_url = files.save_bytes(data, ".pdf", "pdf")
        sub.pdf_original_name = pdf.filename[:255]
    if has_zip:
        data = await files.read_limited(code_zip)
        sub.code_manifest, sub.code_excerpt = files.analyze_code_zip(data)
        sub.code_zip_url = files.save_bytes(data, ".zip", "code")

    db.add(sub)
    await db.flush()
    audit(db, user, "CREATE_SUBMISSION", "submission", sub.id, {"laboratory_id": lab.id})
    await db.commit()
    s = (await db.execute(_submission_query().where(Submission.id == sub.id))).scalar_one()
    return _submission_out(s)


async def _get_owned_submission(db, sid: int, user) -> Submission:
    s = (await db.execute(_submission_query().where(Submission.id == sid))).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Entrega no encontrada.")
    if not is_staff(user) and s.student_id != user.id:
        raise HTTPException(403, "No tiene acceso a esta entrega.")
    return s


@router.get("/submissions/{sid}", response_model=SubmissionOut)
async def get_submission(sid: int, db: DB, user: CurrentUser):
    return _submission_out(await _get_owned_submission(db, sid, user))


@router.get("/submissions/{sid}/pdf", summary="Descargar el PDF de la entrega")
async def download_pdf(sid: int, db: DB, user: CurrentUser):
    s = await _get_owned_submission(db, sid, user)
    if not s.pdf_url:
        raise HTTPException(404, "La entrega no tiene PDF.")
    path = files.resolve_stored(s.pdf_url)
    if not path.exists():
        raise HTTPException(410, "El archivo ya no está disponible en disco (filesystem efímero). El texto extraído se conserva en BD.")
    return FileResponse(path, media_type="application/pdf", filename=s.pdf_original_name or f"entrega_{sid}.pdf")


@router.delete("/submissions/{sid}", status_code=204)
async def delete_submission(sid: int, db: DB, user: CurrentUser):
    s = await _get_owned_submission(db, sid, user)
    if not is_staff(user) and any(e.teacher_approved for e in s.evaluations):
        raise HTTPException(409, "No puede eliminar una entrega con calificación publicada.")
    audit(db, user, "DELETE_SUBMISSION", "submission", s.id)
    await db.delete(s)
    await db.commit()
