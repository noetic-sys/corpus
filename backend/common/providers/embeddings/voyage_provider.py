"""Voyage AI embedding provider implementation."""

from typing import List, Optional
import httpx

from common.providers.embeddings.interface import EmbeddingProviderInterface
from common.core.config import settings
from common.providers.api_keys.rotation_provider import APIKeyRotationProvider
from common.providers.api_keys.provider_enum import APIProviderType


class VoyageEmbeddingProvider(EmbeddingProviderInterface):
    """Voyage AI embedding provider with key rotation."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize Voyage embedding provider.

        Args:
            model_name: Model to use (default: voyage-2)
        """
        if not settings.voyage_api_keys:
            raise ValueError(
                "VOYAGE_API_KEYS environment variable is required for Voyage embeddings"
            )

        self.rotator = APIKeyRotationProvider(
            keys=settings.voyage_api_keys, provider_type=APIProviderType.VOYAGE
        )
        self.model_name = model_name or "voyage-2"
        self.base_url = "https://api.voyageai.com/v1"

        # Model dimension mapping
        self.dimensions = {
            "voyage-2": 1024,
            "voyage-large-2": 1536,
            "voyage-code-2": 1536,
        }

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        api_key = self.rotator.get_next_key()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"input": texts, "model": self.model_name},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                self.rotator.report_success(api_key)
                return [item["embedding"] for item in data["data"]]
        except Exception as e:
            self.rotator.report_failure(api_key)
            raise e

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for current model."""
        return self.dimensions.get(self.model_name, 1024)

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model_name
