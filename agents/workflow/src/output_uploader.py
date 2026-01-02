"""
Output file uploader for workflow execution.

Uploads generated files and manifest directly via API after agent completes.
"""

import json
from pathlib import Path
from typing import List

import requests
from workflows.execution_result import ExecutionFileInfo


def upload_outputs_to_s3(
    api_endpoint: str,
    workflow_id: int,
    execution_id: int,
    api_key: str,
    output_files: List[ExecutionFileInfo],
) -> None:
    """
    Upload output files and manifest directly via API.

    Called after agent execution completes to persist results.

    Args:
        api_endpoint: API base URL
        workflow_id: Workflow ID
        execution_id: Execution ID
        api_key: Service account API key
        output_files: List of output file info objects

    Raises:
        requests.HTTPError: If API request or upload fails
    """
    if not output_files:
        print("No output files to upload")
        return

    headers = {"X-Api-Key": api_key}

    print(f"Uploading {len(output_files)} file(s) directly to API...")

    try:
        # Upload each file using multipart form data
        for file_info in output_files:
            filename = file_info.name
            file_path = Path(file_info.path)

            if not file_path.exists():
                raise FileNotFoundError(f"Output file not found: {file_path}")

            # POST file as multipart/form-data
            upload_endpoint = f"{api_endpoint}/api/v1/workflows/{workflow_id}/executions/{execution_id}/files"

            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "application/octet-stream")}
                upload_response = requests.post(
                    upload_endpoint, headers=headers, files=files, timeout=300
                )
                upload_response.raise_for_status()

            print(f"  ✓ Uploaded: {filename} ({file_info.size} bytes)")

        # Upload manifest as JSON
        manifest_path = Path("/workspace/.manifest.json")
        if not manifest_path.exists():
            raise FileNotFoundError("Manifest file not found")

        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)

        manifest_endpoint = f"{api_endpoint}/api/v1/workflows/{workflow_id}/executions/{execution_id}/manifest"
        manifest_headers = {**headers, "Content-Type": "application/json"}
        manifest_response = requests.post(
            manifest_endpoint,
            headers=manifest_headers,
            json={"manifest": manifest_data},
            timeout=60,
        )
        manifest_response.raise_for_status()

        print("  ✓ Uploaded manifest")
        print("All files uploaded successfully")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to upload files: {e}")
        raise
