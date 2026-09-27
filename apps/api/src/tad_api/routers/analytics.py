"""Summary, trend, and flaky-test analytics over uploaded reports."""

from fastapi import APIRouter, Depends, Query

from tad_api.analytics.flakiness import RunOutcome, find_flaky_tests
from tad_api.analytics.summary import summarize
from tad_api.storage.base import RunStore
from tad_api.storage.dependency import get_run_store

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary(run_store: RunStore = Depends(get_run_store)) -> dict:
    runs = await run_store.list()
    s = summarize(runs)
    return {
        "total_runs": s.total_runs,
        "total_tests": s.total_tests,
        "passed": s.passed,
        "failed": s.failed,
        "skipped": s.skipped,
        "error": s.error,
        "pass_rate": s.pass_rate,
    }


@router.get("/trends")
async def get_trends(
    days: int = Query(default=30, ge=1, le=365),
    run_store: RunStore = Depends(get_run_store),
) -> list[dict]:
    # daily_counts() aggregates in SQL (GROUP BY DATE(started_at)), not by
    # loading every run/result into Python — see storage/base.py's
    # docstring on why this is a separate method from list().
    counts = (await run_store.daily_counts())[-days:]
    return [
        {
            "day": c.day.isoformat(),
            "passed": c.passed,
            "failed": c.failed,
            "skipped": c.skipped,
            "error": c.error,
        }
        for c in counts
    ]


@router.get("/flaky")
async def get_flaky(
    threshold: float = Query(default=0.1, ge=0.0, le=1.0),
    run_store: RunStore = Depends(get_run_store),
) -> list[dict]:
    # all_outcomes() queries test_results directly, ordered by
    # (test_id, started_at) — exercises ix_test_results_test_id_started_at
    # rather than hydrating every full run/test object just to discard most
    # of each one's fields.
    raw_outcomes = await run_store.all_outcomes()
    outcomes = [
        RunOutcome(
            test_id=o.test_id,
            git_sha=o.git_sha,
            started_at=o.started_at,
            status=o.status,
        )
        for o in raw_outcomes
    ]
    results = find_flaky_tests(outcomes, threshold=threshold)
    return [
        {
            "test_id": r.test_id,
            "score": r.score,
            "same_commit_disagreements": r.same_commit_disagreements,
            "flip_rate": r.flip_rate,
            "total_runs": r.total_runs,
        }
        for r in results
    ]
