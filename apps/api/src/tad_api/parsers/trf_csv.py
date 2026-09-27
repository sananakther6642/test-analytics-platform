"""Parser for the TRF v1 CSV variant.

One row per test result. Run-level fields (run_id, suite_name, git_sha,
branch, started_at, finished_at, environment) are repeated on every row —
simplest possible CSV shape, and it's what most CI tools actually emit when
they export "flat" reports. Columns:

run_id,suite_name,git_sha,branch,started_at,finished_at,environment,
test_id,name,file,status,duration_ms,retries,failure_message,tags

`tags` is a `;`-separated list within the cell.
"""

import csv
import io
from datetime import datetime

from tad_api.parsers.base import ParsedRun, ParsedTestResult, ParseError, ReportParser

_REQUIRED_COLUMNS = {
    "run_id",
    "suite_name",
    "git_sha",
    "branch",
    "started_at",
    "finished_at",
    "environment",
    "test_id",
    "name",
    "file",
    "status",
    "duration_ms",
}


class TrfCsvParser(ReportParser):
    def can_parse(self, filename: str, content_type: str | None) -> bool:
        return filename.lower().endswith(".csv") or content_type == "text/csv"

    def parse(self, raw: bytes) -> ParsedRun:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ParseError("File is not valid UTF-8 text") from exc

        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise ParseError("CSV has no header row")

        missing = _REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ParseError(f"CSV missing required columns: {sorted(missing)}")

        rows = list(reader)
        if not rows:
            raise ParseError("CSV has a header but no data rows")

        first = rows[0]
        try:
            tests = [
                ParsedTestResult(
                    test_id=row["test_id"],
                    name=row["name"],
                    file=row["file"],
                    status=row["status"],
                    duration_ms=float(row["duration_ms"]),
                    retries=int(row.get("retries") or 0),
                    failure_message=row.get("failure_message") or None,
                    tags=[t for t in (row.get("tags") or "").split(";") if t],
                )
                for row in rows
            ]
            return ParsedRun(
                run_id=first["run_id"],
                suite_name=first["suite_name"],
                git_sha=first["git_sha"],
                branch=first["branch"],
                started_at=datetime.fromisoformat(first["started_at"]),
                finished_at=datetime.fromisoformat(first["finished_at"]),
                environment=first["environment"],
                tests=tests,
            )
        except (KeyError, ValueError) as exc:
            raise ParseError(f"Malformed row: {exc}") from exc
