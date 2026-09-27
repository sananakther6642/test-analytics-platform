"""Summary, trend, and flaky-test analytics over uploaded reports."""

from fastapi import APIRouter, Query, Request

from tad_api.analytics.flakiness import RunOutcome, find_flaky_tests
from tad_api.analytics.summary import summarize, trends_by_day

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary(request: Request) -> dict:
    runs = await request.app.state.run_store.list()
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
    request: Request, days: int = Query(default=30, ge=1, le=365)
) -> list[dict]:
    runs = await request.app.state.run_store.list()
    trends = trends_by_day(runs)[-days:]
    return [
        {
            "day": t.day.isoformat(),
            "passed": t.passed,
            "failed": t.failed,
            "skipped": t.skipped,
            "error": t.error,
        }
        for t in trends
    ]


@router.get("/flaky")
async def get_flaky(
    request: Request, threshold: float = Query(default=0.1, ge=0.0, le=1.0)
) -> list[dict]:
    runs = await request.app.state.run_store.list()
    outcomes = [
        RunOutcome(
            test_id=t.test_id,
            git_sha=run.git_sha,
            started_at=run.started_at,
            status=t.status,
        )
        for run in runs
        for t in run.tests
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
