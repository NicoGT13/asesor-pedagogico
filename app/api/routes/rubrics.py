"""Módulo 3 – Gestión y parametrización de rúbricas (RF-203, RF-204)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, StaffUser, audit
from app.models.models import Evaluation, Laboratory, Rubric
from app.schemas.schemas import RubricBase, RubricCreate, RubricOut, RubricValidationOut
from app.services.rubric_validator import validate_rubric_criteria

router = APIRouter(prefix="/api/rubrics", tags=["Rúbricas"])


def _out(r: Rubric) -> RubricOut:
    return RubricOut(id=r.id, laboratory_id=r.laboratory_id, laboratory_title=r.laboratory.title if r.laboratory else None,
                     name=r.name, total_weight=r.total_weight, criteria=r.criteria_json, is_active=r.is_active, created_at=r.created_at)


def _validation_out(criteria: list[dict]) -> RubricValidationOut:
    v = validate_rubric_criteria(criteria)
    return RubricValidationOut(valid=v.valid, total_weight=float(v.total_weight), difference=float(v.difference), errors=v.errors)


def _assert_valid(criteria: list[dict]) -> float:
    v = validate_rubric_criteria(criteria)
    if not v.valid:
        # 422 con detalle estructurado: el frontend lo muestra tal cual.
        raise HTTPException(422, {"message": "Rúbrica inválida", "errors": v.errors, "total_weight": float(v.total_weight)})
    return float(v.total_weight)


async def _deactivate_others(db, lab_id: int, keep_id: int) -> None:
    await db.execute(update(Rubric).where(Rubric.laboratory_id == lab_id, Rubric.id != keep_id).values(is_active=False))


@router.post("/validate", response_model=RubricValidationOut, summary="Validación en seco (no persiste)")
async def validate(body: RubricBase, _: StaffUser):
    return _validation_out([c.model_dump() for c in body.criteria])


@router.get("", response_model=list[RubricOut])
async def list_rubrics(db: DB, _: CurrentUser, laboratory_id: int | None = None):
    stmt = select(Rubric).options(selectinload(Rubric.laboratory)).order_by(Rubric.laboratory_id, Rubric.created_at.desc())
    if laboratory_id:
        stmt = stmt.where(Rubric.laboratory_id == laboratory_id)
    return [_out(r) for r in (await db.execute(stmt)).scalars().all()]


@router.get("/{rid}", response_model=RubricOut)
async def get_rubric(rid: int, db: DB, _: CurrentUser):
    r = (await db.execute(select(Rubric).options(selectinload(Rubric.laboratory)).where(Rubric.id == rid))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Rúbrica no encontrada.")
    return _out(r)


@router.post("", response_model=RubricOut, status_code=201)
async def create_rubric(body: RubricCreate, db: DB, actor: StaffUser):
    if not await db.get(Laboratory, body.laboratory_id):
        raise HTTPException(404, "Laboratorio no encontrado.")
    criteria = [c.model_dump() for c in body.criteria]
    total = _assert_valid(criteria)  # RF-204: bloquea si ≠ 100 %
    r = Rubric(laboratory_id=body.laboratory_id, name=body.name, criteria_json=criteria, total_weight=total,
               is_active=body.activate, created_by=actor.id)
    db.add(r)
    await db.flush()
    if body.activate:
        await _deactivate_others(db, r.laboratory_id, r.id)
    audit(db, actor, "CREATE_RUBRIC", "rubric", r.id, {"total_weight": total})
    await db.commit()
    return await get_rubric(r.id, db, actor)


@router.put("/{rid}", response_model=RubricOut)
async def update_rubric(rid: int, body: RubricCreate, db: DB, actor: StaffUser):
    r = await db.get(Rubric, rid)
    if not r:
        raise HTTPException(404, "Rúbrica no encontrada.")
    used = (await db.execute(select(Evaluation.id).where(Evaluation.rubric_id == rid).limit(1))).first()
    if used:
        raise HTTPException(409, "La rúbrica ya fue usada en evaluaciones; cree una nueva versión para preservar la trazabilidad.")
    criteria = [c.model_dump() for c in body.criteria]
    r.total_weight = _assert_valid(criteria)
    r.name, r.criteria_json, r.laboratory_id, r.is_active = body.name, criteria, body.laboratory_id, body.activate
    if body.activate:
        await _deactivate_others(db, r.laboratory_id, r.id)
    audit(db, actor, "UPDATE_RUBRIC", "rubric", r.id)
    await db.commit()
    return await get_rubric(r.id, db, actor)


@router.post("/{rid}/activate", response_model=RubricOut)
async def activate_rubric(rid: int, db: DB, actor: StaffUser):
    r = await db.get(Rubric, rid)
    if not r:
        raise HTTPException(404, "Rúbrica no encontrada.")
    _assert_valid(r.criteria_json)  # re-verificación defensiva
    r.is_active = True
    await _deactivate_others(db, r.laboratory_id, r.id)
    audit(db, actor, "ACTIVATE_RUBRIC", "rubric", r.id)
    await db.commit()
    return await get_rubric(r.id, db, actor)
