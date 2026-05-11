"""
AgroSense API — Health Check Endpoints
Used by Cloud Run, Docker health checks, and uptime monitors.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db

router = APIRouter()


@router.get("/health", summary="Basic health check")
async def health():
    """Returns 200 OK — used by Cloud Run to confirm the container is alive."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/ready", summary="Readiness check (DB + dependencies)")
async def readiness(db: AsyncSession = Depends(get_db)):
    """
    Checks that the API can reach the database.
    Cloud Run uses this before routing traffic to a new instance.
    """
    checks = {"api": "ok", "database": "unknown"}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
