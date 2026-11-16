"""RF-209 a RF-212: Informe Integrado del Aprendizaje, panorama de cohortes y Mapa Mental."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Cohort, Evaluation, Laboratory, Role, Submission, User
from app.services.grading import performance_level

GAP_THRESHOLD = 3.5
PASS_THRESHOLD = 3.0


def _r(x: float | None, nd: int = 2) -> float | None:
    return None if x is None else round(x, nd)


async def _cohorts(db: AsyncSession) -> list[Cohort]:
    res = await db.execute(select(Cohort).options(selectinload(Cohort.laboratories)).order_by(Cohort.order, Cohort.id))
    return list(res.scalars().unique())


async def collect_records(db: AsyncSession, student_id: uuid.UUID | None = None, only_approved: bool = True) -> list[dict]:
    """Última evaluación por (estudiante, laboratorio). Fuente única para informes y mapa."""
    stmt = (
        select(Evaluation)
        .join(Submission, Evaluation.submission_id == Submission.id)
        .options(
            selectinload(Evaluation.submission).selectinload(Submission.laboratory).selectinload(Laboratory.cohort),
            selectinload(Evaluation.submission).selectinload(Submission.student),
        )
        .order_by(Evaluation.created_at)
    )
    if student_id:
        stmt = stmt.where(Submission.student_id == student_id)
    if only_approved:
        stmt = stmt.where(Evaluation.teacher_approved.is_(True))
    evaluations = (await db.execute(stmt)).scalars().unique().all()

    latest: dict[tuple, Evaluation] = {}
    for ev in evaluations:
        key = (ev.submission.student_id, ev.submission.laboratory_id)
        latest[key] = ev  # orden ascendente ⇒ queda la más reciente

    records = []
    for ev in latest.values():
        lab = ev.submission.laboratory
        raw = ev.raw_llm_json or {}
        records.append(
            {
                "evaluation_id": ev.id,
                "student_id": str(ev.submission.student_id),
                "student_name": ev.submission.student.full_name,
                "lab_id": lab.id,
                "lab_title": lab.title,
                "lab_order": lab.order,
                "cohort_id": lab.cohort.id,
                "cohort_name": lab.cohort.name,
                "cohort_order": lab.cohort.order,
                "competencies": lab.competencies or [],
                "score": ev.calculated_score,
                "approved": ev.teacher_approved,
                "criteria": ev.criteria_scores or [],
                "strengths": raw.get("strengths", []),
                "weaknesses": raw.get("weaknesses", []),
                "recommendations": raw.get("recommendations", []),
                "date": (ev.approved_at or ev.created_at).isoformat(),
            }
        )
    records.sort(key=lambda r: (r["cohort_order"], r["lab_order"]))
    return records


def _competency_stats(records: list[dict]) -> dict[str, dict]:
    acc: dict[str, dict] = defaultdict(lambda: {"scores": [], "labs": set(), "evidences": [], "recommendations": []})
    for r in records:
        for c in r["criteria"]:
            comp = c.get("competency") or "General"
            acc[comp]["scores"].append(c["partial_score"])
            acc[comp]["labs"].add(r["lab_title"])
            if c.get("evidence_quote") and "Sin evidencia" not in c["evidence_quote"]:
                acc[comp]["evidences"].append({"lab": r["lab_title"], "criterion": c["name"], "quote": c["evidence_quote"]})
        for rec in r["recommendations"]:
            for comp in r["competencies"]:
                acc[comp]["recommendations"].append(rec)
    return acc


_PLAN_TEMPLATES = {
    "Inicial": [
        "Repasar fundamentos teóricos con material guiado y ejercicios cortos semanales.",
        "Agendar asesoría docente para resolver dudas conceptuales antes del siguiente laboratorio.",
        "Rehacer el laboratorio asociado documentando cada paso y su justificación.",
    ],
    "En desarrollo": [
        "Profundizar con un mini-proyecto aplicado y comparar al menos dos enfoques/modelos.",
        "Incorporar métricas de evaluación y análisis de error en los informes.",
    ],
    "Competente": ["Extender el trabajo con experimentación avanzada o un dataset más complejo."],
}


async def student_report(db: AsyncSession, student: User, include_pending: bool = False) -> dict:
    records = await collect_records(db, student.id, only_approved=not include_pending)
    cohorts = await _cohorts(db)
    by_lab = {r["lab_id"]: r for r in records}

    cohort_blocks, pending = [], []
    for co in cohorts:
        labs = []
        for lab in co.laboratories:
            r = by_lab.get(lab.id)
            if r is None:
                pending.append({"lab_id": lab.id, "title": lab.title, "cohort": co.name})
            labs.append(
                {
                    "lab_id": lab.id,
                    "title": lab.title,
                    "score": r["score"] if r else None,
                    "level": performance_level(r["score"]) if r else "Sin evidencia",
                    "evaluation_id": r["evaluation_id"] if r else None,
                    "approved": r["approved"] if r else None,
                }
            )
        scores = [l["score"] for l in labs if l["score"] is not None]
        cohort_blocks.append({"id": co.id, "name": co.name, "average": _r(mean(scores)) if scores else None, "labs": labs})

    all_scores = [r["score"] for r in records]
    comp = _competency_stats(records)
    competencies = sorted(
        (
            {
                "name": name,
                "average": _r(mean(d["scores"])),
                "level": performance_level(mean(d["scores"])),
                "samples": len(d["scores"]),
                "labs": sorted(d["labs"]),
            }
            for name, d in comp.items()
            if d["scores"]
        ),
        key=lambda x: x["average"],
    )
    gaps = [c for c in competencies if c["average"] < GAP_THRESHOLD]

    plan = []
    for i, g in enumerate(gaps):
        specific = list(dict.fromkeys(comp[g["name"]]["recommendations"]))[:3]
        plan.append(
            {
                "competency": g["name"],
                "priority": "Alta" if g["average"] < PASS_THRESHOLD else "Media",
                "current_level": g["level"],
                "target": "Competente (≥ 4.0)",
                "actions": specific + _PLAN_TEMPLATES.get(g["level"], _PLAN_TEMPLATES["En desarrollo"]),
                "order": i + 1,
            }
        )
    if not plan and competencies:
        plan.append(
            {
                "competency": "Consolidación avanzada",
                "priority": "Baja",
                "current_level": performance_level(mean(all_scores)),
                "target": "Sobresaliente (≥ 4.6)",
                "actions": _PLAN_TEMPLATES["Competente"] + ["Postular el trabajo a un semillero o evento de investigación formativa."],
                "order": 1,
            }
        )

    c_avgs = [c["average"] for c in cohort_blocks if c["average"] is not None]
    trend = _r(c_avgs[-1] - c_avgs[0]) if len(c_avgs) >= 2 else None

    strengths = list(dict.fromkeys(s for r in records for s in r["strengths"]))[:8]
    return {
        "student": {"id": str(student.id), "full_name": student.full_name, "email": student.email, "student_code": student.student_code},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "includes_pending": include_pending,
        "overall_average": _r(mean(all_scores)) if all_scores else None,
        "overall_level": performance_level(mean(all_scores)) if all_scores else "Sin evidencia",
        "evaluated_labs": len(records),
        "total_labs": sum(len(c.laboratories) for c in cohorts),
        "trend_between_cohorts": trend,
        "cohorts": cohort_blocks,
        "evolution": [{"label": r["lab_title"], "cohort": r["cohort_name"], "score": r["score"]} for r in records],
        "competencies": competencies,
        "gaps": gaps,
        "plan": plan,
        "strengths": strengths,
        "pending_labs": pending,
    }


async def cohorts_overview(db: AsyncSession) -> dict:
    cohorts = await _cohorts(db)
    records = await collect_records(db, None, only_approved=True)
    subs = (await db.execute(select(Submission).options(selectinload(Submission.laboratory)))).scalars().all()
    students = (await db.execute(select(User).where(User.role == Role.ESTUDIANTE))).scalars().all()

    out = []
    for co in cohorts:
        lab_ids = {l.id for l in co.laboratories}
        recs = [r for r in records if r["cohort_id"] == co.id]
        scores = [r["score"] for r in recs]
        co_subs = [s for s in subs if s.laboratory_id in lab_ids]
        buckets = [0, 0, 0, 0, 0]
        for s in scores:
            buckets[min(4, int(s))] += 1
        labs = []
        for lab in co.laboratories:
            ls = [r["score"] for r in recs if r["lab_id"] == lab.id]
            labs.append({"lab_id": lab.id, "title": lab.title, "average": _r(mean(ls)) if ls else None, "published": len(ls),
                         "submissions": sum(1 for s in co_subs if s.laboratory_id == lab.id)})
        out.append(
            {
                "id": co.id,
                "name": co.name,
                "submissions": len(co_subs),
                "published": len(recs),
                "average": _r(mean(scores)) if scores else None,
                "pass_rate": _r(100 * sum(1 for s in scores if s >= PASS_THRESHOLD) / len(scores), 1) if scores else None,
                "distribution": {"labels": ["0–1", "1–2", "2–3", "3–4", "4–5"], "values": buckets},
                "labs": labs,
            }
        )

    comp = _competency_stats(records)
    ranking = defaultdict(list)
    for r in records:
        ranking[(r["student_id"], r["student_name"])].append(r["score"])
    return {
        "students": len(students),
        "cohorts": out,
        "competencies": sorted(
            ({"name": k, "average": _r(mean(v["scores"])), "level": performance_level(mean(v["scores"]))} for k, v in comp.items() if v["scores"]),
            key=lambda x: x["average"],
        ),
        "students_summary": sorted(
            ({"student_id": sid, "full_name": name, "average": _r(mean(v)), "labs": len(v)} for (sid, name), v in ranking.items()),
            key=lambda x: -x["average"],
        ),
    }


async def competency_mindmap(db: AsyncSession, student_id: uuid.UUID | None) -> dict:
    """Árbol: Competencias IA → Cohorte → Competencia → Laboratorio (RF-211/RF-212)."""
    cohorts = await _cohorts(db)
    records = await collect_records(db, student_id, only_approved=True)

    root = {"id": "root", "name": "Competencias en IA", "type": "root", "children": []}
    for co in cohorts:
        co_recs = [r for r in records if r["cohort_id"] == co.id]
        stats = _competency_stats(co_recs)
        comp_names = list(dict.fromkeys(c for lab in co.laboratories for c in (lab.competencies or [])))
        co_scores = [r["score"] for r in co_recs]
        co_node = {
            "id": f"c{co.id}", "name": co.name, "type": "cohort", "description": co.description,
            "mastery": _r(mean(co_scores)) if co_scores else None,
            "level": performance_level(mean(co_scores)) if co_scores else "Sin evidencia",
            "children": [],
        }
        for comp in comp_names:
            d = stats.get(comp)
            m = mean(d["scores"]) if d and d["scores"] else None
            comp_node = {
                "id": f"c{co.id}-{comp}", "name": comp, "type": "competency",
                "mastery": _r(m), "level": performance_level(m),
                "evidences": (d["evidences"][:6] if d else []),
                "deepening": list(dict.fromkeys(d["recommendations"]))[:4] if d and (m or 0) < 4.6 else [],
                "children": [],
            }
            for lab in co.laboratories:
                if comp not in (lab.competencies or []):
                    continue
                lab_recs = [r for r in co_recs if r["lab_id"] == lab.id]
                crit = [c for r in lab_recs for c in r["criteria"] if c.get("competency") == comp]
                lm = mean([c["partial_score"] for c in crit]) if crit else None
                comp_node["children"].append(
                    {
                        "id": f"l{lab.id}-{comp}", "name": lab.title, "type": "laboratory", "lab_id": lab.id,
                        "objectives": lab.objectives,
                        "mastery": _r(lm), "level": performance_level(lm),
                        "score": _r(mean([r["score"] for r in lab_recs])) if lab_recs else None,
                        "evidences": [{"criterion": c["name"], "quote": c.get("evidence_quote", "")} for c in crit][:4],
                        "deepening": list(dict.fromkeys(x for r in lab_recs for x in r["recommendations"]))[:3],
                    }
                )
            co_node["children"].append(comp_node)
        root["children"].append(co_node)
    all_scores = [r["score"] for r in records]
    root["mastery"] = _r(mean(all_scores)) if all_scores else None
    root["level"] = performance_level(mean(all_scores)) if all_scores else "Sin evidencia"
    root["scope"] = "student" if student_id else "global"
    return root
