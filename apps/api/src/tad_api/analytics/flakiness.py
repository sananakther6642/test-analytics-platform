"""Flaky-test detection.

A naive definition — "this test has both passed and failed" — conflates
flakiness with a real regression that later got fixed. We use two signals
instead, combined into one score:

1. Same-commit disagreement: the same test, run against the *same git_sha*,
   produced different outcomes. This is causally unambiguous — nothing about
   the code changed between those runs, so the test itself is unstable.
   Weighted highest.

2. Flip-rate: the fraction of consecutive-run status changes over a sliding
   window, for tests that don't have repeat runs against the same commit.
   Weaker signal (a real regression-then-fix also flips), so weighted lower
   and only used to catch what same-commit disagreement can't see.

See docs/decisions/ for the ADR on this design (added once the API is wired
up and there's a natural point to reference it from).
"""

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise

# Weight given to same-commit disagreement vs. flip-rate in the combined
# score. Same-commit is causally sound; flip-rate is a weaker heuristic.
_SAME_COMMIT_WEIGHT = 0.7
_FLIP_RATE_WEIGHT = 0.3


@dataclass(frozen=True)
class RunOutcome:
    """One (test, run) observation — the minimal shape flakiness needs."""

    test_id: str
    git_sha: str
    started_at: object  # comparable/sortable; a datetime in practice
    status: str  # "passed" | "failed" | "skipped" | "error"


@dataclass(frozen=True)
class FlakinessResult:
    test_id: str
    score: float  # 0.0 (stable) .. 1.0 (maximally flaky)
    same_commit_disagreements: int
    flip_rate: float
    total_runs: int


def _same_commit_disagreement_rate(outcomes: list[RunOutcome]) -> tuple[float, int]:
    """Fraction of distinct git_shas where this test showed >1 outcome."""
    by_sha: dict[str, set[str]] = defaultdict(set)
    for o in outcomes:
        by_sha[o.git_sha].add(o.status)

    disagreeing_shas = sum(1 for statuses in by_sha.values() if len(statuses) > 1)
    total_shas = len(by_sha)
    if total_shas == 0:
        return 0.0, 0
    return disagreeing_shas / total_shas, disagreeing_shas


def _flip_rate(outcomes: list[RunOutcome]) -> float:
    """Fraction of consecutive runs (ordered by time) whose status changed."""
    if len(outcomes) < 2:
        return 0.0
    ordered = sorted(outcomes, key=lambda o: o.started_at)
    flips = sum(1 for prev, curr in pairwise(ordered) if prev.status != curr.status)
    return flips / (len(ordered) - 1)


def score_test(test_id: str, outcomes: list[RunOutcome]) -> FlakinessResult:
    """Compute a flakiness score for one test from its historical outcomes."""
    same_commit_rate, disagreements = _same_commit_disagreement_rate(outcomes)
    flip_rate = _flip_rate(outcomes)

    combined = _SAME_COMMIT_WEIGHT * same_commit_rate + _FLIP_RATE_WEIGHT * flip_rate

    return FlakinessResult(
        test_id=test_id,
        score=round(combined, 4),
        same_commit_disagreements=disagreements,
        flip_rate=round(flip_rate, 4),
        total_runs=len(outcomes),
    )


def find_flaky_tests(
    outcomes: list[RunOutcome], threshold: float = 0.1
) -> list[FlakinessResult]:
    """Score every test present in `outcomes`, return those above threshold.

    Sorted by score descending, so the most-flaky tests surface first.
    """
    by_test: dict[str, list[RunOutcome]] = defaultdict(list)
    for o in outcomes:
        by_test[o.test_id].append(o)

    results = [score_test(test_id, obs) for test_id, obs in by_test.items()]
    return sorted(
        (r for r in results if r.score >= threshold),
        key=lambda r: r.score,
        reverse=True,
    )
