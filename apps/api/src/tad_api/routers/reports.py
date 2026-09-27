"""Upload and retrieve test-run reports."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from tad_api.parsers.base import ParseError
from tad_api.parsers.registry import get_parser
from tad_api.storage.base import RunStore
from tad_api.storage.dependency import get_run_store

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("")
async def upload_report(
    file: UploadFile, run_store: RunStore = Depends(get_run_store)
) -> dict:
    raw = await file.read()
    parser = get_parser(file.filename or "", file.content_type)

    try:
        run = parser.parse(raw)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await run_store.add(run)
    return {"run_id": run.run_id, "test_count": len(run.tests)}


@router.get("")
async def list_reports(run_store: RunStore = Depends(get_run_store)) -> list[dict]:
    return [
        {"run_id": r.run_id, "suite_name": r.suite_name, "started_at": r.started_at}
        for r in await run_store.list()
    ]


@router.get("/{run_id}")
async def get_report(run_id: str, run_store: RunStore = Depends(get_run_store)) -> dict:
    run = await run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No report with run_id '{run_id}'")
    return {
        "run_id": run.run_id,
        "suite_name": run.suite_name,
        "git_sha": run.git_sha,
        "branch": run.branch,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "environment": run.environment,
        "tests": [
            {
                "test_id": t.test_id,
                "name": t.name,
                "status": t.status,
                "duration_ms": t.duration_ms,
            }
            for t in run.tests
        ],
    }
