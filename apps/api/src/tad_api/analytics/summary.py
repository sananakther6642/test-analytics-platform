"""Pass/fail summary and trend-over-time aggregation.

Deliberately simple counting — no need for cleverness here, unlike
flakiness.py where the naive approach is actually wrong.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import date

from tad_api.parsers.base import ParsedRun


@dataclass(frozen=True)
class Summary:
    total_runs: int
    total_tests: int
    passed: int
    failed: int
    skipped: int
    error: int
    pass_rate: float


@dataclass(frozen=True)
class DailyTrend:
    day: date
    passed: int
    failed: int
    skipped: int
    error: int


def summarize(runs: list[ParsedRun]) -> Summary:
    counts: Counter[str] = Counter()
    for run in runs:
        for t in run.tests:
            counts[t.status] += 1

    total = sum(counts.values())
    passed = counts["passed"]
    return Summary(
        total_runs=len(runs),
        total_tests=total,
        passed=passed,
        failed=counts["failed"],
        skipped=counts["skipped"],
        error=counts["error"],
        pass_rate=round(passed / total, 4) if total else 0.0,
    )


def trends_by_day(runs: list[ParsedRun]) -> list[DailyTrend]:
    by_day: dict[date, Counter[str]] = {}
    for run in runs:
        day = run.started_at.date()
        counts = by_day.setdefault(day, Counter())
        for t in run.tests:
            counts[t.status] += 1

    return [
        DailyTrend(
            day=day,
            passed=counts["passed"],
            failed=counts["failed"],
            skipped=counts["skipped"],
            error=counts["error"],
        )
        for day, counts in sorted(by_day.items())
    ]
