"""
Corpus Agent Service

Handles agent/conversation endpoints:
- WebSocket for real-time agent chat
- Conversation CRUD
- Agent loop execution
- Tool execution

This service is deployed separately from the main API service
to allow independent scaling and resource isolation.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.core.config import settings
from packages.agents.routes import router as agents_router
from internal.routes.router import internal_router
from common.db.session import init_db

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
    logger.info("Starting Corpus Agent service...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Corpus Agent service...")


# Only expose OpenAPI docs in local development
docs_url = "/docs" if settings.environment == "local" else None
redoc_url = "/redoc" if settings.environment == "local" else None
openapi_url = "/openapi.json" if settings.environment == "local" else None

app = FastAPI(
    title="Corpus Agent Service",
    version=settings.api_version,
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)
# Add ASGI middleware for context propagation
app.add_middleware(OpenTelemetryMiddleware)

# CORS - more permissive for agent service since it handles WebSocket
# nginx handles most of this, but we need it for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include agent routes (already prefixed with /agents in the router)
app.include_router(agents_router, prefix="/api/v1")

# Internal routes (k8s probes, metrics, etc.) - not under /api, so not exposed via ingress
app.include_router(internal_router, include_in_schema=False)
