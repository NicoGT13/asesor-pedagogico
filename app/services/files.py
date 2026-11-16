"""RF-202: recepción segura de evidencias (PDF, ZIP de código, repositorio GitHub).

Seguridad (SRS §8.2 – sandboxing):
  * El código del estudiante NUNCA se ejecuta en el servidor web: sólo análisis estático
    (lectura de texto). La ejecución, si se requiere, debe delegarse a contenedores efímeros
    sin red (`docker run --network none --memory 256m --cpus 0.5 ...`).
  * Validación por "magic bytes" (no por extensión), límite de tamaño en streaming,
    protección contra Zip-Slip (rutas absolutas o `..`) y Zip-Bomb (tamaño descomprimido).
  * El texto se extrae al subir y se persiste en BD: la evaluación no depende del disco
    (importante en Render Free, cuyo filesystem es efímero).
"""
from __future__ import annotations

import io
import json
import re
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader

from app.core.config import settings

PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06")
MAX_PDF_TEXT = 60_000
MAX_CODE_EXCERPT = 30_000
CODE_EXTENSIONS = {
    ".py", ".ipynb", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".cs", ".r", ".m",
    ".sql", ".md", ".txt", ".yaml", ".yml", ".toml", ".json", ".html", ".css", ".sh", ".go", ".rs", ".kt",
}
IGNORED_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "env", ".ipynb_checkpoints", "dist", "build"}
GITHUB_RE = re.compile(r"^https://(www\.)?github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+/?(\.git)?(/.*)?$")


def upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


async def read_limited(file: UploadFile) -> bytes:
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    buf = io.BytesIO()
    while chunk := await file.read(1024 * 256):
        buf.write(chunk)
        if buf.tell() > limit:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"El archivo supera {settings.MAX_UPLOAD_MB} MB.")
    return buf.getvalue()


def save_bytes(data: bytes, suffix: str, subdir: str) -> str:
    folder = upload_root() / subdir
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{suffix}"
    (folder / name).write_bytes(data)
    return f"{subdir}/{name}"


def resolve_stored(rel: str) -> Path:
    root = upload_root().resolve()
    path = (root / rel).resolve()
    if root not in path.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ruta de archivo inválida.")
    return path


def extract_pdf_text(data: bytes) -> str:
    if not data.startswith(PDF_MAGIC):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "El informe debe ser un PDF válido.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El PDF está cifrado; cargue una versión sin contraseña.")
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except HTTPException:
        raise
    except Exception as exc:  # pypdf lanza múltiples tipos
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"No fue posible leer el PDF: {exc}") from exc
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) < 30:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El PDF no contiene texto legible (¿es un escaneo?). RF-202 exige PDF con texto seleccionable.",
        )
    return text[:MAX_PDF_TEXT]


def _notebook_code(raw: str) -> str:
    try:
        nb = json.loads(raw)
        cells = nb.get("cells", [])
        return "\n\n".join(
            "".join(c.get("source", [])) if isinstance(c.get("source"), list) else str(c.get("source", ""))
            for c in cells
            if c.get("cell_type") in {"code", "markdown"}
        )
    except (json.JSONDecodeError, AttributeError):
        return raw


def analyze_code_zip(data: bytes) -> tuple[dict, str]:
    """Devuelve (manifest, excerpt). No extrae a disco ni ejecuta nada."""
    if not data.startswith(ZIP_MAGIC):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "El código debe cargarse como archivo .zip válido.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ZIP corrupto.") from exc

    infos = zf.infolist()
    total_uncompressed = sum(i.file_size for i in infos)
    if total_uncompressed > settings.MAX_ZIP_UNCOMPRESSED_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "El ZIP descomprimido excede el límite permitido.")
    if len(infos) > 3000:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El ZIP contiene demasiados archivos.")

    by_ext: dict[str, int] = {}
    files: list[str] = []
    excerpt_parts: list[str] = []
    budget = MAX_CODE_EXCERPT
    total_lines = 0

    for info in sorted(infos, key=lambda i: i.filename):
        p = PurePosixPath(info.filename)
        if info.is_dir() or p.is_absolute() or ".." in p.parts:
            continue  # Zip-Slip: se ignora
        if any(part in IGNORED_DIRS for part in p.parts):
            continue
        ext = p.suffix.lower() or "(sin extensión)"
        by_ext[ext] = by_ext.get(ext, 0) + 1
        files.append(str(p))
        if p.suffix.lower() in CODE_EXTENSIONS and info.file_size < 400_000 and budget > 0:
            raw = zf.read(info).decode("utf-8", errors="replace")
            if p.suffix.lower() == ".ipynb":
                raw = _notebook_code(raw)
            total_lines += raw.count("\n") + 1
            snippet = raw[: min(budget, 6000)]
            excerpt_parts.append(f"# ---- {p} ----\n{snippet}")
            budget -= len(snippet)

    manifest = {
        "total_files": len(files),
        "by_extension": dict(sorted(by_ext.items(), key=lambda kv: -kv[1])),
        "files": files[:200],
        "analyzed_lines": total_lines,
        "has_tests": any("test" in f.lower() for f in files),
        "has_readme": any(PurePosixPath(f).name.lower().startswith("readme") for f in files),
        "has_requirements": any(PurePosixPath(f).name.lower() in {"requirements.txt", "pyproject.toml", "environment.yml", "package.json"} for f in files),
    }
    return manifest, "\n\n".join(excerpt_parts)


def validate_repo_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not GITHUB_RE.match(url):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El repositorio debe ser una URL https://github.com/usuario/repositorio")
    return url
