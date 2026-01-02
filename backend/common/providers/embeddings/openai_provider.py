"""OpenAI embedding provider implementation."""

from typing import List, Optional
from openai import AsyncOpenAI

from common.providers.embeddings.interface import EmbeddingProviderInterface
from common.core.config import settings
from common.core.otel_axiom_exporter import trace_span
from common.providers.api_keys.rotation_provider import APIKeyRotationProvider
from common.providers.api_keys.provider_enum import APIProviderType


class OpenAIEmbeddingProvider(EmbeddingProviderInterface):
    """OpenAI embedding provider using text-embedding models with key rotation."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize OpenAI embedding provider.

        Args:
            model_name: Model to use (default: text-embedding-3-small)
        """
        self.rotator = APIKeyRotationProvider(
            keys=settings.openai_api_keys, provider_type=APIProviderType.OPENAI
        )
        self.model_name = model_name or "text-embedding-3-small"

        # Model dimension mapping
        self.dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

    @trace_span
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        api_key = self.rotator.get_next_key()
        try:
            client = AsyncOpenAI(api_key=api_key)
            response = await client.embeddings.create(input=text, model=self.model_name)
            self.rotator.report_success(api_key)
            return response.data[0].embedding
        except Exception as e:
            self.rotator.report_failure(api_key)
            raise e

    @trace_span
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        api_key = self.rotator.get_next_key()
        try:
            client = AsyncOpenAI(api_key=api_key)
            response = await client.embeddings.create(
                input=texts, model=self.model_name
            )
            self.rotator.report_success(api_key)
            return [item.embedding for item in response.data]
        except Exception as e:
            self.rotator.report_failure(api_key)
            raise e

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for current model."""
        return self.dimensions.get(self.model_name, 1536)

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model_name
