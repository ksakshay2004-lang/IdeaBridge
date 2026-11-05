"""Shared fixtures. Environment is configured BEFORE the app is imported (SQLite + local demo AI)."""
import os
import sys
import tempfile
import uuid

_tmp = tempfile.mkdtemp(prefix="ideabridge-test-")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db", "UPLOAD_DIR": f"{_tmp}/uploads", "APP_ENV": "test",
    "SECRET_KEY": "test-secret-key-test-secret-key-0123456789", "LLM_PROVIDER": "none", "ANTHROPIC_API_KEY": "",
    "OPENAI_API_KEY": "", "EMBEDDING_PROVIDER": "local", "EXTERNAL_RETRIEVAL": "none", "SEED_DEMO_DATA": "false",
    "ADMIN_EMAIL": "admin@ideabridge.io", "ADMIN_PASSWORD": "Admin#12345", "MAX_UPLOAD_MB": "1",
})
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest  # noqa: E402

try:
    from fastapi.testclient import TestClient  # noqa: E402
except ImportError:  # backend deps missing: only the ai_engine unit tests can run
    TestClient = None

PASSWORD = "Passw0rd!x"
IDEA = {
    "title": "Offline spaced repetition flashcards for rural schools",
    "short_description": "A mobile app that lets rural students study with spaced repetition flashcards offline.",
    "problem": "Students in low-connectivity regions cannot use cloud study tools and teachers cannot see who struggles.",
    "solution": "An offline-first mobile app that schedules flashcards with spaced repetition and syncs progress later.",
    "industry": "EdTech", "target_audience": "Rural secondary school students and teachers",
    "technologies": ["Mobile App", "Data Analytics"], "stage": "prototype", "visibility": "public",
    "business_potential": "School subscriptions and NGO grants", "funding_needed": 50000,
}


@pytest.fixture(scope="session")
def client():
    if TestClient is None:
        pytest.skip("backend dependencies not installed (pip install -r backend/requirements-dev.txt)")
    from app.main import app
    with TestClient(app) as c:
        yield c


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def signup(client):
    def _signup(role, name="Test User", company=None):
        email = f"{role}-{uuid.uuid4().hex[:10]}@ideabridge.io"
        r = client.post("/api/auth/register", json={"email": email, "password": PASSWORD, "full_name": name,
                                                    "role": role, "company_name": company})
        assert r.status_code == 201, r.text
        d = r.json()
        return {"h": hdr(d["access_token"]), "user": d["user"], "email": email, "token": d["access_token"]}
    return _signup


@pytest.fixture
def admin(client):
    r = client.post("/api/auth/login", json={"email": "admin@ideabridge.io", "password": "Admin#12345"})
    assert r.status_code == 200, r.text
    return {"h": hdr(r.json()["access_token"]), "user": r.json()["user"]}


@pytest.fixture
def make_idea(client):
    def _make(owner, **over):
        r = client.post("/api/ideas", json={**IDEA, **over}, headers=owner["h"])
        assert r.status_code == 201, r.text
        return r.json()["idea"]
    return _make
