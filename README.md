# Asesor Pedagógico Inteligente

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Jhiguita11/asesor-pedagogico)

Plataforma web de **evaluación y retroalimentación asistida por IA** para las Cohortes 1 y 2 del curso
*Profundización I – Inteligencia Artificial* · Ingeniería de Sistemas y Telecomunicaciones · **Universidad de Manizales**.
Autor y desarrollador principal: **Sergio Sánchez Arango**.

> **Regla de negocio central (RF-207):** el LLM **nunca** calcula la nota final. La IA devuelve puntajes parciales por criterio
> en un JSON validado con Pydantic (`extra="forbid"`), y el backend aplica
> `Nota = Σ (puntaje_i × ponderación_i / 100)` con aritmética `Decimal` y redondeo `ROUND_HALF_UP` a una nota de 0,0 a 5,0.

---

## 1. Arquitectura

```
┌──────────────── Navegador (SPA: HTML5 + Tailwind precompilado + JS vainilla + Chart.js + D3) ───────────────┐
│ Login/RBAC · Portafolio C1/C2 · Constructor de rúbricas (Σ=100% en vivo) · Supervisión IA · Informe · Mapa   │
└───────────────────────────────────────────────┬──────────────────────────────────────────────────────────────┘
                                                │ REST + JWT (Bearer)
┌───────────────────────────────── FastAPI (ASGI) · Gunicorn + UvicornWorker ──────────────────────────────────┐
│  api/routes      → capa de interfaz (auth, portfolio, rubrics, evaluations, reports)                          │
│  api/deps.py     → sesión BD, usuario actual, require_roles() (RBAC), auditoría                               │
│  services/       → DOMINIO (Python puro, testeable sin HTTP):                                                 │
│     rubric_validator.py  RF-204  Σ ponderaciones == 100 exacto (Decimal)                                      │
│     grading.py           RF-207  motor determinista de calificación                                           │
│     ai_engine.py         RF-205/206  Strategy: OpenAIProvider | MockAIProvider + validación cruzada vs rúbrica │
│     files.py             RF-202  PDF (magic bytes, pypdf), ZIP (anti Zip-Slip/Zip-Bomb, sin ejecución), GitHub│
│     analytics.py         RF-209..212  informe integrado, panorama de cohortes, mapa mental                    │
│     pdf_report.py        RF-209  exportación PDF (fpdf2)                                                      │
│  schemas/        → Pydantic: DTOs de API + contrato estricto del LLM (schemas/ai.py, SRS §6.2)                │
│  models/         → SQLAlchemy 2 (async): users, cohorts, laboratories, rubrics, submissions, evaluations, audit│
└───────────────────────────────────────────────┬──────────────────────────────────────────────────────────────┘
                                 SQLite + aiosqlite (local)  │  PostgreSQL + asyncpg (Render) — JSON ⇄ JSONB
```

**Patrones aplicados:** Clean Architecture (dominio sin dependencias de FastAPI), Strategy (proveedores de IA),
Dependency Injection (`Depends`), Repository implícito vía `AsyncSession`, DTO (Pydantic), Audit Log, Fail-fast validation.

### Flujo de evaluación
1. Estudiante carga PDF/ZIP/GitHub → se extrae texto y estructura **en el upload** y se persiste en BD (el disco de Render Free es efímero).
2. Docente pulsa **Evaluar con IA** → se exige rúbrica **activa y válida** (Σ=100 %).
3. El proveedor IA responde JSON → `AIEvaluationOutput.model_validate()` (rechaza campos extra como `final_score`) → `ensure_matches_rubric()` (ni criterios faltantes, ni duplicados, ni inventados).
4. `compute_final_score()` calcula la nota. La salida cruda de la IA queda **inmutable** en `raw_llm_json`.
5. Docente puede **ajustar puntajes parciales** (con justificación obligatoria) → el backend recalcula → **aprueba y publica**. Publicada ⇒ inmutable. Todo queda en `audit_logs`.

---

## 2. Estructura de carpetas

```
asesor-pedagogico/
├── app/
│   ├── main.py                 # App FastAPI, middlewares, routers, SPA fallback, /api/health
│   ├── seed.py                 # create_all + datos demo idempotentes (python -m app.seed)
│   ├── core/  config.py · database.py · security.py
│   ├── models/models.py
│   ├── schemas/ ai.py · schemas.py
│   ├── services/ rubric_validator.py · grading.py · ai_engine.py · files.py · analytics.py · pdf_report.py
│   ├── api/ deps.py · routes/{auth,portfolio,rubrics,evaluations,reports}.py
│   └── data/project.json       # Abstract + equipo (edítelo sin tocar código)
├── frontend/
│   ├── index.html
│   ├── src/input.css           # fuente Tailwind
│   └── static/ css/app.css (compilado) · js/app.js · vendor/{chart.umd.js,d3.min.js} · img/team/
├── tests/                      # pytest: unitarias (grading, esquema IA) + integración E2E
├── scripts/ start.sh (producción) · build_css.sh (Tailwind)
├── main.py                     # shim: permite `gunicorn main:app` (comando del SRS §9)
├── Dockerfile · render.yaml · requirements.txt · requirements-dev.txt · tailwind.config.js
└── .env.example · .gitignore · .dockerignore
```

