from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MatrixTemplateVariableModel(BaseModel):
    id: int
    template_string: str
    value: str
    matrix_id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MatrixTemplateVariableCreateModel(BaseModel):
    """Model for creating a new matrix template variable."""

    template_string: str
    value: str
    matrix_id: int
    company_id: int


class MatrixTemplateVariableUpdateModel(BaseModel):
    """Model for updating a matrix template variable."""

    template_string: Optional[str] = None
    value: Optional[str] = None


class MatrixTemplateVariableBulkCreateModel(BaseModel):
    """Model for bulk creating/updating matrix template variables (without matrix_id and company_id)."""

    template_string: str
    value: str
