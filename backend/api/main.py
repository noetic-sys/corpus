import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from common.core.config import settings
from api.v1.routes.router import api_router
from common.db.session import init_db
from common.providers.rate_limiter.limiter import limiter

# Initialize Axiom OpenTelemetry exporter (must be first)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from common.core.otel_axiom_exporter import (
    _initialize_telemetry,
    get_logger,
)  # noqa


_initialize_telemetry()
# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down application...")


# Only expose OpenAPI docs in local development
docs_url = "/docs" if settings.environment == "local" else None
redoc_url = "/redoc" if settings.environment == "local" else None
openapi_url = "/openapi.json" if settings.environment == "local" else None

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)
# Add ASGI middleware for context propagation
app.add_middleware(OpenTelemetryMiddleware)

# Add gzip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (auth enforced via dependencies at router level)
app.include_router(api_router, prefix="/api/v1")


# Internal health endpoint for k8s probes - not under /api/v1 to avoid external spam
# K8s probes hit pod IPs directly, but this also reduces visibility to scanners
@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}
