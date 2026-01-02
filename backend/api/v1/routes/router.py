from fastapi import APIRouter, Depends

from api.v1.routes import (
    health,
)
from packages.qa.routes import qa
from packages.matrices.routes import matrix_template_variables, matrices, entity_sets
from packages.workspaces.routes import workspaces
from packages.questions.routes import questions, question_types
from packages.documents.routes import documents, document_extraction, chunks
from packages.ai_model.routes import ai_selection, ai_models
from packages.agents.routes import router as agents_router
from packages.workflows.routes import workflows, execution_uploads
from packages.users.routes import protected
from packages.auth.dependencies import get_current_active_user, get_subscribed_user
from packages.billing.routes import billing, webhooks, plans

api_router = APIRouter()

# Health check (no auth required)
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Webhooks (no auth - signature verified internally)
api_router.include_router(webhooks.router, tags=["webhooks"])

# Plans (no auth - public pricing info)
api_router.include_router(plans.router, prefix="/billing/plans", tags=["billing"])

# Protected routes (require auth + active subscription)
api_router.include_router(
    protected.router,
    prefix="/auth",
    tags=["protected"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    workspaces.router,
    prefix="/workspaces",
    tags=["workspaces"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    documents.router,
    tags=["documents"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    questions.router,
    tags=["questions"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    question_types.router,
    tags=["question-types"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    matrices.router, tags=["matrices"], dependencies=[Depends(get_subscribed_user)]
)
api_router.include_router(
    entity_sets.router,
    tags=["entity-sets"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    matrix_template_variables.router,
    tags=["matrix-template-variables"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    qa.router, tags=["qa"], dependencies=[Depends(get_subscribed_user)]
)
api_router.include_router(
    document_extraction.router,
    tags=["document-extraction"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    chunks.router,
    tags=["chunks"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    ai_models.router,
    prefix="/admin",
    tags=["ai-models-admin"],
    dependencies=[Depends(get_subscribed_user)],
)
api_router.include_router(
    ai_selection.router,
    prefix="/ai",
    tags=["ai-selection"],
    dependencies=[Depends(get_subscribed_user)],
)

# Workflows router
api_router.include_router(
    workflows.router,
    tags=["workflows"],
    dependencies=[Depends(get_subscribed_user)],
)

# Execution uploads router - service account auth (called by agent)
api_router.include_router(
    execution_uploads.router,
    tags=["execution-uploads"],
)

# Agents router - auth handled internally (note: websocket auth handled at endpoint level)
api_router.include_router(agents_router)

# Billing routes (require auth)
api_router.include_router(
    billing.router,
    prefix="/billing",
    tags=["billing"],
    dependencies=[Depends(get_current_active_user)],
)
