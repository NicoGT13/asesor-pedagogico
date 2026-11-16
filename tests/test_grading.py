"""Pruebas unitarias del motor determinista (RF-207) y del validador de rúbricas (RF-204)."""
from decimal import Decimal

import pytest

from app.services.grading import GradingError, compute_final_score, performance_level
from app.services.rubric_validator import validate_rubric_criteria

CRIT = [
    {"id": "C1", "name": "A", "weight": 30},
    {"id": "C2", "name": "B", "weight": 20},
    {"id": "C3", "name": "C", "weight": 50},
]


def test_formula_exacta():
    r = compute_final_score(CRIT, {"C1": 4.0, "C2": 3.0, "C3": 5.0})
    # 4*0.3 + 3*0.2 + 5*0.5 = 1.2 + 0.6 + 2.5 = 4.3
    assert r.final_score == Decimal("4.3")
    assert r.raw_score == Decimal("4.3000")


def test_redondeo_half_up():
    crit = [{"id": "A", "weight": 50}, {"id": "B", "weight": 50}]
    assert compute_final_score(crit, {"A": 3.4, "B": 3.5}).final_score == Decimal("3.5")  # 3.45 → 3.5


def test_pesos_decimales_suman_100_sin_error_flotante():
    crit = [{"id": "A", "weight": 33.3}, {"id": "B", "weight": 33.3}, {"id": "C", "weight": 33.4}]
    assert validate_rubric_criteria(crit).valid
    assert compute_final_score(crit, {"A": 5, "B": 5, "C": 5}).final_score == Decimal("5.0")


def test_determinismo():
    a = compute_final_score(CRIT, {"C1": 3.7, "C2": 4.1, "C3": 2.9})
    b = compute_final_score(CRIT, {"C1": 3.7, "C2": 4.1, "C3": 2.9})
    assert a == b


@pytest.mark.parametrize("weights", [[30, 20, 40], [30, 20, 60], [100.01]])
def test_rubrica_distinta_de_100_se_bloquea(weights):
    crit = [{"id": f"C{i}", "weight": w} for i, w in enumerate(weights)]
    v = validate_rubric_criteria(crit)
    assert not v.valid and any("100%" in e for e in v.errors)
    with pytest.raises(GradingError):
        compute_final_score(crit, {c["id"]: 4 for c in crit})


def test_ids_duplicados():
    v = validate_rubric_criteria([{"id": "X", "weight": 50}, {"id": "X", "weight": 50}])
    assert not v.valid


def test_criterio_faltante_o_extra():
    with pytest.raises(GradingError, match="Faltan"):
        compute_final_score(CRIT, {"C1": 4, "C2": 4})
    with pytest.raises(GradingError, match="inexistentes"):
        compute_final_score(CRIT, {"C1": 4, "C2": 4, "C3": 4, "C9": 4})


def test_puntaje_fuera_de_rango():
    with pytest.raises(GradingError, match="fuera de rango"):
        compute_final_score(CRIT, {"C1": 5.1, "C2": 4, "C3": 4})


def test_niveles():
    assert performance_level(4.7) == "Sobresaliente"
    assert performance_level(4.0) == "Competente"
    assert performance_level(3.0) == "En desarrollo"
    assert performance_level(2.9) == "Inicial"
