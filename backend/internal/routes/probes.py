"""Kubernetes probe endpoints.

These endpoints are internal-only - not exposed via ingress.
Ingress only routes /api/* paths, so these root-level paths are only
reachable by k8s probes hitting the pod IP directly.
"""

from fastapi import APIRouter

router = APIRouter(tags=["internal"])


@router.get("/healthz")
async def healthz():
    """Liveness probe - is the process alive?"""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz():
    """Readiness probe - is the service ready to receive traffic?"""
    # TODO: Add checks for dependencies (db, redis, etc.) if needed
    return {"status": "ok"}
