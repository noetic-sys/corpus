from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from common.db.session import get_db
from common.core.otel_axiom_exporter import get_logger, log_span_event
from common.providers.rate_limiter.limiter import limiter

logger = get_logger(__name__)

router = APIRouter()


@router.get("/")
async def health_check(request: Request):
    # No rate limiting or logging - k8s probes hit this every 5-10s
    return {"status": "healthy", "service": "corpus-service"}


@router.get("/db")
@limiter.limit("100/minute")
async def db_check(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected"}
