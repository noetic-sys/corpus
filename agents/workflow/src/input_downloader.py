"""
Input file downloading for workflow execution.

Handles downloading input files (templates, data files) from API to workspace.
"""

from pathlib import Path

import requests


def download_input_files(api_endpoint: str, workflow_id: str, api_key: str) -> None:
    """
    Download input files (templates, data files) from API to /workspace/inputs.

    Called before agent execution starts so files are available in inputs directory.

    Args:
        api_endpoint: API base URL
        workflow_id: Workflow ID to download files for
        api_key: API key for authentication

    Raises:
        requests.HTTPError: If API request fails
    """
    inputs_dir = Path("/workspace/inputs")

    # List input files for this workflow
    list_url = f"{api_endpoint}/api/v1/workflows/{workflow_id}/input-files"
    headers = {"X-Api-Key": f"{api_key}"}

    try:
        response = requests.get(list_url, headers=headers, timeout=30)
        response.raise_for_status()
        input_files = response.json()

        if not input_files:
            print("No input files to download")
            return

        print(f"Downloading {len(input_files)} input file(s)...")

        # Download each file
        for file_info in input_files:
            file_id = file_info["id"]
            filename = file_info["name"]

            download_url = f"{api_endpoint}/api/v1/workflows/{workflow_id}/input-files/{file_id}/download"

            try:
                file_response = requests.get(
                    download_url, headers=headers, timeout=60, stream=True
                )
                file_response.raise_for_status()

                # Save to inputs directory
                file_path = inputs_dir / filename
                with open(file_path, "wb") as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                print(f"  ✓ Downloaded: {filename} ({file_info['fileSize']} bytes)")

            except Exception as e:
                print(f"  ✗ Failed to download {filename}: {e}")
                raise

        print("All input files downloaded successfully")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to list/download input files: {e}")
        raise
