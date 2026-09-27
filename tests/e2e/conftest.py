"""Shared fixtures for E2E tests.

Tests target BASE_URL, which defaults to the local Docker Compose stack
(localhost:8080) but can point at a deployed environment instead (Phase 6+)
without changing any test code — only this env var.
"""

import json
import os
from pathlib import Path

import pytest

BASE_URL = os.environ.get("TAD_E2E_BASE_URL", "http://localhost:8080")


@pytest.fixture
def app_base_url() -> str:
    # Named app_base_url, not base_url — pytest-playwright's own
    # pytest-base-url plugin already owns a session-scoped `base_url`
    # fixture, and shadowing it with a function-scoped one of the same
    # name is a real ScopeMismatch error, not just a style nit.
    return BASE_URL


@pytest.fixture
def sample_trf_file(tmp_path: Path) -> Path:
    """A single valid TRF v1 JSON file, written to a temp path so the
    browser's file-upload input can attach it like a real user would.
    """
    data = {
        "run_id": "e2e-smoke-run",
        "suite_name": "e2e-smoke-suite",
        "git_sha": "e2e0001",
        "branch": "main",
        "started_at": "2026-01-01T00:00:00",
        "finished_at": "2026-01-01T00:05:00",
        "environment": "e2e",
        "tests": [
            {
                "test_id": "t1",
                "name": "test_one",
                "file": "a.py",
                "status": "passed",
                "duration_ms": 10.0,
            },
            {
                "test_id": "t2",
                "name": "test_two",
                "file": "b.py",
                "status": "failed",
                "duration_ms": 5.0,
            },
        ],
    }
    file_path = tmp_path / "e2e-smoke-run.json"
    file_path.write_text(json.dumps(data))
    return file_path


@pytest.fixture
def malformed_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "malformed.json"
    file_path.write_text("{ this is not valid json")
    return file_path