---

## 3. Ejecución local

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                      # Windows: copy .env.example .env
uvicorn app.main:app --reload
```
Abra **http://localhost:8000** · Swagger: **http://localhost:8000/api/docs**

Cuentas demo (contraseña `Demo2026*`):

| Rol | Correo |
|---|---|
| Docente | docente@umanizales.edu.co |
| Administrador | admin@umanizales.edu.co |
| Estudiantes | ana.rios@ · carlos.perez@ · valentina.ortiz@umanizales.edu.co |

Pruebas: `pytest -q` (29 pruebas). Para reiniciar los datos demo, borre `asesor.db`.

**Con Docker:** `docker build -t asesor . && docker run -p 8000:8000 asesor`

---

## 4. Despliegue en Render (Git + CI/CD)

```bash
git init && git add . && git commit -m "Asesor Pedagógico Inteligente v3.0.0"
git branch -M main
git remote add origin https://github.com/<usuario>/asesor-pedagogico.git
git push -u origin main
```

### Opción A — Blueprint (recomendada, 1 clic)
Render → **New → Blueprint** → seleccione el repo. `render.yaml` crea el **Web Service (Docker, free)** y la **PostgreSQL free**,
enlaza `DATABASE_URL`, genera `SECRET_KEY` y configura el health check `/api/health`. Render le pedirá `OPENAI_API_KEY` (puede dejarla vacía).

### Opción B — Manual
1. **New → PostgreSQL** (free) → copie la *Internal Database URL*.
2. **New → Web Service** → repo → Runtime **Docker** (detecta el `Dockerfile`).
3. Environment: `DATABASE_URL`, `SECRET_KEY` (`python -c "import secrets;print(secrets.token_urlsafe(48))"`), `ENVIRONMENT=production`.
4. Health Check Path: `/api/health`.

> Si prefiere runtime **Python nativo** en vez de Docker: Build `pip install -r requirements.txt` ·
> Start `./scripts/start.sh` (o el del SRS: `gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker`, en cuyo caso deje `INIT_DB_ON_STARTUP=true`).

Cada `git push origin main` dispara un redeploy automático.

### Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./asesor.db` | Acepta `postgres://`, `postgresql://` (se normaliza a `asyncpg`; `sslmode=require` soportado → sirve Neon/Supabase) |
| `SECRET_KEY` | inseguro | Firma de JWT. **Obligatorio en producción** |
| `AI_PROVIDER` | `mock` | `mock` (determinista) u `openai` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL` | — / `gpt-4o-mini` / OpenAI | Cualquier endpoint compatible OpenAI con Structured Outputs |
| `AI_FALLBACK_TO_MOCK` | `true` | Si el LLM falla o viola el esquema, usa el motor determinista (queda registrado en `ai_provider`) |
| `WEB_CONCURRENCY` | `2` | Workers Gunicorn |
| `SEED_DEMO_DATA` | `true` | Crea datos demo si la BD está vacía. Póngalo en `false` para producción real |
| `INIT_DB_ON_STARTUP` | `true` (Docker: `false`) | En Docker la inicialización corre en `start.sh` antes de Gunicorn para evitar carreras entre workers |

### Limitaciones del plan gratuito de Render (tenerlas presentes en la sustentación)
- El Web Service se **suspende tras 15 min sin tráfico** y tarda ~1 min en despertar: abra la URL un minuto antes de la presentación.
- **Filesystem efímero:** los PDF/ZIP subidos se pierden al redeploy/reinicio. El texto extraído y las evaluaciones **sí persisten** en PostgreSQL. Para conservar archivos use un disco persistente (plan pago) u object storage (S3/R2).
- La **PostgreSQL free expira a los 30 días** (14 días de gracia). Para el semestre completo, apunte `DATABASE_URL` a Neon o Supabase (free sin expiración).

---

## 5. Activar un LLM real
```
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```
Se envía `response_format={"type":"json_schema","strict":true}` con el esquema derivado de `AIEvaluationOutput`, `temperature=0`,
y un *system prompt* con defensa contra *prompt injection* (la evidencia del estudiante va delimitada y se trata como datos).

## 6. Seguridad
Bcrypt (12 rounds) · JWT HS256 con `exp`/`iss` · RBAC en backend (no sólo en UI) · registro público sólo crea ESTUDIANTE ·
HSTS / nosniff / X-Frame-Options · validación por *magic bytes* · límite de tamaño en streaming · código estudiantil **nunca ejecutado**
(SRS §8.2: la ejecución, si se requiere, debe ir a contenedores efímeros `--network none --memory 256m --cpus 0.5`) · usuario no-root en Docker.

## 7. Personalización
- **Foto del equipo:** guarde `frontend/static/img/team/sergio.jpg` (si no existe, se muestran iniciales).
- **Más integrantes / abstract:** edite `app/data/project.json`.
- **Estilos:** tras cambiar clases Tailwind ejecute `./scripts/build_css.sh` (requiere Node.js) y versione `frontend/static/css/app.css`.
