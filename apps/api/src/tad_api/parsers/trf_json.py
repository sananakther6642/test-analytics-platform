"""Parser for TRF v1 JSON — see schemas/trf-v1.schema.json."""

import json
from datetime import datetime

import jsonschema

from tad_api.config import settings
from tad_api.parsers.base import ParseError, ParsedRun, ParsedTestResult, ReportParser

_SCHEMA_PATH = settings.schema_dir / "trf-v1.schema.json"
_schema = json.loads(_SCHEMA_PATH.read_text())


class TrfJsonParser(ReportParser):
    def can_parse(self, filename: str, content_type: str | None) -> bool:
        return filename.lower().endswith(".json") or content_type == "application/json"

    def parse(self, raw: bytes) -> ParsedRun:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid JSON: {exc.msg} at line {exc.lineno}") from exc

        try:
            jsonschema.validate(data, _schema)
        except jsonschema.ValidationError as exc:
            raise ParseError(f"Does not match TRF v1 schema: {exc.message}") from exc

        return ParsedRun(
            run_id=data["run_id"],
            suite_name=data["suite_name"],
            git_sha=data["git_sha"],
            branch=data["branch"],
            started_at=datetime.fromisoformat(data["started_at"]),
            finished_at=datetime.fromisoformat(data["finished_at"]),
            environment=data["environment"],
            tests=[
                ParsedTestResult(
                    test_id=t["test_id"],
                    name=t["name"],
                    file=t["file"],
                    status=t["status"],
                    duration_ms=t["duration_ms"],
                    retries=t.get("retries", 0),
                    failure_message=t.get("failure_message"),
                    tags=t.get("tags", []),
                )
                for t in data["tests"]
            ],
        )
