"""In-process, non-persistent RunStore. Phase 1 only — see base.py."""

from tad_api.parsers.base import ParsedRun
from tad_api.storage.base import RunStore


class InMemoryRunStore(RunStore):
    def __init__(self) -> None:
        self._runs: dict[str, ParsedRun] = {}

    def add(self, run: ParsedRun) -> None:
        self._runs[run.run_id] = run

    def get(self, run_id: str) -> ParsedRun | None:
        return self._runs.get(run_id)

    def list(self) -> list[ParsedRun]:
        return list(self._runs.values())
