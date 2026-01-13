"""Internal routes aggregator.

Routes in this module are mounted at root level (not under /api/v1).
They are not exposed via ingress - only reachable by k8s probes
hitting the pod IP directly.
"""

from fastapi import APIRouter

from internal.routes import probes

internal_router = APIRouter()

# K8s probe endpoints
internal_router.include_router(probes.router)
