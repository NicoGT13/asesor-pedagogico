"""Módulo 4 – Evaluación inteligente asistida por IA + supervisión docente (RF-205 a RF-208)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, StaffUser, audit, is_staff
from app.core.config import settings
from app.models.models import Evaluation, Laboratory, Rubric, Submission, SubmissionStatus
from app.schemas.ai import AIEvaluationOutput
from app.schemas.schemas import AIStatusOut, EvaluationAdjustRequest, EvaluationApproveRequest, EvaluationOut
from app.services.ai_engine import AIEngineError, EvaluationContext, run_ai_evaluation
from app.services.grading import GradingError, compute_final_score

router = APIRouter(prefix="/api", tags=["Evaluación IA"])


def _eval_query():
    return select(Evaluation).options(
        selectinload(Evaluation.submission).selectinload(Submission.student),
        selectinload(Evaluation.submission).selectinload(Submission.laboratory).selectinload(Laboratory.cohort),
        selectinload(Evaluation.rubric),
    )


def _out(ev: Evaluation) -> EvaluationOut:
    raw = ev.raw_llm_json or {}
    terms = " + ".join(f"{c['partial_score']}×{c['weight']:g}%" for c in ev.criteria_scores)
    return EvaluationOut(
        id=ev.id, submission_id=ev.submission_id, rubric_id=ev.rubric_id,
        student_name=ev.submission.student.full_name, laboratory_title=ev.submission.laboratory.title,
        cohort_name=ev.submission.laboratory.cohort.name,
        general_summary=raw.get("general_summary", ""), strengths=raw.get("strengths", []),
        weaknesses=raw.get("weaknesses", []), recommendations=raw.get("recommendations", []),
        criteria_scores=ev.criteria_scores, raw_score=ev.raw_score, calculated_score=ev.calculated_score,
        formula=f"Σ(puntaje × ponderación/100) = {terms} = {ev.raw_score:.4f} → {ev.calculated_score:.1f}",
        ai_provider=ev.ai_provider, teacher_approved=ev.teacher_approved, teacher_comment=ev.teacher_comment,
        adjusted=ev.adjusted, approved_at=ev.approved_at, created_at=ev.created_at,
    )


def _build_lines(criteria: list[dict], ai: AIEvaluationOutput) -> list[dict]:
    by_id = {e.criterion_id: e for e in ai.evaluations}
    return [
        {
            "criterion_id": c["id"], "name": c["name"], "competency": c.get("competency", ""), "weight": c["weight"],
            "partial_score": by_id[c["id"]].partial_score, "ai_partial_score": by_id[c["id"]].partial_score,
            "contribution": 0.0, "evidence_quote": by_id[c["id"]].evidence_quote, "reasoning": by_id[c["id"]].reasoning,
            "adjusted": False, "adjust_reason": "",
        }
        for c in criteria
    ]


def _apply_grade(ev: Evaluation, criteria: list[dict], lines: list[dict]) -> None:
    """Cálculo determinista en el backend: la única fuente de la nota oficial."""
    result = compute_final_score(criteria, {l["criterion_id"]: l["partial_score"] for l in lines})
    contrib = {g.criterion_id: float(g.contribution) for g in result.lines}
    for l in lines:
        l["contribution"] = contrib[l["criterion_id"]]
    ev.criteria_scores = lines
    ev.raw_score = float(result.raw_score)
    ev.calculated_score = float(result.final_score)


@router.get("/ai/status", response_model=AIStatusOut)
async def ai_status(_: CurrentUser):
    configured = settings.AI_PROVIDER.lower() == "openai" and bool(settings.OPENAI_API_KEY)
    return AIStatusOut(provider="openai" if configured else "mock-determinista",
                       model=settings.OPENAI_MODEL if configured else None, configured=configured,
                       fallback_to_mock=settings.AI_FALLBACK_TO_MOCK)


@router.post("/submissions/{sid}/evaluate", response_model=EvaluationOut, status_code=201, summary="Evaluar entrega con IA")
async def evaluate_submission(sid: int, db: DB, actor: StaffUser):
    sub = (await db.execute(
        select(Submission).options(selectinload(Submission.laboratory)).where(Submission.id == sid)
    )).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Entrega no encontrada.")
    rubric = (await db.execute(
        select(Rubric).where(Rubric.laboratory_id == sub.laboratory_id, Rubric.is_active.is_(True))
    )).scalar_one_or_none()
    if not rubric:
        raise HTTPException(409, "El laboratorio no tiene una rúbrica activa y válida (RF-204). Configure una antes de evaluar.")

    ctx = EvaluationContext(
        laboratory_title=sub.laboratory.title, laboratory_objectives=sub.laboratory.objectives,
        criteria=rubric.criteria_json, pdf_text=sub.pdf_text or "", code_excerpt=sub.code_excerpt or "",
        repo_url=sub.repo_url, code_manifest=sub.code_manifest or {},
    )
    try:
        ai_output, provider = await run_ai_evaluation(ctx)
    except AIEngineError as exc:
        raise HTTPException(502, f"Motor de IA: {exc}") from exc

    ev = Evaluation(submission_id=sub.id, rubric_id=rubric.id, raw_llm_json=ai_output.model_dump(), ai_provider=provider)
    try:
        _apply_grade(ev, rubric.criteria_json, _build_lines(rubric.criteria_json, ai_output))
    except GradingError as exc:
        raise HTTPException(422, str(exc)) from exc

    db.add(ev)
    sub.status = SubmissionStatus.EVALUADO_IA
    await db.flush()
    audit(db, actor, "AI_EVALUATE", "evaluation", ev.id, {"provider": provider, "score": ev.calculated_score})
    await db.commit()
    return _out((await db.execute(_eval_query().where(Evaluation.id == ev.id))).scalar_one())


@router.get("/evaluations", response_model=list[EvaluationOut])
async def list_evaluations(db: DB, user: CurrentUser, pending: bool | None = None):
    stmt = _eval_query().order_by(Evaluation.created_at.desc())
    if not is_staff(user):
        stmt = stmt.join(Submission).where(Submission.student_id == user.id, Evaluation.teacher_approved.is_(True))
    elif pending is not None:
        stmt = stmt.where(Evaluation.teacher_approved.is_(not pending))
    return [_out(e) for e in (await db.execute(stmt)).scalars().unique().all()]


async def _get(db, eid: int) -> Evaluation:
    ev = (await db.execute(_eval_query().where(Evaluation.id == eid))).scalar_one_or_none()
    if not ev:
        raise HTTPException(404, "Evaluación no encontrada.")
    return ev


@router.get("/evaluations/{eid}", response_model=EvaluationOut)
async def get_evaluation(eid: int, db: DB, user: CurrentUser):
    ev = await _get(db, eid)
    if not is_staff(user) and (ev.submission.student_id != user.id or not ev.teacher_approved):
        raise HTTPException(403, "Evaluación no disponible.")
    return _out(ev)


@router.patch("/evaluations/{eid}/adjust", response_model=EvaluationOut, summary="Ajuste docente de puntajes parciales (recalcula)")
async def adjust_evaluation(eid: int, body: EvaluationAdjustRequest, db: DB, actor: StaffUser):
    ev = await _get(db, eid)
    if ev.teacher_approved:
        raise HTTPException(409, "La evaluación ya fue publicada; no se puede modificar.")
    lines = [dict(l) for l in ev.criteria_scores]
    idx = {l["criterion_id"]: l for l in lines}
    for adj in body.adjustments:
        if adj.criterion_id not in idx:
            raise HTTPException(422, f"Criterio inexistente: {adj.criterion_id}")
        idx[adj.criterion_id].update(partial_score=adj.partial_score, adjusted=True, adjust_reason=adj.reason)
    before = ev.calculated_score
    try:
        _apply_grade(ev, ev.rubric.criteria_json, lines)  # el docente ajusta parciales; la nota la recalcula el backend
    except GradingError as exc:
        raise HTTPException(422, str(exc)) from exc
    ev.adjusted, ev.reviewed_by = True, actor.id
    audit(db, actor, "ADJUST_EVALUATION", "evaluation", ev.id,
          {"before": before, "after": ev.calculated_score, "adjustments": [a.model_dump() for a in body.adjustments]})
    await db.commit()
    return _out(await _get(db, eid))


@router.post("/evaluations/{eid}/approve", response_model=EvaluationOut, summary="Aprobar y publicar la nota")
async def approve_evaluation(eid: int, body: EvaluationApproveRequest, db: DB, actor: StaffUser):
    ev = await _get(db, eid)
    if ev.teacher_approved:
        raise HTTPException(409, "La evaluación ya está publicada.")
    ev.teacher_approved, ev.teacher_comment = True, body.teacher_comment.strip()
    ev.reviewed_by, ev.approved_at = actor.id, datetime.now(timezone.utc)
    ev.submission.status = SubmissionStatus.PUBLICADO
    audit(db, actor, "APPROVE_EVALUATION", "evaluation", ev.id, {"score": ev.calculated_score})
    await db.commit()
    return _out(await _get(db, eid))
