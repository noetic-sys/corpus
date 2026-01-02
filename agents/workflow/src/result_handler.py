"""
Result handling for workflow execution.

Handles file listing, manifest generation, and result processing.
"""

import json
from pathlib import Path
from typing import List

from workflows.execution_result import (
    ExecutionFileInfo,
    ExecutionFiles,
    ExecutionManifest,
    ExecutionMetadata,
)


def list_generated_files() -> ExecutionFiles:
    """
    List all files generated in workspace, separated by type.

    Returns:
        ExecutionFiles with outputs and scratch file lists
    """
    outputs_dir = Path("/workspace/outputs")
    scratch_dir = Path("/workspace/scratch")

    def list_files_in_dir(directory: Path) -> List[ExecutionFileInfo]:
        """List all files in a directory recursively."""
        files = []
        if not directory.exists():
            return files

        for file_path in directory.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                files.append(
                    ExecutionFileInfo(
                        name=file_path.name,
                        relative_path=str(file_path.relative_to(directory)),
                        size=file_path.stat().st_size,
                        path=str(file_path),
                    )
                )
        return files

    return ExecutionFiles(
        outputs=list_files_in_dir(outputs_dir), scratch=list_files_in_dir(scratch_dir)
    )


def write_manifest(
    execution_id: int, files: ExecutionFiles, metadata: ExecutionMetadata
) -> None:
    """
    Write execution manifest to workspace.

    Args:
        execution_id: Execution ID (integer from database)
        files: ExecutionFiles with outputs and scratch
        metadata: ExecutionMetadata with success, error, cost, duration
    """
    manifest = ExecutionManifest(
        execution_id=execution_id,
        output_files=files.outputs,
        scratch_files=files.scratch,
        metadata=metadata,
    )

    manifest_path = Path("/workspace/.manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest.model_dump(), f, indent=2)

    print(f"Manifest written to {manifest_path}")
