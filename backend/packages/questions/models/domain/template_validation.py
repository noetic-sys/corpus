from __future__ import annotations

from typing import List, Dict
from pydantic import BaseModel


class TemplateVariableValidationModel(BaseModel):
    """Model for template variable validation results."""

    template_variable_id: int
    exists: bool


class TemplateVariableValidationResultModel(BaseModel):
    """Model for template variable validation results."""

    validations: List[TemplateVariableValidationModel]

    def to_dict(self) -> Dict[int, bool]:
        """Convert to dictionary for backwards compatibility."""
        return {v.template_variable_id: v.exists for v in self.validations}


class TemplatePreviewModel(BaseModel):
    """Model for template variable preview results."""

    original: str
    resolved: str
    variables_used: List[int]


class QuestionTemplateValidationModel(BaseModel):
    """Model for template variable validation results."""

    question_id: int
    variables_in_text: List[str]
    associated_variables: List[str]
    missing_associations: List[str]
    extra_associations: List[str]
    is_valid: bool

    model_config = {"from_attributes": True}
