from typing import List, Annotated
from fastapi import APIRouter, Depends, Path

from packages.ai_model.models.schemas.ai_provider import AIProviderResponse
from packages.ai_model.models.schemas.ai_model import AIModelResponse
from packages.ai_model.services.ai_model_service import AIModelService
from common.core.otel_axiom_exporter import trace_span
from common.db.context import readonly

router = APIRouter()


def get_ai_model_service() -> AIModelService:
    return AIModelService()


@router.get("/providers", response_model=List[AIProviderResponse])
@readonly
@trace_span
async def get_available_providers(
    service: AIModelService = Depends(get_ai_model_service),
):
    """Get all enabled AI providers for frontend selection menus."""
    return await service.get_enabled_providers()


@router.get("/models", response_model=List[AIModelResponse])
@readonly
@trace_span
async def get_available_models(
    service: AIModelService = Depends(get_ai_model_service),
):
    """Get all enabled AI models with provider info for frontend selection menus."""
    return await service.get_enabled_models()


@router.get("/providers/{providerId}/models", response_model=List[AIModelResponse])
@readonly
@trace_span
async def get_models_for_provider(
    provider_id: Annotated[int, Path(alias="providerId")],
    service: AIModelService = Depends(get_ai_model_service),
):
    """Get all enabled AI models for a specific provider for frontend selection menus."""
    return await service.get_enabled_models_by_provider(provider_id)
