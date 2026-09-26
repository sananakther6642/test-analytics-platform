"""Tests for pass/fail summary and daily trend aggregation."""

from datetime import datetime

from tad_api.analytics.summary import summarize, trends_by_day
from tad_api.parsers.base import ParsedRun, ParsedTestResult


def _run(run_id, day_str, statuses):
    return ParsedRun(
        run_id=run_id,
        suite_name="s",
        git_sha="abc",
        branch="main",
        started_at=datetime.fromisoformat(day_str),
        finished_at=datetime.fromisoformat(day_str),
        environment="ci",
        tests=[
            ParsedTestResult(
                test_id=f"t{i}", name=f"t{i}", file="f.py", status=s, duration_ms=1.0
            )
            for i, s in enumerate(statuses)
        ],
    )


def test_summarize_empty_is_zero_not_divide_by_zero():
    s = summarize([])
    assert s.total_tests == 0
    assert s.pass_rate == 0.0


def test_summarize_counts_and_pass_rate():
    runs = [
        _run("r1", "2026-01-01T00:00:00", ["passed", "passed", "failed", "skipped"])
    ]
    s = summarize(runs)
    assert s.total_tests == 4
    assert s.passed == 2
    assert s.pass_rate == 0.5


def test_trends_by_day_groups_and_sorts():
    runs = [
        _run("r2", "2026-01-02T00:00:00", ["passed"]),
        _run("r1", "2026-01-01T00:00:00", ["failed", "failed"]),
        _run("r1b", "2026-01-01T12:00:00", ["passed"]),
    ]
    trends = trends_by_day(runs)
    assert [t.day.isoformat() for t in trends] == ["2026-01-01", "2026-01-02"]
    assert trends[0].failed == 2
    assert trends[0].passed == 1
    assert trends[1].passed == 1
