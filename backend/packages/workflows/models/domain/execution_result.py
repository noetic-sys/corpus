"""
Domain models for workflow execution results.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ExecutionFileInfo(BaseModel):
    """Information about a file generated during execution."""

    name: str = Field(..., description="Filename")
    relative_path: str = Field(..., description="Path relative to outputs/ or scratch/")
    size: int = Field(..., description="File size in bytes")
    path: str = Field(..., description="Absolute path in container")


class ExecutionFiles(BaseModel):
    """Files generated during workflow execution."""

    outputs: List[ExecutionFileInfo] = Field(
        default_factory=list, description="Final deliverable files"
    )
    scratch: List[ExecutionFileInfo] = Field(
        default_factory=list, description="Working/debug files"
    )


class ExecutionMetadata(BaseModel):
    """Metadata about the execution."""

    success: bool
    error: Optional[str] = None
    cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None


class ExecutionManifest(BaseModel):
    """Complete manifest of workflow execution results."""

    execution_id: int
    output_files: List[ExecutionFileInfo] = Field(default_factory=list)
    scratch_files: List[ExecutionFileInfo] = Field(default_factory=list)
    metadata: ExecutionMetadata
