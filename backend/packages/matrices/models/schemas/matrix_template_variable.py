from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class MatrixTemplateVariableCreate(BaseModel):
    """Schema for creating a matrix template variable."""

    template_string: str = Field(
        ..., description="Template variable name (e.g., 'company_name')"
    )
    value: str = Field(..., description="Value to substitute for the template variable")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixTemplateVariableUpdate(BaseModel):
    """Schema for updating a matrix template variable."""

    template_string: Optional[str] = Field(None, description="Template variable name")
    value: Optional[str] = Field(
        None, description="Value to substitute for the template variable"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixTemplateVariableResponse(BaseModel):
    """Schema for matrix template variable responses."""

    id: int
    template_string: str
    value: str
    matrix_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


class MatrixTemplateVariableBulkCreate(BaseModel):
    """Schema for bulk creating/updating template variables."""

    variables: List[dict] = Field(
        ...,
        description="List of template variables with 'template_string' and 'value' keys",
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class TemplateVariableUsageResponse(BaseModel):
    """Schema for template variable with usage information."""

    variable: MatrixTemplateVariableResponse
    usage_count: int = Field(..., description="Number of questions using this variable")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class TemplateValidationResponse(BaseModel):
    """Schema for template variable validation."""

    question_id: int
    variables_in_text: List[str]
    associated_variables: List[str]
    missing_associations: List[str]
    extra_associations: List[str]
    is_valid: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )
