"""Storage interface for parsed runs.

Phase 1 implementation is in-memory (`memory.py`). Phase 2 adds a
Postgres-backed one (`postgres.py`) behind the same interface — nothing
that calls `RunStore` needs to change.

Async throughout, even though Phase 1's in-memory implementation has no
real I/O to await: a Postgres-backed store using SQLAlchemy's async engine
must be async, and retrofitting a sync interface after the fact would mean
either blocking calls inside FastAPI's async request handlers or bridging
with asyncio.run() — both worse than declaring the interface correctly
from the start. `InMemoryRunStore`'s methods are async but simply don't
await anything internally.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from tad_api.parsers.base import ParsedRun


@dataclass(frozen=True)
class ResultOutcome:
    """The minimal shape flakiness scoring needs from one test_results row —
    matches analytics.flakiness.RunOutcome's fields exactly. Kept as a
    separate type (not reusing RunOutcome directly) so storage/ doesn't
    import from analytics/, keeping the dependency direction one-way:
    routers depend on both storage and analytics, storage doesn't need to
    know analytics exists.
    """

    test_id: str
    git_sha: str
    started_at: datetime
    status: str


@dataclass(frozen=True)
class DailyCounts:
    day: date
    passed: int
    failed: int
    skipped: int
    error: int


class RunStore(ABC):
    @abstractmethod
    async def add(self, run: ParsedRun) -> None: ...

    @abstractmethod
    async def get(self, run_id: str) -> ParsedRun | None: ...

    @abstractmethod
    async def list(self) -> list[ParsedRun]: ...

    @abstractmethod
    async def all_outcomes(self) -> list[ResultOutcome]:
        """Every (test, run) outcome, for flakiness scoring.

        A separate method from list() rather than deriving this from list()'s
        output in Python: list() returns full ParsedRun objects (every field,
        every test's full detail) for the /reports endpoints, which need
        that. Flakiness scoring needs only four columns from test_results
        and never needs to touch test_runs or test_identity at all — a
        Postgres-backed implementation can answer this with a single
        indexed query instead of hydrating full run objects it then
        discards most of.
        """
        ...

    @abstractmethod
    async def daily_counts(self) -> list[DailyCounts]:
        """Pass/fail/skip/error counts grouped by day, for trend charts.

        Same reasoning as all_outcomes(): a Postgres-backed implementation
        can do this with GROUP BY DATE(started_at) instead of loading every
        run and every result into Python just to bucket them by day.
        """
        ...
