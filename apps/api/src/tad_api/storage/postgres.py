"""Postgres-backed RunStore.

Conforms to the same interface as InMemoryRunStore (storage/base.py) — the
routers that call `add`/`get`/`list` don't know or care which one they're
talking to.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tad_api.db.models import TestIdentity, TestResult, TestRun
from tad_api.parsers.base import ParsedRun, ParsedTestResult
from tad_api.storage.base import DailyCounts, ResultOutcome, RunStore


class PostgresRunStore(RunStore):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: ParsedRun) -> None:
        db_run = TestRun(
            run_id=run.run_id,
            suite_name=run.suite_name,
            git_sha=run.git_sha,
            branch=run.branch,
            started_at=run.started_at,
            finished_at=run.finished_at,
            environment=run.environment,
        )
        self._session.add(db_run)

        for t in run.tests:
            # test_identity rows are upserted implicitly: merge() inserts if
            # the primary key doesn't exist yet, or is a no-op update if it
            # does. Simpler than a separate exists-check + conditional
            # insert, and correct for this table's current 1:1-with-test_id
            # shape (see the ADR/model docstring on why this table exists).
            await self._session.merge(TestIdentity(test_id=t.test_id))

            self._session.add(
                TestResult(
                    run_id=run.run_id,
                    test_id=t.test_id,
                    name=t.name,
                    file=t.file,
                    status=t.status,
                    duration_ms=t.duration_ms,
                    retries=t.retries,
                    failure_message=t.failure_message,
                    # Denormalized from the parent run — see ADR 0003.
                    started_at=run.started_at,
                    git_sha=run.git_sha,
                )
            )

        await self._session.commit()

    async def get(self, run_id: str) -> ParsedRun | None:
        result = await self._session.execute(
            select(TestRun)
            .where(TestRun.run_id == run_id)
            .options(selectinload(TestRun.results))
        )
        db_run = result.scalar_one_or_none()
        return self._to_parsed_run(db_run) if db_run is not None else None

    async def list(self) -> list[ParsedRun]:
        # selectinload issues exactly one extra query for all results across
        # every matched run (batched by run_id), not one query per run —
        # avoids the N+1 that a naive per-run `get()` loop would produce.
        result = await self._session.execute(
            select(TestRun).options(selectinload(TestRun.results))
        )
        return [self._to_parsed_run(db_run) for db_run in result.scalars()]

    async def all_outcomes(self) -> list[ResultOutcome]:
        # A single query against test_results only — never touches
        # test_runs or test_identity, and can use the
        # ix_test_results_test_id_started_at index for the ordering
        # flakiness scoring needs (see ADR 0003 for why started_at/git_sha
        # are denormalized here rather than requiring a join).
        result = await self._session.execute(
            select(
                TestResult.test_id,
                TestResult.git_sha,
                TestResult.started_at,
                TestResult.status,
            ).order_by(TestResult.test_id, TestResult.started_at)
        )
        return [
            ResultOutcome(
                test_id=row.test_id,
                git_sha=row.git_sha,
                started_at=row.started_at,
                status=row.status,
            )
            for row in result.all()
        ]

    async def daily_counts(self) -> list[DailyCounts]:
        # GROUP BY DATE(started_at) does the day-bucketing in Postgres
        # rather than loading every result into Python to bucket by hand —
        # the same query shape trends_by_day() in analytics/summary.py
        # does in-process for the in-memory store, now pushed down to SQL.
        day = func.date(TestResult.started_at)
        status_count = func.count().filter
        result = await self._session.execute(
            select(
                day.label("day"),
                status_count(TestResult.status == "passed").label("passed"),
                status_count(TestResult.status == "failed").label("failed"),
                status_count(TestResult.status == "skipped").label("skipped"),
                status_count(TestResult.status == "error").label("error"),
            )
            .group_by(day)
            .order_by(day)
        )
        return [
            DailyCounts(
                day=row.day,
                passed=row.passed,
                failed=row.failed,
                skipped=row.skipped,
                error=row.error,
            )
            for row in result.all()
        ]

    @staticmethod
    def _to_parsed_run(db_run: TestRun) -> ParsedRun:
        return ParsedRun(
            run_id=db_run.run_id,
            suite_name=db_run.suite_name,
            git_sha=db_run.git_sha,
            branch=db_run.branch,
            started_at=db_run.started_at,
            finished_at=db_run.finished_at,
            environment=db_run.environment,
            tests=[
                ParsedTestResult(
                    test_id=r.test_id,
                    name=r.name,
                    file=r.file,
                    status=r.status,
                    duration_ms=r.duration_ms,
                    retries=r.retries,
                    failure_message=r.failure_message,
                )
                for r in db_run.results
            ],
        )
