"""Pruebas de integración end-to-end de la API."""
import io
import zipfile

from fpdf import FPDF


def _pdf_bytes(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, text)
    return bytes(pdf.output())


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("src/model.py", "import torch\nclass Net: pass\n")
        z.writestr("README.md", "# Lab")
        z.writestr("../evil.py", "malicioso")  # Zip-Slip: debe ignorarse
    return buf.getvalue()


def test_health(client):
    assert client.get("/api/health").json()["database"] is True


def test_rbac_estudiante_no_crea_rubricas(client, student):
    r = client.post("/api/rubrics", headers=student, json={"laboratory_id": 1, "name": "x", "criteria": [{"id": "C1", "name": "xx", "competency": "yy", "weight": 100}]})
    assert r.status_code == 403


def test_sin_token_401(client):
    assert client.get("/api/submissions").status_code == 401


def test_rubrica_invalida_bloqueada(client, teacher):
    body = {"laboratory_id": 1, "name": "Mala", "criteria": [
        {"id": "C1", "name": "Uno", "competency": "Comp", "weight": 60},
        {"id": "C2", "name": "Dos", "competency": "Comp", "weight": 30}]}
    v = client.post("/api/rubrics/validate", headers=teacher, json=body).json()
    assert v["valid"] is False and v["total_weight"] == 90
    assert client.post("/api/rubrics", headers=teacher, json=body).status_code == 422


def test_flujo_completo_entrega_evaluacion_ajuste_publicacion(client, teacher, student):
    text = ("Informe de laboratorio. Se aplicó limpieza y transformación de datos con tratamiento de valores faltantes, "
            "outliers y normalización. Se entrenó un modelo de regresión lineal y se interpretan coeficientes y residuales. ") * 8
    files = {"pdf": ("informe.pdf", _pdf_bytes(text), "application/pdf"), "code_zip": ("code.zip", _zip_bytes(), "application/zip")}
    r = client.post("/api/submissions", headers=student, data={"laboratory_id": "1", "repo_url": "https://github.com/demo/lab1"}, files=files)
    assert r.status_code == 201, r.text
    sub = r.json()
    assert sub["pdf_text_chars"] > 100
    assert "../evil.py" not in sub["code_manifest"]["files"]

    # Estudiante no puede evaluar
    assert client.post(f"/api/submissions/{sub['id']}/evaluate", headers=student).status_code == 403

    ev = client.post(f"/api/submissions/{sub['id']}/evaluate", headers=teacher)
    assert ev.status_code == 201, ev.text
    ev = ev.json()
    # La nota es exactamente la fórmula aplicada sobre los parciales
    expected = round(sum(c["partial_score"] * c["weight"] / 100 for c in ev["criteria_scores"]) + 1e-9, 1)
    assert ev["calculated_score"] == expected

    # Antes de aprobar, el estudiante no la ve
    assert client.get(f"/api/evaluations/{ev['id']}", headers=student).status_code == 403

    adj = client.patch(f"/api/evaluations/{ev['id']}/adjust", headers=teacher,
                       json={"adjustments": [{"criterion_id": "C1", "partial_score": 5.0, "reason": "Evidencia adicional revisada"}]}).json()
    assert adj["adjusted"] and adj["criteria_scores"][0]["partial_score"] == 5.0

    pub = client.post(f"/api/evaluations/{ev['id']}/approve", headers=teacher, json={"teacher_comment": "Buen trabajo"}).json()
    assert pub["teacher_approved"] is True
    assert client.get(f"/api/evaluations/{ev['id']}", headers=student).status_code == 200
    # Publicada ⇒ inmutable
    assert client.patch(f"/api/evaluations/{ev['id']}/adjust", headers=teacher,
                        json={"adjustments": [{"criterion_id": "C1", "partial_score": 1, "reason": "xxx"}]}).status_code == 409


def test_pdf_falso_rechazado(client, student):
    r = client.post("/api/submissions", headers=student, data={"laboratory_id": "1"},
                    files={"pdf": ("x.pdf", b"no soy un pdf", "application/pdf")})
    assert r.status_code == 415


def test_informe_y_mapa(client, student, teacher):
    rep = client.get("/api/reports/student", headers=student).json()
    assert rep["overall_average"] is not None and len(rep["cohorts"]) == 2
    pdf = client.get("/api/reports/student/pdf", headers=student)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    mm = client.get("/api/mindmap", headers=student).json()
    assert mm["type"] == "root" and len(mm["children"]) == 2
    ov = client.get("/api/reports/overview", headers=teacher).json()
    assert len(ov["cohorts"]) == 2
    assert client.get("/api/reports/overview", headers=student).status_code == 403


def test_proyecto_publico(client):
    p = client.get("/api/project").json()
    names = {m["name"] for m in p["team"] if m["highlight"]}
    assert {"Sergio Sánchez Arango", "Nicolás Giraldo Tobón"} <= names


def test_spa_servida(client):
    r = client.get("/")
    assert r.status_code == 200 and "Asesor Pedagógico" in r.text
