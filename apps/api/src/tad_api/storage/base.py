"""Storage interface for parsed runs.

Phase 1 implementation is in-memory (`memory.py`). Phase 2 swaps this for a
Postgres-backed repository behind the same interface — nothing that calls
`RunStore` needs to change. This is the one abstraction Phase 1 justifies
building ahead of need: storing uploads on local disk/memory directly would
work today but breaks the moment there's more than one process, and the
plan explicitly calls that out as a common mistake.
"""

from abc import ABC, abstractmethod

from tad_api.parsers.base import ParsedRun


class RunStore(ABC):
    @abstractmethod
    def add(self, run: ParsedRun) -> None: ...

    @abstractmethod
    def get(self, run_id: str) -> ParsedRun | None: ...

    @abstractmethod
    def list(self) -> list[ParsedRun]: ...
