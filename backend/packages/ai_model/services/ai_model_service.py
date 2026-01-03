from typing import List, Optional

from packages.ai_model.repositories.ai_provider_repository import AIProviderRepository
from packages.ai_model.repositories.ai_model_repository import AIModelRepository
from packages.ai_model.models.domain.ai_provider import (
    AIProviderModel,
)
from packages.ai_model.models.domain.ai_model import (
    AIModelModel,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class AIModelService:
    """Service for handling AI provider and model operations."""

    def __init__(self):
        self.provider_repo = AIProviderRepository()
        self.model_repo = AIModelRepository()

    @trace_span
    async def get_provider(self, provider_id: int) -> Optional[AIProviderModel]:
        """Get an AI provider by ID."""
        return await self.provider_repo.get(provider_id)

    @trace_span
    async def get_provider_by_name(self, name: str) -> Optional[AIProviderModel]:
        """Get an AI provider by name."""
        return await self.provider_repo.get_by_name(name)

    @trace_span
    async def get_all_providers(self) -> List[AIProviderModel]:
        """Get all AI providers."""
        return await self.provider_repo.get_multi()

    @trace_span
    async def get_enabled_providers(self) -> List[AIProviderModel]:
        """Get all enabled AI providers."""
        return await self.provider_repo.get_enabled()

    @trace_span
    async def get_model(self, model_id: int) -> Optional[AIModelModel]:
        """Get an AI model by ID."""
        return await self.model_repo.get(model_id)

    @trace_span
    async def get_model_with_provider(self, model_id: int) -> Optional[AIModelModel]:
        """Get an AI model by ID with provider information loaded."""
        return await self.model_repo.get_with_provider(model_id)

    @trace_span
    async def get_all_models(self) -> List[AIModelModel]:
        """Get all AI models."""
        return await self.model_repo.get_multi()

    @trace_span
    # TODO: expensive ass join for no reason
    async def get_enabled_models(self) -> List[AIModelModel]:
        """Get all enabled AI models with provider information."""
        models = await self.model_repo.get_enabled()
        return models

    @trace_span
    async def get_models_by_provider(self, provider_id: int) -> List[AIModelModel]:
        """Get all AI models for a specific provider."""
        return await self.model_repo.get_by_provider_id(provider_id)

    @trace_span
    async def get_enabled_models_by_provider(
        self, provider_id: int
    ) -> List[AIModelModel]:
        """Get all enabled AI models for a specific provider."""
        return await self.model_repo.get_enabled_by_provider_id(provider_id)
