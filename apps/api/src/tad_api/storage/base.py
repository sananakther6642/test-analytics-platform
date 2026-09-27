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

from abc import ABC, abstractmethod

from tad_api.parsers.base import ParsedRun


class RunStore(ABC):
    @abstractmethod
    async def add(self, run: ParsedRun) -> None: ...

    @abstractmethod
    async def get(self, run_id: str) -> ParsedRun | None: ...

    @abstractmethod
    async def list(self) -> list[ParsedRun]: ...
