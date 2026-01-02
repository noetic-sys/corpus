from typing import Optional, Dict, Any

from common.core.config import settings
from .provider_enum import AIProviderType
from .aisuite_provider import AISuiteProvider
from common.providers.api_keys.rotation_provider import APIKeyRotationProvider
from common.providers.api_keys.provider_enum import (
    APIProviderType as KeyAPIProviderType,
)


class GoogleProvider(AISuiteProvider):
    """Google Gemini implementation using aisuite unified interface."""

    def __init__(self, model_name: Optional[str] = None):
        model = model_name or getattr(settings, "google_model", "gemini-2.5-flash-lite")

        # Google uses single service account credential (no rotation)
        self.google_project_id = settings.google_project_id
        self.google_region = settings.google_region
        self.google_credentials_path = settings.google_application_credentials

        # Google uses service account file, create single-item rotator
        rotator = APIKeyRotationProvider(
            keys=[settings.google_application_credentials],
            provider_type=KeyAPIProviderType.GOOGLE,
        )

        super().__init__(
            provider=AIProviderType.GOOGLE.value, model_name=model, rotator=rotator
        )

    def get_config_dict(self, rotated_key: str) -> Dict[str, Any]:
        """Get Google-specific configuration dictionary."""
        return {
            "project_id": self.google_project_id,
            "region": self.google_region,
            # Pass placeholder if no creds path - aisuite validates this but vertexai.init() will ignore it and use ADC
            "application_credentials": self.google_credentials_path
            or "workload-identity",
        }
