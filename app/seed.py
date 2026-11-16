"""Inicialización de BD y datos de demostración (idempotente).

Uso:  python -m app.seed            (crea tablas + datos demo si la BD está vacía)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from app.core.config import settings
from app.core.database import SessionLocal, create_all_tables, engine
from app.core.security import hash_password
from app.models.models import Cohort, Evaluation, Laboratory, Role, Rubric, Submission, SubmissionStatus, User
from app.services.ai_engine import EvaluationContext, MockAIProvider, ensure_matches_rubric
from app.services.grading import compute_final_score

log = logging.getLogger("asesor.seed")

SE = "Ingeniería de software para IA"

LEVELS = [
    {"label": "Inicial", "min_score": 0.0, "max_score": 2.9, "descriptor": "Evidencia ausente o con errores conceptuales."},
    {"label": "En desarrollo", "min_score": 3.0, "max_score": 3.9, "descriptor": "Cumple parcialmente; falta justificación."},
    {"label": "Competente", "min_score": 4.0, "max_score": 4.5, "descriptor": "Cumple con solidez técnica."},
    {"label": "Sobresaliente", "min_score": 4.6, "max_score": 5.0, "descriptor": "Supera lo esperado con análisis crítico."},
]

COHORTS = [
    {
        "name": "Cohorte 1", "order": 1,
        "description": "Fundamentos de Aprendizaje Automático: datos, modelos supervisados y evaluación.",
        "labs": [
            {
                "title": "Lab 1 · Preprocesamiento y regresión lineal", "order": 1,
                "objectives": "Limpiar, transformar y explorar un dataset real; entrenar y analizar un modelo de regresión.",
                "competencies": ["Preprocesamiento de datos", "Aprendizaje supervisado", SE],
                "criteria": [
                    ("C1", "Limpieza y transformación de datos", "Preprocesamiento de datos", "Tratamiento de valores faltantes, outliers, normalización y codificación de variables categóricas.", 30),
                    ("C2", "Análisis exploratorio", "Preprocesamiento de datos", "Visualizaciones, correlaciones y estadística descriptiva que justifican decisiones.", 20),
                    ("C3", "Modelo de regresión", "Aprendizaje supervisado", "Entrenamiento de regresión lineal, interpretación de coeficientes y residuales.", 30),
                    ("C4", "Calidad del código y reproducibilidad", SE, "Código modular, semillas fijas, requirements y notebook ejecutable de principio a fin.", 20),
                ],
            },
            {
                "title": "Lab 2 · Clasificación y métricas de evaluación", "order": 2,
                "objectives": "Comparar clasificadores y seleccionar el mejor con validación cruzada y métricas adecuadas.",
                "competencies": ["Aprendizaje supervisado", "Evaluación de modelos", SE],
                "criteria": [
                    ("C1", "Comparación de clasificadores", "Aprendizaje supervisado", "Entrenamiento de regresión logística, árboles de decisión y random forest con ajuste de hiperparámetros.", 35),
                    ("C2", "Métricas y validación cruzada", "Evaluación de modelos", "Matriz de confusión, precisión, recall, F1, curva ROC y validación cruzada estratificada.", 35),
                    ("C3", "Análisis de resultados", "Evaluación de modelos", "Discusión de sobreajuste, desbalance de clases e interpretación de errores.", 15),
                    ("C4", "Calidad del código y reproducibilidad", SE, "Pipeline reproducible, funciones documentadas y pruebas básicas.", 15),
                ],
            },
        ],
    },
    {
        "name": "Cohorte 2", "order": 2,
        "description": "Aprendizaje Profundo e IA Generativa: redes neuronales, LLMs y uso responsable.",
        "labs": [
            {
                "title": "Lab 3 · Redes neuronales con PyTorch", "order": 3,
                "objectives": "Diseñar, entrenar y evaluar una red neuronal para clasificación de imágenes.",
                "competencies": ["Redes neuronales", "Evaluación de modelos", SE],
                "criteria": [
                    ("C1", "Arquitectura de la red", "Redes neuronales", "Diseño de capas convolucionales, funciones de activación y regularización con dropout.", 30),
                    ("C2", "Entrenamiento y optimización", "Redes neuronales", "Uso de optimizador Adam, tasa de aprendizaje, épocas, batch y curvas de pérdida.", 30),
                    ("C3", "Evaluación del modelo", "Evaluación de modelos", "Exactitud en conjunto de prueba, matriz de confusión y análisis de errores.", 20),
                    ("C4", "Calidad del código y reproducibilidad", SE, "Estructura de proyecto, semillas, control de versiones y documentación.", 20),
                ],
            },
            {
                "title": "Lab 4 · LLMs, prompting y RAG", "order": 4,
                "objectives": "Construir un asistente con recuperación aumentada (RAG) y evaluar su comportamiento de forma responsable.",
                "competencies": ["IA generativa y LLMs", "Ética y uso responsable de IA", SE],
                "criteria": [
                    ("C1", "Ingeniería de prompts", "IA generativa y LLMs", "Diseño de prompts con instrucciones, ejemplos few-shot y salida estructurada en JSON.", 25),
                    ("C2", "Recuperación aumentada RAG", "IA generativa y LLMs", "Embeddings, base vectorial, fragmentación de documentos y recuperación semántica.", 35),
                    ("C3", "Ética y uso responsable", "Ética y uso responsable de IA", "Análisis de sesgos, alucinaciones, privacidad de datos y transparencia.", 20),
                    ("C4", "Calidad del código y reproducibilidad", SE, "Manejo seguro de API keys con variables de entorno, pruebas y documentación.", 20),
                ],
            },
        ],
    },
]

DEMO_STUDENTS = [
    ("ana.rios@umanizales.edu.co", "Ana María Ríos (demo)", "U2026001", [0.95, 1.0]),
    ("carlos.perez@umanizales.edu.co", "Carlos Pérez (demo)", "U2026002", [0.55, 0.8]),
    ("valentina.ortiz@umanizales.edu.co", "Valentina Ortiz (demo)", "U2026003", [0.3, 0.55]),
]

FILLER = (
    "Durante el desarrollo del laboratorio se documentó el proceso experimental, se registraron las decisiones de diseño "
    "y se analizaron los resultados obtenidos frente a los objetivos planteados por el docente. "
)


def _criteria(rows):
    return [{"id": i, "name": n, "competency": comp, "description": d, "weight": w, "levels": LEVELS} for i, n, comp, d, w in rows]


def _evidence(criteria: list[dict], quality: float, lab_title: str) -> tuple[str, str]:
    parts = [f"Informe del {lab_title}."]
    k = max(1, round(len(criteria) * quality))
    for c in criteria[:k]:
        parts.append(f"{c['name']}: {c['description']} Se presentan resultados y su discusión técnica.")
    parts.append(FILLER * int(2 + quality * 40))
    code = "import numpy as np\nimport pandas as pd\nnp.random.seed(42)\n" if quality > 0.5 else ""
    return "\n".join(parts), code


_INIT_LOCK_KEY = 727_2026  # pg_advisory_lock: serializa la inicialización entre workers/instancias


async def _init() -> None:
    await create_all_tables()
    if settings.SEED_DEMO_DATA:
        await seed_demo()


async def init_db() -> None:
    """Idempotente y segura ante concurrencia (p. ej. `gunicorn -w 4` con INIT_DB_ON_STARTUP=true)."""
    if engine.dialect.name != "postgresql":
        await _init()
        return
    async with engine.connect() as conn:
        await conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _INIT_LOCK_KEY})
        try:
            await _init()
        finally:
            await conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _INIT_LOCK_KEY})


async def seed_demo() -> None:
    async with SessionLocal() as db:
        if (await db.execute(select(func.count(User.id)))).scalar_one() > 0:
            log.info("Seed omitido: la base de datos ya contiene usuarios.")
            return

        pwd = hash_password(settings.DEMO_PASSWORD)
        admin = User(email="admin@umanizales.edu.co", full_name="Administrador del Sistema", password_hash=pwd, role=Role.ADMINISTRADOR)
        teacher = User(email="docente@umanizales.edu.co", full_name="Docente Profundización I", password_hash=pwd, role=Role.DOCENTE)
        students = [User(email=e, full_name=n, student_code=c, password_hash=pwd, role=Role.ESTUDIANTE) for e, n, c, _ in DEMO_STUDENTS]
        db.add_all([admin, teacher, *students])
        await db.flush()

        provider = MockAIProvider()
        base_date = datetime.now(timezone.utc) - timedelta(days=60)
        for co_idx, co_data in enumerate(COHORTS):
            cohort = Cohort(name=co_data["name"], description=co_data["description"], order=co_data["order"])
            db.add(cohort)
            await db.flush()
            for lab_data in co_data["labs"]:
                lab = Laboratory(cohort_id=cohort.id, title=lab_data["title"], objectives=lab_data["objectives"],
                                 competencies=lab_data["competencies"], order=lab_data["order"])
                db.add(lab)
                await db.flush()
                crit = _criteria(lab_data["criteria"])
                rubric = Rubric(laboratory_id=lab.id, name=f"Rúbrica {lab.title}", criteria_json=crit, total_weight=100.0,
                                is_active=True, created_by=teacher.id)
                db.add(rubric)
                await db.flush()

                for s_idx, (student, (_, _, _, qualities)) in enumerate(zip(students, DEMO_STUDENTS)):
                    quality = qualities[co_idx] - (0.1 if lab.order % 2 == 0 else 0)
                    text, code = _evidence(crit, quality, lab.title)
                    when = base_date + timedelta(days=lab.order * 12 + s_idx)
                    sub = Submission(student_id=student.id, laboratory_id=lab.id, pdf_text=text, code_excerpt=code,
                                     pdf_original_name=f"informe_{lab.order}_demo.pdf",
                                     repo_url=f"https://github.com/demo-umanizales/lab{lab.order}" if code else None,
                                     notes="Entrega de demostración generada automáticamente.", submitted_at=when)
                    db.add(sub)
                    await db.flush()

                    # El último laboratorio del último estudiante queda SIN evaluar (demo del flujo completo)
                    if lab.order == 4 and s_idx == len(students) - 1:
                        continue
                    ctx = EvaluationContext(lab.title, lab.objectives, crit, text, code, sub.repo_url, {})
                    ai = ensure_matches_rubric(await provider.evaluate(ctx), crit)
                    by_id = {e.criterion_id: e for e in ai.evaluations}
                    grade = compute_final_score(crit, {k: v.partial_score for k, v in by_id.items()})
                    contrib = {g.criterion_id: float(g.contribution) for g in grade.lines}
                    lines = [{"criterion_id": c["id"], "name": c["name"], "competency": c["competency"], "weight": c["weight"],
                              "partial_score": by_id[c["id"]].partial_score, "ai_partial_score": by_id[c["id"]].partial_score,
                              "contribution": contrib[c["id"]], "evidence_quote": by_id[c["id"]].evidence_quote,
                              "reasoning": by_id[c["id"]].reasoning, "adjusted": False, "adjust_reason": ""} for c in crit]
                    pending = lab.order == 4 and s_idx == 1  # queda pendiente de aprobación docente
                    db.add(Evaluation(submission_id=sub.id, rubric_id=rubric.id, raw_llm_json=ai.model_dump(), criteria_scores=lines,
                                      raw_score=float(grade.raw_score), calculated_score=float(grade.final_score),
                                      ai_provider=provider.name, teacher_approved=not pending, reviewed_by=None if pending else teacher.id,
                                      approved_at=None if pending else when + timedelta(days=2), created_at=when + timedelta(days=1),
                                      teacher_comment="" if pending else "Revisado y aprobado por el docente."))
                    sub.status = SubmissionStatus.EVALUADO_IA if pending else SubmissionStatus.PUBLICADO
        await db.commit()
        log.info("Datos de demostración creados (contraseña demo: %s).", settings.DEMO_PASSWORD)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(init_db())
