"""RF-207: Motor de cálculo DETERMINISTA de calificaciones (SRS §7.1).

    Nota Final = Σ ( PuntajeParcial_i × Ponderación_i / 100 )

Reglas de negocio:
  1. La IA sólo aporta puntajes parciales por criterio (0.0–5.0); jamás la nota final.
  2. Debe existir exactamente un puntaje por cada criterio de la rúbrica (ni faltantes ni extra).
  3. La rúbrica debe sumar exactamente 100 % (si no, se rechaza el cálculo).
  4. Aritmética en Decimal; redondeo oficial a 1 decimal con ROUND_HALF_UP (3.45 → 3.5).
  5. Mismas entradas ⇒ misma salida (función pura, sin estado ni aleatoriedad).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Mapping, Sequence

from app.services.rubric_validator import to_decimal, validate_rubric_criteria

MIN_SCORE = Decimal("0.0")
MAX_SCORE = Decimal("5.0")


class GradingError(ValueError):
    """Inconsistencia entre la salida de la IA y la rúbrica."""


@dataclass(frozen=True)
class GradeLine:
    criterion_id: str
    weight: Decimal
    partial_score: Decimal
    contribution: Decimal  # partial_score * weight / 100


@dataclass(frozen=True)
class GradeResult:
    lines: tuple[GradeLine, ...]
    raw_score: Decimal    # 4 decimales, trazabilidad
    final_score: Decimal  # 1 decimal, nota oficial

    @property
    def formula(self) -> str:
        terms = " + ".join(f"{l.partial_score}×{l.weight.normalize():f}%" for l in self.lines)
        return f"{terms} = {self.raw_score} → {self.final_score}"


def compute_final_score(criteria: Sequence[Mapping], partial_scores: Mapping[str, float]) -> GradeResult:
    validation = validate_rubric_criteria(criteria)
    if not validation.valid:
        raise GradingError("Rúbrica inválida: " + " ".join(validation.errors))

    expected_ids = [str(c["id"]) for c in criteria]
    received_ids = set(partial_scores.keys())
    missing = [i for i in expected_ids if i not in received_ids]
    unknown = sorted(received_ids - set(expected_ids))
    if missing:
        raise GradingError(f"Faltan puntajes para los criterios: {', '.join(missing)}.")
    if unknown:
        raise GradingError(f"Se recibieron criterios inexistentes en la rúbrica: {', '.join(unknown)}.")

    lines: list[GradeLine] = []
    total = Decimal("0")
    for c in criteria:
        cid = str(c["id"])
        score = to_decimal(partial_scores[cid])
        if score < MIN_SCORE or score > MAX_SCORE:
            raise GradingError(f"Puntaje fuera de rango para '{cid}': {score} (permitido 0.0–5.0).")
        weight = to_decimal(c["weight"])
        contribution = score * weight / Decimal("100")
        total += contribution
        lines.append(GradeLine(cid, weight, score, contribution.quantize(Decimal("0.0001"), ROUND_HALF_UP)))

    raw = total.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    final = total.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    final = max(MIN_SCORE, min(MAX_SCORE, final))  # defensa en profundidad
    return GradeResult(tuple(lines), raw, final)


def performance_level(score: float | None) -> str:
    if score is None:
        return "Sin evidencia"
    if score >= 4.6:
        return "Sobresaliente"
    if score >= 4.0:
        return "Competente"
    if score >= 3.0:
        return "En desarrollo"
    return "Inicial"
