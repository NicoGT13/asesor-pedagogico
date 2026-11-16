"""RF-209: exportación del Informe Integrado a PDF (fpdf2, sin dependencias nativas)."""
from __future__ import annotations

from datetime import datetime

from fpdf import FPDF

_REPL = {"≥": ">=", "≤": "<=", "–": "-", "—": "-", "…": "...", "→": "->", "×": "x", "“": '"', "”": '"', "‘": "'", "’": "'", "•": "-", "Σ": "Suma"}

NAVY = (15, 23, 42)
INDIGO = (79, 70, 229)
GRAY = (100, 116, 139)


def _t(text) -> str:
    s = "" if text is None else str(text)
    for k, v in _REPL.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


class _PDF(FPDF):
    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 18, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 11)
        self.set_xy(10, 5)
        self.cell(0, 8, _t("Asesor Pedagógico Inteligente  |  Universidad de Manizales"))
        self.ln(16)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 8, _t(f"Informe generado automáticamente - Página {self.page_no()}/{{nb}}"), align="C")


def _h2(pdf: FPDF, text: str):
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*INDIGO)
    pdf.cell(0, 8, _t(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*INDIGO)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    pdf.set_text_color(0, 0, 0)


def _p(pdf: FPDF, text: str, size=10, style=""):
    pdf.set_font("Helvetica", style, size)
    pdf.multi_cell(0, 5.5, _t(text), new_x="LMARGIN", new_y="NEXT")


def _fmt(x):
    return "-" if x is None else f"{x:.1f}".replace(".", ",")


def render_report_pdf(report: dict) -> bytes:
    pdf = _PDF(format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()

    st = report["student"]
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _t("Informe Integrado del Aprendizaje"), new_x="LMARGIN", new_y="NEXT")
    _p(pdf, f"Estudiante: {st['full_name']}   |   Código: {st.get('student_code') or 'N/A'}   |   {st['email']}")
    _p(pdf, f"Fecha: {datetime.fromisoformat(report['generated_at']).strftime('%Y-%m-%d %H:%M UTC')}", 9)
    if report.get("includes_pending"):
        _p(pdf, "Nota: incluye evaluaciones aún no aprobadas por el docente (vista preliminar).", 9, "I")

    _h2(pdf, "1. Resumen global")
    _p(pdf, f"Promedio general: {_fmt(report['overall_average'])} / 5,0  -  Nivel: {report['overall_level']}", 11, "B")
    _p(pdf, f"Laboratorios evaluados: {report['evaluated_labs']} de {report['total_labs']}.")
    if report.get("trend_between_cohorts") is not None:
        t = report["trend_between_cohorts"]
        _p(pdf, f"Evolución Cohorte 1 -> Cohorte 2: {'+' if t >= 0 else ''}{_fmt(t)} puntos.")

    _h2(pdf, "2. Rendimiento por cohorte")
    for co in report["cohorts"]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, _t(f"{co['name']}  -  Promedio: {_fmt(co['average'])}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(120, 6, "Laboratorio", border=1, fill=True)
        pdf.cell(25, 6, "Nota", border=1, fill=True, align="C")
        pdf.cell(45, 6, "Nivel", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        for lab in co["labs"]:
            pdf.cell(120, 6, _t(lab["title"][:70]), border=1)
            pdf.cell(25, 6, _fmt(lab["score"]), border=1, align="C")
            pdf.cell(45, 6, _t(lab["level"]), border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    _h2(pdf, "3. Dominio por competencia")
    for c in report["competencies"]:
        _p(pdf, f"- {c['name']}: {_fmt(c['average'])} ({c['level']})  ·  Labs: {', '.join(c['labs'])}", 9)

    _h2(pdf, "4. Brechas de conocimiento identificadas")
    if report["gaps"]:
        for g in report["gaps"]:
            _p(pdf, f"- {g['name']}: {_fmt(g['average'])} - {g['level']}", 10)
    else:
        _p(pdf, "No se identifican brechas por debajo del umbral (3,5).")

    _h2(pdf, "5. Plan personalizado de fortalecimiento académico")
    for item in report["plan"]:
        _p(pdf, f"{item['order']}. {item['competency']}  [Prioridad {item['priority']}]  {item['current_level']} -> {item['target']}", 10, "B")
        for a in item["actions"]:
            _p(pdf, f"    - {a}", 9)

    if report.get("strengths"):
        _h2(pdf, "6. Fortalezas consolidadas")
        for s in report["strengths"]:
            _p(pdf, f"- {s}", 9)

    out = pdf.output()
    return bytes(out)
