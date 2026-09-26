"""Parser strategy interface.

Each concrete parser turns raw uploaded bytes into a `ParsedRun`. New formats
plug in by implementing this interface and registering in `registry.py` —
nothing else needs to change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedTestResult:
    test_id: str
    name: str
    file: str
    status: str  # "passed" | "failed" | "skipped" | "error"
    duration_ms: float
    retries: int = 0
    failure_message: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class ParsedRun:
    run_id: str
    suite_name: str
    git_sha: str
    branch: str
    started_at: datetime
    finished_at: datetime
    environment: str
    tests: list[ParsedTestResult]


class ParseError(ValueError):
    """Raised when raw input cannot be parsed as a valid test run.

    Carries a message safe to return to the API caller — never leaks
    internal exception details or file paths.
    """


class ReportParser(ABC):
    """A parser for one report format."""

    @abstractmethod
    def can_parse(self, filename: str, content_type: str | None) -> bool:
        """Whether this parser should handle a file with this name/type."""

    @abstractmethod
    def parse(self, raw: bytes) -> ParsedRun:
        """Parse raw bytes into a ParsedRun, or raise ParseError."""
