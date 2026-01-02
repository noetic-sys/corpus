from typing import TypeVar, Type
from pydantic import BaseModel

SourceType = TypeVar("SourceType", bound=BaseModel)
TargetType = TypeVar("TargetType", bound=BaseModel)


def map_preserving_fields_set(
    source: SourceType, target_class: Type[TargetType]
) -> TargetType:
    """Map from source model to target model, preserving only fields that were set.

    This ensures that only fields that were explicitly provided in the source model
    are included in the target model, which is crucial for partial updates where
    we need to distinguish between 'not provided' and 'explicitly set to None'.

    Args:
        source: The source Pydantic model instance
        target_class: The target Pydantic model class to create

    Returns:
        Instance of target_class with only the fields that were set in source
    """
    # Use model_dump with exclude_unset to get only the fields that were set
    data = source.model_dump(exclude_unset=True)
    return target_class(**data)
