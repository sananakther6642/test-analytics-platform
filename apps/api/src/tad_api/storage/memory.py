"""In-process, non-persistent RunStore.

Kept alongside the Postgres-backed store (not deleted once Phase 2 lands)
because it's genuinely useful for fast unit tests that don't need a real
database — see tests/unit/test_app.py.
"""

from __future__ import annotations

from collections import defaultdict

from tad_api.parsers.base import ParsedRun
from tad_api.storage.base import DailyCounts, ResultOutcome, RunStore


class InMemoryRunStore(RunStore):
    def __init__(self) -> None:
        self._runs: dict[str, ParsedRun] = {}

    async def add(self, run: ParsedRun) -> None:
        self._runs[run.run_id] = run

    async def get(self, run_id: str) -> ParsedRun | None:
        return self._runs.get(run_id)

    async def list(self) -> list[ParsedRun]:
        return list(self._runs.values())

    async def all_outcomes(self) -> list[ResultOutcome]:
        # No index to exploit in-memory — this is fine as a plain Python
        # loop, unlike PostgresRunStore where the same method issues a real
        # SQL query.
        return [
            ResultOutcome(
                test_id=t.test_id,
                git_sha=run.git_sha,
                started_at=run.started_at,
                status=t.status,
            )
            for run in self._runs.values()
            for t in run.tests
        ]

    async def daily_counts(self) -> list[DailyCounts]:
        by_day: dict = defaultdict(lambda: defaultdict(int))
        for run in self._runs.values():
            day = run.started_at.date()
            for t in run.tests:
                by_day[day][t.status] += 1

        return [
            DailyCounts(
                day=day,
                passed=counts["passed"],
                failed=counts["failed"],
                skipped=counts["skipped"],
                error=counts["error"],
            )
            for day, counts in sorted(by_day.items())
        ]
