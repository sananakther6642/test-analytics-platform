"""Tests for the flaky-test detection algorithm.

These are the tests that matter most in the codebase: the algorithm's whole
point is to avoid the naive "any test with mixed results is flaky" mistake,
so the test suite specifically exercises the case that mistake gets wrong.
"""

from datetime import datetime

from tad_api.analytics.flakiness import RunOutcome, find_flaky_tests, score_test


def _outcome(test_id, sha, status, minute):
    return RunOutcome(
        test_id=test_id,
        git_sha=sha,
        started_at=datetime(2026, 1, 1, 0, minute),
        status=status,
    )


def test_stable_test_scores_zero():
    """A test that always passes, across many commits, is not flaky."""
    outcomes = [_outcome("t1", f"sha{i}", "passed", i) for i in range(10)]
    result = score_test("t1", outcomes)
    assert result.score == 0.0
    assert result.same_commit_disagreements == 0


def test_regression_then_fix_is_not_flaky():
    """The naive 'has both pass and fail' definition would flag this test as
    flaky. It isn't — it regressed at sha2 and was fixed at sha4. Every
    commit's outcome is internally consistent; nothing here is unstable.
    """
    outcomes = [
        _outcome("t1", "sha1", "passed", 0),
        _outcome("t1", "sha2", "failed", 1),
        _outcome("t1", "sha3", "failed", 2),
        _outcome("t1", "sha4", "passed", 3),
        _outcome("t1", "sha5", "passed", 4),
    ]
    result = score_test("t1", outcomes)
    assert result.same_commit_disagreements == 0
    # Some flip-rate signal exists (consecutive statuses did change), but the
    # dominant, causally-sound signal must be zero — this is exactly the
    # distinction the algorithm exists to make.
    assert result.score < 0.5


def test_same_commit_disagreement_is_flagged():
    """Same git_sha, different outcomes across repeated runs — this is the
    causally unambiguous flaky signal: nothing about the code changed.
    """
    outcomes = [
        _outcome("t1", "sha1", "passed", 0),
        _outcome("t1", "sha1", "failed", 1),
        _outcome("t1", "sha1", "passed", 2),
    ]
    result = score_test("t1", outcomes)
    assert result.same_commit_disagreements == 1
    assert result.score > 0.5


def test_find_flaky_tests_filters_by_threshold_and_sorts_descending():
    outcomes = [
        # t1: stable
        _outcome("t1", "sha1", "passed", 0),
        _outcome("t1", "sha2", "passed", 1),
        # t2: flaky (same-commit disagreement)
        _outcome("t2", "sha1", "passed", 0),
        _outcome("t2", "sha1", "failed", 1),
        # t3: also flaky, but only flip-rate signal (weaker → lower score)
        _outcome("t3", "sha1", "passed", 0),
        _outcome("t3", "sha2", "failed", 1),
        _outcome("t3", "sha3", "passed", 2),
    ]
    results = find_flaky_tests(outcomes, threshold=0.1)
    test_ids = [r.test_id for r in results]

    assert "t1" not in test_ids
    assert "t2" in test_ids
    assert "t3" in test_ids
    # t2 (same-commit disagreement) must outrank t3 (flip-rate only)
    assert results[0].test_id == "t2"
    assert results[0].score >= results[1].score


def test_single_run_is_never_flaky():
    """A test with only one observation has no basis for a flakiness claim."""
    outcomes = [_outcome("t1", "sha1", "failed", 0)]
    result = score_test("t1", outcomes)
    assert result.score == 0.0
