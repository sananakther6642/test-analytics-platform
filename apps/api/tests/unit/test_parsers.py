"""Tests for the TRF parsers — the format-parsing edge cases most likely to
break in practice: malformed input, missing fields, wrong types.
"""

import json

import pytest

from tad_api.parsers.base import ParseError
from tad_api.parsers.registry import get_parser
from tad_api.parsers.trf_csv import TrfCsvParser
from tad_api.parsers.trf_json import TrfJsonParser

VALID_RUN = {
    "run_id": "run-1",
    "suite_name": "suite",
    "git_sha": "abc1234",
    "branch": "main",
    "started_at": "2026-01-01T00:00:00",
    "finished_at": "2026-01-01T00:05:00",
    "environment": "ci",
    "tests": [
        {
            "test_id": "t1",
            "name": "test_a",
            "file": "a.py",
            "status": "passed",
            "duration_ms": 10.0,
        }
    ],
}


def test_registry_picks_json_parser_by_extension():
    parser = get_parser("report.json", None)
    assert isinstance(parser, TrfJsonParser)


def test_registry_picks_csv_parser_by_extension():
    parser = get_parser("report.csv", None)
    assert isinstance(parser, TrfCsvParser)


def test_registry_raises_for_unknown_format():
    with pytest.raises(ParseError):
        get_parser("report.xml", None)


def test_json_parser_parses_valid_run():
    parser = TrfJsonParser()
    run = parser.parse(json.dumps(VALID_RUN).encode())
    assert run.run_id == "run-1"
    assert len(run.tests) == 1
    assert run.tests[0].status == "passed"


def test_json_parser_rejects_invalid_json():
    parser = TrfJsonParser()
    with pytest.raises(ParseError, match="Invalid JSON"):
        parser.parse(b"{not json")


def test_json_parser_rejects_missing_required_field():
    bad = dict(VALID_RUN)
    del bad["git_sha"]
    parser = TrfJsonParser()
    with pytest.raises(ParseError, match="schema"):
        parser.parse(json.dumps(bad).encode())


def test_json_parser_rejects_invalid_status_enum():
    bad = json.loads(json.dumps(VALID_RUN))
    bad["tests"][0]["status"] = "definitely_not_a_status"
    parser = TrfJsonParser()
    with pytest.raises(ParseError):
        parser.parse(json.dumps(bad).encode())


CSV_HEADER = (
    "run_id,suite_name,git_sha,branch,started_at,finished_at,environment,"
    "test_id,name,file,status,duration_ms,retries,failure_message,tags\n"
)


def test_csv_parser_parses_multiple_rows_into_one_run():
    rows = (
        "run-1,suite,abc1234,main,2026-01-01T00:00:00,2026-01-01T00:05:00,ci,"
        "t1,test_a,a.py,passed,10.0,0,,\n"
        "run-1,suite,abc1234,main,2026-01-01T00:00:00,2026-01-01T00:05:00,ci,"
        "t2,test_b,b.py,failed,20.0,1,boom,slow;flaky\n"
    )
    parser = TrfCsvParser()
    run = parser.parse((CSV_HEADER + rows).encode())
    assert run.run_id == "run-1"
    assert len(run.tests) == 2
    assert run.tests[1].tags == ["slow", "flaky"]
    assert run.tests[1].failure_message == "boom"


def test_csv_parser_rejects_missing_columns():
    parser = TrfCsvParser()
    with pytest.raises(ParseError, match="missing required columns"):
        parser.parse(b"run_id,suite_name\nrun-1,suite\n")


def test_csv_parser_rejects_header_only():
    parser = TrfCsvParser()
    with pytest.raises(ParseError, match="no data rows"):
        parser.parse(CSV_HEADER.encode())
