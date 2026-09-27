"""Upload and retrieve test-run reports."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from tad_api.parsers.base import ParseError
from tad_api.parsers.registry import get_parser
from tad_api.storage.base import RunStore
from tad_api.storage.blob import ReportBlobStore
from tad_api.storage.dependency import get_blob_store, get_run_store

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("")
async def upload_report(
    file: UploadFile,
    run_store: RunStore = Depends(get_run_store),
    blob_store: ReportBlobStore = Depends(get_blob_store),
) -> dict:
    raw = await file.read()
    parser = get_parser(file.filename or "", file.content_type)

    try:
        run = parser.parse(raw)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Blob save happens after a successful parse, not before: an
    # unparseable upload shouldn't leave an orphaned blob with no
    # corresponding run_id anyone can look up. Parsed-data storage
    # (Postgres) is still the source of truth for whether an upload
    # "succeeded" — the raw blob is retained evidence, not required for
    # the API to function if it's ever briefly unavailable.
    await run_store.add(run)
    await blob_store.save(run.run_id, raw)
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
