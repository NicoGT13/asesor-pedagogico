"""Contrato estricto de salida del LLM (SRS §6.2 / RF-206).

`extra="forbid"` → cualquier campo no declarado que devuelva el modelo provoca
ValidationError: la respuesta de la IA se rechaza en lugar de aceptarse "a medias".
Observe que NO existe campo de nota final: el LLM no tiene forma de emitirla (RF-207).
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class CriterionEvaluation(BaseModel, extra="forbid"):
    criterion_id: str = Field(..., description="ID único del criterio de la rúbrica")
    partial_score: float = Field(..., ge=0.0, le=5.0, description="Puntaje parcial asignado al criterio (0.0 a 5.0)")
    evidence_quote: str = Field(..., description="Evidencia exacta encontrada en la solución del estudiante")
    reasoning: str = Field(..., description="Justificación técnica de la evaluación")


class AIEvaluationOutput(BaseModel, extra="forbid"):
    general_summary: str = Field(..., description="Resumen general del desempeño del estudiante")
    strengths: List[str] = Field(..., description="Fortalezas detectadas")
    weaknesses: List[str] = Field(..., description="Debilidades o brechas técnicas detectadas")
    evaluations: List[CriterionEvaluation] = Field(..., description="Evaluación detallada de cada criterio")
    recommendations: List[str] = Field(..., description="Recomendaciones de mejoramiento")


def strict_json_schema() -> dict:
    """JSON Schema para `response_format: json_schema` (modo strict de OpenAI).

    El modo strict exige `additionalProperties: false` y todos los campos en
    `required`; además algunos proveedores no soportan `minimum/maximum`, por lo que
    se eliminan aquí y el rango 0–5 se re-impone con Pydantic al validar.
    """
    schema = AIEvaluationOutput.model_json_schema()

    def clean(node):
        if isinstance(node, dict):
            for key in ("title", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
                node.pop(key, None)
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"].keys())
            for v in node.values():
                clean(v)
        elif isinstance(node, list):
            for v in node:
                clean(v)
        return node

    return clean(schema)
