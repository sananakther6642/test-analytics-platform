"""In-process, non-persistent RunStore.

Kept alongside the Postgres-backed store (not deleted once Phase 2 lands)
because it's genuinely useful for fast unit tests that don't need a real
database — see tests/unit/test_app.py.
"""

from tad_api.parsers.base import ParsedRun
from tad_api.storage.base import RunStore


class InMemoryRunStore(RunStore):
    def __init__(self) -> None:
        self._runs: dict[str, ParsedRun] = {}

    async def add(self, run: ParsedRun) -> None:
        self._runs[run.run_id] = run

    async def get(self, run_id: str) -> ParsedRun | None:
        return self._runs.get(run_id)

    async def list(self) -> list[ParsedRun]:
        return list(self._runs.values())
