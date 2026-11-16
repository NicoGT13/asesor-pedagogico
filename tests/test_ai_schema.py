"""Validación estricta de la salida del LLM (RF-206)."""
import asyncio

import pytest

from app.schemas.ai import strict_json_schema
from app.services.ai_engine import AIEngineError, EvaluationContext, MockAIProvider, ensure_matches_rubric, parse_ai_json

CRIT = [
    {"id": "C1", "name": "Métricas de evaluación", "competency": "Evaluación de modelos", "description": "Matriz de confusión, precisión y recall", "weight": 60},
    {"id": "C2", "name": "Calidad del código", "competency": "Ingeniería", "description": "Pruebas y documentación", "weight": 40},
]
VALID = {
    "general_summary": "ok", "strengths": ["a"], "weaknesses": ["b"], "recommendations": ["c"],
    "evaluations": [
        {"criterion_id": "C1", "partial_score": 4.5, "evidence_quote": "q", "reasoning": "r"},
        {"criterion_id": "C2", "partial_score": 3.0, "evidence_quote": "q", "reasoning": "r"},
    ],
}


def test_json_valido():
    out = ensure_matches_rubric(parse_ai_json(VALID), CRIT)
    assert [e.criterion_id for e in out.evaluations] == ["C1", "C2"]


def test_campo_extra_rechazado_llm_no_puede_dar_nota_final():
    bad = {**VALID, "final_score": 5.0}
    with pytest.raises(AIEngineError):
        parse_ai_json(bad)


def test_puntaje_fuera_de_rango_rechazado():
    bad = {**VALID, "evaluations": [{**VALID["evaluations"][0], "partial_score": 7}, VALID["evaluations"][1]]}
    with pytest.raises(AIEngineError):
        parse_ai_json(bad)


def test_criterio_faltante_rechazado():
    bad = {**VALID, "evaluations": VALID["evaluations"][:1]}
    with pytest.raises(AIEngineError, match="faltantes"):
        ensure_matches_rubric(parse_ai_json(bad), CRIT)


def test_json_malformado():
    with pytest.raises(AIEngineError):
        parse_ai_json("{no es json")


def test_schema_strict_compatible():
    s = strict_json_schema()
    assert s["additionalProperties"] is False
    assert set(s["required"]) == {"general_summary", "strengths", "weaknesses", "evaluations", "recommendations"}


def test_mock_es_determinista():
    ctx = EvaluationContext("Lab", "obj", CRIT, "Se presenta la matriz de confusión con precisión y recall. " * 20, "def test(): pass", None, {})
    a = asyncio.run(MockAIProvider().evaluate(ctx))
    b = asyncio.run(MockAIProvider().evaluate(ctx))
    assert a == b
    assert all(0 <= e.partial_score <= 5 for e in a.evaluations)


def _patch_transport(monkeypatch, handler):
    import httpx

    real = httpx.AsyncClient
    monkeypatch.setattr("app.services.ai_engine.httpx.AsyncClient",
                        lambda *a, **k: real(*a, transport=httpx.MockTransport(handler), **k))


def test_openai_provider_structured_output(monkeypatch):
    import json

    import httpx

    from app.services.ai_engine import OpenAIProvider

    seen = {}

    def handler(request: httpx.Request):
        body = json.loads(request.content)
        seen.update(body)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(VALID)}}]})

    _patch_transport(monkeypatch, handler)
    ctx = EvaluationContext("Lab", "obj", CRIT, "texto", "", None, {})
    out = asyncio.run(OpenAIProvider("k", "gpt-test", "https://llm.local/v1", 5).evaluate(ctx))
    assert out.evaluations[0].partial_score == 4.5
    assert seen["temperature"] == 0
    assert seen["response_format"]["json_schema"]["strict"] is True


def test_fallback_si_llm_viola_esquema(monkeypatch):
    import json

    import httpx

    from app.core.config import settings
    from app.services import ai_engine

    bad = {**VALID, "final_score": 5.0}  # el LLM intenta "poner la nota"
    _patch_transport(monkeypatch, lambda r: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(bad)}}]}))
    monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "k")
    monkeypatch.setattr(settings, "AI_FALLBACK_TO_MOCK", True)
    ctx = EvaluationContext("Lab", "obj", CRIT, "matriz de confusión precisión recall " * 30, "", None, {})
    out, provider = asyncio.run(ai_engine.run_ai_evaluation(ctx))
    assert "fallback" in provider and len(out.evaluations) == 2

    monkeypatch.setattr(settings, "AI_FALLBACK_TO_MOCK", False)
    with pytest.raises(AIEngineError):
        asyncio.run(ai_engine.run_ai_evaluation(ctx))
