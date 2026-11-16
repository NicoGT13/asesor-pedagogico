import os
import sys
import tempfile
from pathlib import Path

# BD aislada por sesión de pruebas (debe configurarse ANTES de importar la app)
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["AI_PROVIDER"] = "mock"
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["INIT_DB_ON_STARTUP"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PWD = "Demo2026*"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": PWD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def teacher(client):
    return _login(client, "docente@umanizales.edu.co")


@pytest.fixture(scope="session")
def student(client):
    return _login(client, "ana.rios@umanizales.edu.co")
