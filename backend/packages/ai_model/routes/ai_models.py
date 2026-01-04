from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from packages.ai_model.models.schemas.ai_provider import (
    AIProviderResponse,
)
from packages.ai_model.models.schemas.ai_model import (
    AIModelResponse,
)
from packages.ai_model.services.ai_model_service import AIModelService
from common.core.otel_axiom_exporter import get_logger
from common.db.context import readonly

router = APIRouter()
logger = get_logger(__name__)


def get_ai_model_service() -> AIModelService:
    return AIModelService()


@router.get("/providers/", response_model=List[AIProviderResponse])
@readonly
async def get_ai_providers(
    enabled_only: bool = False,
    service: AIModelService = Depends(get_ai_model_service),
):
    """Get all AI providers, optionally filtered to enabled only."""
    if enabled_only:
        return await service.get_enabled_providers()
    return await service.get_all_providers()


@router.get("/providers/{providerId}", response_model=AIProviderResponse)
@readonly
async def get_ai_provider(
    provider_id: int = Path(alias="providerId"),
    service: AIModelService = Depends(get_ai_model_service),
):
    """Get an AI provider by ID."""
    provider = await service.get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider not found")
    return provider


@router.get("/models/", response_model=List[AIModelResponse])
@readonly
async def get_ai_models(
    enabled_only: bool = Query(default=False, alias="enabledOnly"),
    service: AIModelService = Depends(get_ai_model_service),
):
    """Get all AI models, optionally filtered by enabled status."""
    if enabled_only:
        return await service.get_enabled_models()
    return await service.get_all_models()


@router.get("/providers/{providerId}/models/", response_model=List[AIModelResponse])
@readonly
async def get_models_by_provider(
    provider_id: Annotated[int, Path(alias="providerId")],
    enabled_only: bool = Query(default=False, alias="enabledOnly"),
    service: AIModelService = Depends(get_ai_model_service),
):
    """Get AI models for a specific provider, optionally filtered by enabled status."""
    # Verify provider exists
    provider = await service.get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider not found")

    if enabled_only:
        return await service.get_enabled_models_by_provider(provider_id)
    return await service.get_models_by_provider(provider_id)


@router.get("/models/{modelId}", response_model=AIModelResponse)
@readonly
async def get_ai_model(
    model_id: Annotated[int, Path(alias="modelId")],
    service: AIModelService = Depends(get_ai_model_service),
):
    """Get an AI model by ID with provider information."""
    model = await service.get_model_with_provider(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="AI model not found")
    return model
