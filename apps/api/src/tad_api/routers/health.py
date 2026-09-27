"""Liveness vs. readiness — kept deliberately distinct.

Liveness answers "is this process unrecoverable?" and must never depend on
external systems: if it did, a database blip would make Kubernetes kill and
restart every replica, turning a recoverable dependency outage into a total
one. Readiness answers "can this instance serve traffic right now?" and is
where dependency checks belong.

Phase 2 adds the real dependency check here — a Postgres connection — which
is exactly the seam this file's Phase 1 version was written to leave open.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tad_api.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/healthz")
def liveness() -> dict[str, str]:
    """Is the process itself alive? No dependency checks, ever."""
    return {"status": "ok"}


@router.get("/readyz")
async def readiness(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Can this instance serve traffic? Checks the database is reachable —
    the one real external dependency this app has as of Phase 2.
    """
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database not reachable") from exc
    return {"status": "ok"}
