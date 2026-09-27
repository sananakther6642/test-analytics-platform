"""Integration tests for PostgresRunStore against a real Postgres container.

Not mocks — every test here exercises actual SQL through actual migrations,
per the plan's explicit call to test against a real database. Mocking the
session would only prove our mock behaves the way we told it to; it
wouldn't catch a foreign-key violation, a type mismatch, or a migration
that doesn't actually match the ORM models — all real bug classes a mock
can't see.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tad_api.parsers.base import ParsedRun, ParsedTestResult
from tad_api.storage.postgres import PostgresRunStore


def _run(run_id: str, git_sha: str = "abc1234") -> ParsedRun:
    return ParsedRun(
        run_id=run_id,
        suite_name="suite",
        git_sha=git_sha,
        branch="main",
        # Timezone-aware: the schema is TIMESTAMPTZ (see ADR 0005 / migration
        # d03862a437ec). A naive datetime here would have masked the exact
        # bug that migration fixes.
        started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
        environment="ci",
        tests=[
            ParsedTestResult(
                test_id="t1",
                name="test_a",
                file="a.py",
                status="passed",
                duration_ms=10.0,
            ),
            ParsedTestResult(
                test_id="t2",
                name="test_b",
                file="b.py",
                status="failed",
                duration_ms=5.0,
                failure_message="boom",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_add_then_get_round_trips_correctly(db_session: AsyncSession):
    store = PostgresRunStore(db_session)
    await store.add(_run("run-1"))

    fetched = await store.get("run-1")

    assert fetched is not None
    assert fetched.run_id == "run-1"
    assert fetched.git_sha == "abc1234"
    assert len(fetched.tests) == 2
    statuses = {t.test_id: t.status for t in fetched.tests}
    assert statuses == {"t1": "passed", "t2": "failed"}
    failed = next(t for t in fetched.tests if t.test_id == "t2")
    assert failed.failure_message == "boom"


@pytest.mark.asyncio
async def test_get_nonexistent_run_returns_none(db_session: AsyncSession):
    store = PostgresRunStore(db_session)
    assert await store.get("does-not-exist") is None


@pytest.mark.asyncio
async def test_list_returns_all_runs_with_their_results(db_session: AsyncSession):
    store = PostgresRunStore(db_session)
    await store.add(_run("run-1"))
    await store.add(_run("run-2", git_sha="def5678"))

    runs = await store.list()

    assert {r.run_id for r in runs} == {"run-1", "run-2"}
    for r in runs:
        assert len(r.tests) == 2


@pytest.mark.asyncio
async def test_same_test_id_across_runs_shares_one_identity_row(
    db_session: AsyncSession,
):
    """t1 appears in both runs — test_identity.merge() must not fail on the
    second insert of the same test_id (this is the real behaviour the
    'upsert via merge()' comment in postgres.py claims; prove it).
    """
    store = PostgresRunStore(db_session)
    await store.add(_run("run-1"))
    await store.add(_run("run-2"))  # same test_ids (t1, t2) again

    result = await db_session.execute(text("SELECT COUNT(*) FROM test_identity"))
    count = result.scalar_one()
    assert count == 2  # t1 and t2, not 4 — no duplicate identity rows


@pytest.mark.asyncio
async def test_denormalized_fields_match_the_parent_run(db_session: AsyncSession):
    """Per ADR 0003: started_at and git_sha are copied onto test_results at
    insert time. Verify they actually match the run they came from, not
    just that the columns exist.
    """
    store = PostgresRunStore(db_session)
    run = _run("run-1", git_sha="feedface")
    await store.add(run)

    result = await db_session.execute(
        text("SELECT git_sha, started_at FROM test_results WHERE run_id = 'run-1'")
    )
    rows = result.all()
    assert len(rows) == 2
    for git_sha, started_at in rows:
        assert git_sha == "feedface"
        assert started_at == run.started_at
