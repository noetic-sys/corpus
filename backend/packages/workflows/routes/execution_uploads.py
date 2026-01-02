from typing import Annotated
from io import BytesIO
import json
from fastapi import APIRouter, Depends, Path, HTTPException, UploadFile, File

from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.auth.dependencies import get_service_account
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.workflows.models.schemas.execution import (
    GenerateUploadUrlsRequest,
    GenerateUploadUrlsResponse,
    UploadFileResponse,
    UploadManifestRequest,
    UploadManifestResponse,
)
from packages.workflows.services.workflow_storage_service import WorkflowStorageService

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/workflows/{workflowId}/executions/{executionId}/upload-urls",
    response_model=GenerateUploadUrlsResponse,
)
@trace_span
async def generate_upload_urls(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    execution_id: Annotated[int, Path(alias="executionId")],
    request: GenerateUploadUrlsRequest,
    service_account: AuthenticatedUser = Depends(get_service_account),
):
    """
    Generate presigned upload URLs for execution output files.

    Called by workflow agent after completing to get URLs for uploading files + manifest.
    """
    try:
        storage_service = WorkflowStorageService()
        company_id = service_account.company_id

        upload_urls = {}

        # Generate presigned upload URL for each file
        for filename in request.filenames:
            storage_key = storage_service._get_execution_output_path(
                company_id, workflow_id, execution_id, filename
            )
            upload_url = await storage_service.storage.generate_presigned_upload_url(
                key=storage_key, expiration=3600
            )

            if not upload_url:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate upload URL for {filename}",
                )

            upload_urls[filename] = upload_url

        # Generate presigned upload URL for manifest
        manifest_key = storage_service._get_execution_manifest_path(
            company_id, workflow_id, execution_id
        )
        manifest_upload_url = (
            await storage_service.storage.generate_presigned_upload_url(
                key=manifest_key, expiration=3600
            )
        )

        if not manifest_upload_url:
            raise HTTPException(
                status_code=500, detail="Failed to generate manifest upload URL"
            )

        return GenerateUploadUrlsResponse(
            upload_urls=upload_urls, manifest_upload_url=manifest_upload_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to generate upload URLs for execution {execution_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to generate upload URLs")


@router.post(
    "/workflows/{workflowId}/executions/{executionId}/files",
    response_model=UploadFileResponse,
)
@trace_span
async def upload_execution_file(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    execution_id: Annotated[int, Path(alias="executionId")],
    file: UploadFile = File(...),
    service_account: AuthenticatedUser = Depends(get_service_account),
):
    """
    Upload an execution output file directly to storage.

    Called by workflow agent to upload files after completion.
    """
    try:
        storage_service = WorkflowStorageService()
        company_id = service_account.company_id

        # Get filename from uploaded file
        filename = file.filename
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Upload to storage
        storage_path = await storage_service.upload_execution_output(
            company_id=company_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            filename=filename,
            file_data=BytesIO(file_content),
        )

        logger.info(
            f"Uploaded file {filename} ({file_size} bytes) for execution {execution_id}"
        )

        return UploadFileResponse(
            filename=filename, size=file_size, storage_path=storage_path
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to upload file for execution {execution_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.post(
    "/workflows/{workflowId}/executions/{executionId}/manifest",
    response_model=UploadManifestResponse,
)
@trace_span
async def upload_execution_manifest(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    execution_id: Annotated[int, Path(alias="executionId")],
    request: UploadManifestRequest,
    service_account: AuthenticatedUser = Depends(get_service_account),
):
    """
    Upload execution manifest JSON to storage.

    Called by workflow agent after uploading all files.
    """
    try:
        storage_service = WorkflowStorageService()
        company_id = service_account.company_id

        # Convert manifest dict to JSON bytes

        manifest_bytes = json.dumps(request.manifest).encode("utf-8")

        # Get manifest storage path
        manifest_key = storage_service._get_execution_manifest_path(
            company_id, workflow_id, execution_id
        )

        # Upload to storage
        success = await storage_service.storage.upload(
            key=manifest_key, data=BytesIO(manifest_bytes)
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload manifest")

        logger.info(f"Uploaded manifest for execution {execution_id}")

        return UploadManifestResponse(storage_path=manifest_key, success=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to upload manifest for execution {execution_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to upload manifest: {str(e)}"
        )
