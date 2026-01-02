from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .ai_provider import AIProviderResponse


class AIModelBase(BaseModel):
    provider_id: int
    model_name: str
    display_name: str
    default_temperature: float = 0.7
    default_max_tokens: Optional[int] = None
    enabled: bool = True

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class AIModelResponse(AIModelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # Optional loaded relationships
    provider: Optional[AIProviderResponse] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )
