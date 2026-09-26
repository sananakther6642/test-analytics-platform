"""Liveness vs. readiness — kept deliberately distinct.

Liveness answers "is this process unrecoverable?" and must never depend on
external systems: if it did, a database blip would make Kubernetes kill and
restart every replica, turning a recoverable dependency outage into a total
one. Readiness answers "can this instance serve traffic right now?" and is
where dependency checks belong.

Phase 1 has no external dependency yet (in-memory store), so readiness is
trivially always-ready — this file is the seam where Phase 2 plugs in a real
`await db.execute("SELECT 1")` without touching liveness at all.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def liveness() -> dict[str, str]:
    """Is the process itself alive? No dependency checks, ever."""
    return {"status": "ok"}


@router.get("/readyz")
def readiness() -> dict[str, str]:
    """Can this instance serve traffic? Checks dependencies (Phase 2+)."""
    return {"status": "ok"}
