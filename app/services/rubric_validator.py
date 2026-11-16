"""RF-203 / RF-204: validación lógica y matemática de rúbricas.

Se usa `Decimal` construido desde `str(float)` para que 33.3 + 33.3 + 33.4 sume
exactamente 100.0 (en binario flotante daría 99.99999999999999).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, Mapping

REQUIRED_TOTAL = Decimal("100")


def to_decimal(value: float | int | str) -> Decimal:
    return Decimal(str(value))


@dataclass
class RubricValidationResult:
    valid: bool
    total_weight: Decimal
    errors: list[str] = field(default_factory=list)

    @property
    def difference(self) -> Decimal:
        return self.total_weight - REQUIRED_TOTAL


def validate_rubric_criteria(criteria: Iterable[Mapping]) -> RubricValidationResult:
    criteria = list(criteria)
    errors: list[str] = []

    if not criteria:
        return RubricValidationResult(False, Decimal("0"), ["La rúbrica debe tener al menos un criterio."])

    ids = [str(c.get("id", "")).strip() for c in criteria]
    duplicated = sorted({i for i in ids if ids.count(i) > 1})
    if duplicated:
        errors.append(f"IDs de criterio duplicados: {', '.join(duplicated)}.")
    if any(not i for i in ids):
        errors.append("Todos los criterios deben tener un ID.")

    total = Decimal("0")
    for c in criteria:
        w = to_decimal(c.get("weight", 0))
        if w <= 0:
            errors.append(f"El criterio '{c.get('id')}' debe tener una ponderación mayor a 0%.")
        if w > REQUIRED_TOTAL:
            errors.append(f"El criterio '{c.get('id')}' no puede superar el 100%.")
        total += w

        for lvl in c.get("levels", []) or []:
            if to_decimal(lvl.get("min_score", 0)) > to_decimal(lvl.get("max_score", 0)):
                errors.append(f"Criterio '{c.get('id')}', nivel '{lvl.get('label')}': rango inválido.")

    if total != REQUIRED_TOTAL:
        errors.append(
            f"Error de parametrización: la sumatoria de ponderaciones es {total.normalize():f}% "
            f"y debe ser exactamente 100% (diferencia {(total - REQUIRED_TOTAL).normalize():f}%). "
            "La activación de la evaluación queda bloqueada."
        )

    return RubricValidationResult(valid=not errors, total_weight=total, errors=errors)
