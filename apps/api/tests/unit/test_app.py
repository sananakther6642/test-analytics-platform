"""End-to-end tests against the FastAPI app itself, via an in-process
ASGI client — proves the routers, storage, and parsers are wired correctly,
not just individually correct.
"""

import httpx
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport

from tad_api.main import app
from tad_api.storage.dependency import get_run_store
from tad_api.storage.memory import InMemoryRunStore


@pytest.fixture
async def client():
    # Override get_run_store so these tests exercise the routers with a
    # fast, DB-independent InMemoryRunStore rather than needing a real
    # Postgres connection — the point of these unit tests is proving the
    # routers/parsers/analytics wiring is correct, which doesn't need a
    # real database (that's what tests/integration/ is for). A single
    # shared instance across all requests within one test is fine here,
    # unlike PostgresRunStore, since InMemoryRunStore holds no per-request
    # resource that concurrent requests could corrupt.
    store = InMemoryRunStore()
    app.dependency_overrides[get_run_store] = lambda: store

    # ASGITransport alone never triggers `lifespan` — LifespanManager runs
    # startup/shutdown the same way a real ASGI server would.
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


VALID_RUN = {
    "run_id": "run-1",
    "suite_name": "suite",
    "git_sha": "abc1234",
    "branch": "main",
    "started_at": "2026-01-01T00:00:00",
    "finished_at": "2026-01-01T00:05:00",
    "environment": "ci",
    "tests": [
        {
            "test_id": "t1",
            "name": "test_a",
            "file": "a.py",
            "status": "passed",
            "duration_ms": 10.0,
        },
        {
            "test_id": "t2",
            "name": "test_b",
            "file": "b.py",
            "status": "failed",
            "duration_ms": 5.0,
        },
    ],
}


@pytest.mark.asyncio
async def test_liveness_never_fails(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_upload_then_retrieve_report(client):
    import json

    files = {"file": ("run.json", json.dumps(VALID_RUN), "application/json")}
    upload = await client.post("/api/v1/reports", files=files)
    assert upload.status_code == 200
    assert upload.json() == {"run_id": "run-1", "test_count": 2}

    get = await client.get("/api/v1/reports/run-1")
    assert get.status_code == 200
    assert get.json()["suite_name"] == "suite"


@pytest.mark.asyncio
async def test_upload_malformed_file_returns_422_not_500(client):
    files = {"file": ("bad.json", "{not json", "application/json")}
    resp = await client.post("/api/v1/reports", files=files)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_summary_reflects_uploaded_data(client):
    import json

    files = {"file": ("run.json", json.dumps(VALID_RUN), "application/json")}
    await client.post("/api/v1/reports", files=files)

    resp = await client.get("/api/v1/analytics/summary")
    body = resp.json()
    assert body["total_tests"] == 2
    assert body["passed"] == 1
    assert body["failed"] == 1


@pytest.mark.asyncio
async def test_get_nonexistent_report_is_404(client):
    resp = await client.get("/api/v1/reports/does-not-exist")
    assert resp.status_code == 404
