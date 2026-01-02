from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class AIProviderBase(BaseModel):
    name: str
    display_name: str
    enabled: bool = True

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class AIProviderResponse(AIProviderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )
