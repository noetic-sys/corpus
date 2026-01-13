from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Path
from fastapi.responses import Response

from common.db.scoped import transaction
from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.billing.services.quota_service import QuotaService
from packages.billing.services.usage_service import UsageService
from packages.documents.models.schemas.document import (
    DocumentResponse,
    DocumentLabelUpdate,
    MatrixDocumentResponse,
    DocumentListResponse,
    SupportedExtensionsResponse,
    BulkUrlUploadRequest,
    BulkUrlUploadResponse,
    HybridDocumentSearchResponse,
    DocumentSearchHitResponse,
    DocumentMatchSnippetResponse,
    DocumentUploadOptions,
)
from packages.documents.models.domain.document import ExtractionStatus
from packages.matrices.services.batch_processing_service import (
    get_batch_processing_service,
)
from packages.matrices.services.entity_set_service import get_entity_set_service
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixEntitySetMemberCreateModel,
)
from packages.matrices.models.domain.matrix_enums import EntityType
from packages.questions.services.question_service import get_question_service
from packages.documents.services.temporal_document_extraction_service import (
    get_temporal_document_extraction_service,
)
from packages.documents.services.document_highlighting_service import (
    get_document_highlighting_service,
)
from packages.documents.services.document_service import get_document_service
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.providers.storage.factory import get_storage

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/documents/supported-extensions", response_model=SupportedExtensionsResponse
)
async def get_supported_file_extensions():
    """Get all supported file extensions for document uploads."""
    document_service = get_document_service(None)  # Static method, no DB needed
    return SupportedExtensionsResponse(
        extensions=document_service.get_supported_file_extensions(), max_file_size_mb=10
    )


@router.get("/documents/", response_model=DocumentListResponse)
async def list_documents(
    content_type: Optional[str] = Query(
        None, description="Filter by content type", alias="contentType"
    ),
    extraction_status: Optional[str] = Query(
        None, description="Filter by extraction status", alias="extractionStatus"
    ),
    created_after: Optional[str] = Query(
        None, description="Filter by created after (ISO format)", alias="createdAfter"
    ),
    created_before: Optional[str] = Query(
        None, description="Filter by created before (ISO format)", alias="createdBefore"
    ),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of documents to return"
    ),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """List all documents with optional filters and pagination."""
    document_service = get_document_service()

    result = await document_service.list_all_documents(
        company_id=current_user.company_id,
        content_type=content_type,
        extraction_status=extraction_status,
        created_after=created_after,
        created_before=created_before,
        skip=skip,
        limit=limit,
    )

    # Convert domain models to response schemas
    document_responses = [
        DocumentResponse.model_validate(doc) for doc in result.documents
    ]

    return DocumentListResponse(
        documents=document_responses,
        total_count=result.total_count,
        skip=skip,
        limit=limit,
        has_more=result.has_more,
    )


@router.get("/documents/search", response_model=DocumentListResponse)
async def search_documents(
    q: Optional[str] = Query(
        None, description="Search query to match against document filename"
    ),
    content_type: Optional[str] = Query(
        None, description="Filter by content type", alias="contentType"
    ),
    extraction_status: Optional[str] = Query(
        None, description="Filter by extraction status", alias="extractionStatus"
    ),
    created_after: Optional[str] = Query(
        None, description="Filter by created after (ISO format)", alias="createdAfter"
    ),
    created_before: Optional[str] = Query(
        None, description="Filter by created before (ISO format)", alias="createdBefore"
    ),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of documents to return"
    ),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Search documents with optional query and filters."""
    document_service = get_document_service()

    result = await document_service.search_documents(
        company_id=current_user.company_id,
        query=q,
        content_type=content_type,
        extraction_status=extraction_status,
        created_after=created_after,
        created_before=created_before,
        skip=skip,
        limit=limit,
    )

    # Convert domain models to response schemas
    document_responses = [
        DocumentResponse.model_validate(doc) for doc in result.documents
    ]

    return DocumentListResponse(
        documents=document_responses,
        total_count=result.total_count,
        skip=skip,
        limit=limit,
        has_more=result.has_more,
    )


@router.get("/documents/search/hybrid", response_model=HybridDocumentSearchResponse)
async def hybrid_search_documents(
    q: str = Query(..., description="Search query (filename + content + semantic)"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    snippets_per_doc: int = Query(
        3, ge=1, le=10, description="Max snippets per document", alias="snippetsPerDoc"
    ),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Hybrid document search combining filename, BM25 content, and semantic vector search."""
    document_service = get_document_service()

    result = await document_service.hybrid_search_documents(
        company_id=current_user.company_id,
        query=q,
        skip=skip,
        limit=limit,
        snippets_per_doc=snippets_per_doc,
    )

    # Convert domain models to response schemas
    hit_responses = [
        DocumentSearchHitResponse(
            document=DocumentResponse.model_validate(hit.document),
            match_score=hit.match_score,
            match_type=hit.match_type.value,
            snippets=[
                DocumentMatchSnippetResponse(
                    chunk_id=s.chunk_id,
                    content=s.content,
                    score=s.score,
                    metadata=s.metadata,
                )
                for s in hit.snippets
            ],
        )
        for hit in result.results
    ]

    return HybridDocumentSearchResponse(
        results=hit_responses,
        total_count=result.total_count,
        skip=skip,
        limit=limit,
        has_more=result.has_more,
    )


# TODO: do these routes belong in matrix?
@router.post("/matrices/{matrixId}/documents/", response_model=DocumentResponse)
async def upload_document(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    entity_set_id: Annotated[
        int, Query(alias="entitySetId", description="Entity set ID to add document to")
    ],
    use_agentic_chunking: Annotated[
        bool,
        Query(
            alias="useAgenticChunking",
            description="Whether to use AI-powered chunking",
        ),
    ] = False,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    async with transaction():
        # Require file size for quota enforcement
        if file.size is None:
            raise HTTPException(status_code=400, detail="File size required")

        quota_service = QuotaService()

        # Check document count quota first
        await quota_service.check_document_quota(company_id=current_user.company_id)

        # Check storage quota before upload
        quota_check = await quota_service.check_storage_quota(
            company_id=current_user.company_id, file_size_bytes=file.size
        )

        if not quota_check.allowed:
            raise HTTPException(status_code=402, detail=quota_check.get_user_message())

        # these should be dependencies
        document_service = get_document_service()
        question_service = get_question_service()
        batch_processing_service = get_batch_processing_service()
        entity_set_service = get_entity_set_service()
        member_repo = EntitySetMemberRepository()

        # Upload document as standalone entity
        options = DocumentUploadOptions(use_agentic_chunking=use_agentic_chunking)
        document, is_duplicate = await document_service.upload_document(
            file, current_user.company_id, options
        )

        # Track usage for billing (skip if duplicate)
        if not is_duplicate:
            usage_service = UsageService()
            await usage_service.track_storage_upload(
                company_id=current_user.company_id,
                file_size_bytes=file.size,
                user_id=current_user.user_id,
                document_id=document.id,
            )

        # Validate the specified entity set exists and is a document type
        document_entity_set = await entity_set_service.get_entity_set(
            entity_set_id, current_user.company_id
        )
        if not document_entity_set:
            raise HTTPException(
                status_code=404, detail=f"Entity set {entity_set_id} not found"
            )

        if document_entity_set.entity_type != EntityType.DOCUMENT:
            raise HTTPException(
                status_code=400,
                detail=f"Entity set {entity_set_id} is not a document entity set (type: {document_entity_set.entity_type})",
            )

        if document_entity_set.matrix_id != matrix_id:
            raise HTTPException(
                status_code=400,
                detail=f"Entity set {entity_set_id} does not belong to matrix {matrix_id}",
            )

        # Check if document is already a member
        existing_member = await member_repo.get_member_by_entity_id(
            document_entity_set.id,
            document.id,
            EntityType.DOCUMENT,
            current_user.company_id,
        )

        if not existing_member:
            # Get current max order
            existing_members = await member_repo.get_by_entity_set_id(
                document_entity_set.id, current_user.company_id
            )
            next_order = len(existing_members)

            # Add document as member of document entity set
            member_create = MatrixEntitySetMemberCreateModel(
                entity_set_id=document_entity_set.id,
                entity_id=document.id,
                entity_type=EntityType.DOCUMENT,
                member_order=next_order,
                company_id=current_user.company_id,
            )
            await member_repo.add_member(member_create)
            logger.info(
                f"Added document {document.id} to entity set {document_entity_set.id}"
            )

        # Create matrix cells for the new document
        logger.info(
            f"Creating cells for document {document.id} in entity set {document_entity_set.id}"
        )
        created_cells, _ = await batch_processing_service.process_entity_added_to_set(
            matrix_id=matrix_id,
            entity_id=document.id,
            entity_set_id=document_entity_set.id,
            create_qa_jobs=False,  # Jobs created after extraction completes (or immediately for duplicates)
        )

        # Check if document is duplicate AND already extracted
        if is_duplicate and document.extraction_status == ExtractionStatus.COMPLETED:
            logger.info(
                f"Document {document.id} is duplicate and already extracted, "
                f"creating QA jobs immediately for {len(created_cells)} cells"
            )
            # Document already extracted, create and queue QA jobs immediately
            if created_cells:
                queued_count = (
                    await batch_processing_service.create_jobs_and_queue_for_cells(
                        created_cells
                    )
                )
                logger.info(
                    f"Queued {queued_count} QA jobs for duplicate document {document.id}"
                )
        else:
            # Document needs extraction, start Temporal workflow
            temporal_extraction_service = get_temporal_document_extraction_service()
            logger.info(
                f"Starting Temporal workflow for document {document.id} "
                f"(duplicate={is_duplicate}, status={document.extraction_status}, type={document.content_type})"
            )
            job = await temporal_extraction_service.create_and_start_workflow(document)
            if job:
                logger.info(
                    f"Document {document.id} started Temporal workflow with job {job.id}"
                )
            else:
                logger.warning(
                    f"Document {document.id} not supported for Temporal extraction or failed to start workflow"
                )

        return DocumentResponse.model_validate(document)


@router.post(
    "/matrices/{matrixId}/documents/from-urls/", response_model=BulkUrlUploadResponse
)
async def upload_documents_from_urls(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    entity_set_id: Annotated[
        int, Query(alias="entitySetId", description="Entity set ID to add documents to")
    ],
    request: BulkUrlUploadRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Upload multiple documents from URLs to a matrix."""
    quota_service = QuotaService()

    # Check document count quota first (per URL)
    # Note: This is a pre-check - actual count enforcement happens per-document
    await quota_service.check_document_quota(company_id=current_user.company_id)

    # Check storage quota before bulk upload
    # For URL uploads, we can't know file size upfront
    # Use file_size_bytes=0 to at least verify subscription is active and not over quota
    quota_check = await quota_service.check_storage_quota(
        company_id=current_user.company_id,
        file_size_bytes=0,  # Will track actual size after download
    )

    if not quota_check.allowed:
        raise HTTPException(status_code=402, detail=quota_check.get_user_message())

    document_service = get_document_service()
    entity_set_service = get_entity_set_service()
    batch_processing_service = get_batch_processing_service()
    member_repo = EntitySetMemberRepository()
    temporal_extraction_service = get_temporal_document_extraction_service()

    # Validate entity set
    document_entity_set = await entity_set_service.get_entity_set(
        entity_set_id, current_user.company_id
    )
    if not document_entity_set:
        raise HTTPException(
            status_code=404, detail=f"Entity set {entity_set_id} not found"
        )
    if document_entity_set.entity_type != EntityType.DOCUMENT:
        raise HTTPException(
            status_code=400,
            detail=f"Entity set {entity_set_id} is not a document entity set",
        )
    if document_entity_set.matrix_id != matrix_id:
        raise HTTPException(
            status_code=400,
            detail=f"Entity set {entity_set_id} does not belong to matrix {matrix_id}",
        )

    # Download and upload documents (happens outside transaction)
    # Use default options (no agentic chunking) for bulk URL uploads
    urls_list = [str(url) for url in request.urls]
    default_options = DocumentUploadOptions()
    uploaded_documents, upload_errors = (
        await document_service.upload_documents_from_urls(
            urls_list, current_user.company_id, default_options
        )
    )

    # Now handle matrix associations inside transaction
    async with transaction():
        response_documents = []

        for document in uploaded_documents:
            try:
                # Add to entity set if not already a member
                existing_member = await member_repo.get_member_by_entity_id(
                    document_entity_set.id,
                    document.id,
                    EntityType.DOCUMENT,
                    current_user.company_id,
                )

                if not existing_member:
                    existing_members = await member_repo.get_by_entity_set_id(
                        document_entity_set.id, current_user.company_id
                    )
                    next_order = len(existing_members)

                    member_create = MatrixEntitySetMemberCreateModel(
                        entity_set_id=document_entity_set.id,
                        entity_id=document.id,
                        entity_type=EntityType.DOCUMENT,
                        member_order=next_order,
                        company_id=current_user.company_id,
                    )
                    await member_repo.add_member(member_create)

                # Create matrix cells
                created_cells, _ = (
                    await batch_processing_service.process_entity_added_to_set(
                        matrix_id=matrix_id,
                        entity_id=document.id,
                        entity_set_id=document_entity_set.id,
                        create_qa_jobs=False,
                    )
                )

                # Handle extraction workflow
                if document.extraction_status == ExtractionStatus.COMPLETED:
                    if created_cells:
                        await batch_processing_service.create_jobs_and_queue_for_cells(
                            created_cells
                        )
                else:
                    await temporal_extraction_service.create_and_start_workflow(
                        document
                    )

                response_documents.append(DocumentResponse.model_validate(document))

            except Exception as e:
                logger.error(
                    f"Error associating document {document.id} with matrix: {e}"
                )
                upload_errors.append(f"Document {document.filename}: {str(e)}")

    return BulkUrlUploadResponse(documents=response_documents, errors=upload_errors)


@router.post("/documents/", response_model=DocumentResponse)
async def upload_standalone_document(
    use_agentic_chunking: Annotated[
        bool,
        Query(
            alias="useAgenticChunking",
            description="Whether to use AI-powered chunking",
        ),
    ] = False,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Upload a document without associating it with any matrix."""
    async with transaction():
        # Require file size for quota enforcement
        if file.size is None:
            raise HTTPException(status_code=400, detail="File size required")

        quota_service = QuotaService()

        # Check document count quota first
        await quota_service.check_document_quota(company_id=current_user.company_id)

        # Check storage quota before upload
        quota_check = await quota_service.check_storage_quota(
            company_id=current_user.company_id, file_size_bytes=file.size
        )

        if not quota_check.allowed:
            raise HTTPException(status_code=402, detail=quota_check.get_user_message())

        document_service = get_document_service()

        # Upload document as standalone entity
        options = DocumentUploadOptions(use_agentic_chunking=use_agentic_chunking)
        document, is_duplicate = await document_service.upload_document(
            file, current_user.company_id, options
        )

        # Track usage for billing (skip if duplicate)
        if not is_duplicate:
            usage_service = UsageService()
            await usage_service.track_storage_upload(
                company_id=current_user.company_id,
                file_size_bytes=file.size,
                user_id=current_user.user_id,
                document_id=document.id,
            )

        # Start extraction workflow
        temporal_extraction_service = get_temporal_document_extraction_service()

        logger.info(
            f"Using Temporal workflow for standalone document {document.id} (type: {document.content_type})"
        )
        job = await temporal_extraction_service.create_and_start_workflow(document)
        if job:
            logger.info(
                f"Standalone document {document.id} started Temporal workflow with job {job.id}"
            )
        else:
            logger.warning(
                f"Standalone document {document.id} not supported for Temporal extraction or failed to start workflow"
            )

        return DocumentResponse.model_validate(document)


@router.get(
    "/documents/{documentId}",
    response_model=DocumentResponse,
    tags=["workflow-agent"],
    operation_id="get_document",
)
async def get_document(
    document_id: Annotated[int, Path(alias="documentId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    document_service = get_document_service()
    document = await document_service.get_document(document_id, current_user.company_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/documents/{documentId}/content")
async def get_document_content(
    document_id: Annotated[int, Path(alias="documentId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Get extracted content for a document (for chunking agent)."""
    document_service = get_document_service()
    document = await document_service.get_document(document_id, current_user.company_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.extracted_content_path:
        raise HTTPException(
            status_code=404, detail="Document has not been extracted yet"
        )

    # Download extracted content from S3
    storage = get_storage()
    content_bytes = await storage.download(document.extracted_content_path)

    if not content_bytes:
        raise HTTPException(
            status_code=404, detail="Extracted content not found in storage"
        )

    content = content_bytes.decode("utf-8")

    return {"content": content}


@router.delete("/documents/{documentId}")
async def delete_document(
    document_id: Annotated[int, Path(alias="documentId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    document_service = get_document_service()
    success = await document_service.delete_document(
        document_id, current_user.company_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}


@router.get(
    "/matrices/{matrixId}/documents/",
    response_model=List[MatrixDocumentResponse],
    tags=["workflow-agent"],
    operation_id="get_documents_by_matrix",
)
@trace_span
async def get_documents_by_matrix(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Get all documents for a specific matrix through entity set membership."""
    entity_set_service = get_entity_set_service()
    document_service = get_document_service()

    # Get all document members across all document entity sets
    all_members = await entity_set_service.get_all_members_by_type(
        matrix_id, EntityType.DOCUMENT, current_user.company_id
    )

    if not all_members:
        return []

    # Batch fetch all documents by IDs
    document_ids = [member.entity_id for member in all_members]
    documents = await document_service.get_documents_by_ids(
        document_ids, current_user.company_id
    )

    # Create lookup map for O(1) access
    documents_by_id = {doc.id: doc for doc in documents}

    # Stitch together in memory, preserving member order
    response_data = []
    for member in all_members:
        document = documents_by_id.get(member.entity_id)
        if document:
            # Convert domain model to response schema
            document_response = DocumentResponse.model_validate(document)

            matrix_doc_response = MatrixDocumentResponse(
                id=member.id,  # member ID
                matrix_id=matrix_id,
                document_id=document.id,
                company_id=member.company_id,
                label=member.label,
                document=document_response,
                created_at=member.created_at,
                updated_at=document.updated_at,  # Use document's updated_at
            )
            response_data.append(matrix_doc_response)

    return response_data


@router.delete("/matrices/{matrixId}/documents/{documentId}")
async def remove_document_from_matrix(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    document_id: Annotated[int, Path(alias="documentId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Remove a document from a specific matrix (removes from entity set)."""
    async with transaction():
        entity_set_service = get_entity_set_service()
        member_repo = EntitySetMemberRepository()

        # Get matrix entity sets
        entity_sets_with_members = (
            await entity_set_service.get_entity_sets_with_members(
                matrix_id, current_user.company_id
            )
        )
        document_entity_set = next(
            (
                es
                for es, members in entity_sets_with_members
                if es.entity_type == EntityType.DOCUMENT
            ),
            None,
        )

        if not document_entity_set:
            raise HTTPException(
                status_code=404, detail="Matrix has no document entity set"
            )

        # Find the member
        member = await member_repo.get_member_by_entity_id(
            document_entity_set.id,
            document_id,
            EntityType.DOCUMENT,
            current_user.company_id,
        )

        if not member:
            raise HTTPException(status_code=404, detail="Document not found in matrix")

        # Delete the member
        success = await member_repo.delete(member.id, current_user.company_id)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to remove document from matrix"
            )

        logger.info(f"Removed document {document_id} from matrix {matrix_id}")
        return {"message": "Document removed from matrix successfully"}


@router.post("/matrices/{matrixId}/documents/{documentId}/associate")
async def associate_existing_document_with_matrix(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    document_id: Annotated[int, Path(alias="documentId")],
    entity_set_id: Annotated[
        int,
        Query(
            alias="entitySetId",
            description="Target entity set ID to add the document to.",
        ),
    ],
    label_update: DocumentLabelUpdate = None,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Associate an existing document with a matrix by adding it to a specific entity set."""
    async with transaction():
        question_service = get_question_service()
        batch_processing_service = get_batch_processing_service()
        document_service = get_document_service()
        entity_set_service = get_entity_set_service()
        member_repo = EntitySetMemberRepository()

        # Get the document for batch processing
        document = await document_service.get_document(
            document_id, current_user.company_id
        )
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get matrix entity sets and validate the target entity set
        entity_sets_with_members = (
            await entity_set_service.get_entity_sets_with_members(
                matrix_id, current_user.company_id
            )
        )

        # Find the specified entity set and validate it's a document type
        document_entity_set = next(
            (
                es
                for es, members in entity_sets_with_members
                if es.id == entity_set_id and es.entity_type == EntityType.DOCUMENT
            ),
            None,
        )

        if not document_entity_set:
            raise HTTPException(
                status_code=400,
                detail=f"Entity set {entity_set_id} is not a valid document entity set for this matrix",
            )

        # Check if document is already a member
        existing_member = await member_repo.get_member_by_entity_id(
            document_entity_set.id,
            document.id,
            EntityType.DOCUMENT,
            current_user.company_id,
        )

        if existing_member:
            raise HTTPException(
                status_code=409, detail="Document already associated with matrix"
            )

        # Get current max order
        existing_members = await member_repo.get_by_entity_set_id(
            document_entity_set.id, current_user.company_id
        )
        next_order = len(existing_members)

        # Add document as member of document entity set
        member_create = MatrixEntitySetMemberCreateModel(
            entity_set_id=document_entity_set.id,
            entity_id=document.id,
            entity_type=EntityType.DOCUMENT,
            member_order=next_order,
            company_id=current_user.company_id,
        )
        member = await member_repo.add_member(member_create)

        # Get existing questions for the matrix
        questions = await question_service.get_questions_for_matrix(matrix_id)

        logger.info(f"Found {len(questions)} existing questions for matrix {matrix_id}")

        # Create matrix cells for this document-matrix combination
        # IMPORTANT: Always call this even if no questions exist! This ensures:
        # - Entity refs are created
        # - Matrix structure is built (e.g., doc pairs for cross-correlation)
        # - Cells can be created when questions are added later
        (
            created_cells,
            _,
        ) = await batch_processing_service.process_entity_added_to_set(
            matrix_id=matrix_id,
            entity_id=document.id,
            entity_set_id=document_entity_set.id,
            create_qa_jobs=False,  # Jobs created after extraction completes
        )

        logger.info(f"Created {len(created_cells)} cells for document {document.id}")

        # If document is already extracted AND we have cells, create and queue QA jobs
        if created_cells and document.extraction_status == ExtractionStatus.COMPLETED:
            queued_count = (
                await batch_processing_service.create_jobs_and_queue_for_cells(
                    created_cells
                )
            )
            logger.info(
                f"Queued {queued_count} QA jobs for {len(created_cells)} cells (document extraction status: {document.extraction_status})"
            )

        logger.info(f"Associated document {document_id} with matrix {matrix_id}")
        return {
            "message": "Document associated with matrix successfully",
            "association_id": member.id,
        }


@router.get("/documents/{documentId}/highlighted/{matrixCellId}")
@trace_span
async def get_highlighted_document_for_cell(
    document_id: Annotated[int, Path(alias="documentId")],
    matrix_cell_id: Annotated[int, Path(alias="matrixCellId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Get a document with citations from a matrix cell highlighted."""
    highlighting_service = get_document_highlighting_service()

    try:
        highlighted_content = (
            await highlighting_service.get_document_with_cell_citations_highlighted(
                document_id, matrix_cell_id
            )
        )
        # Get document info for proper content type
        document_service = get_document_service()
        document = await document_service.get_document(
            document_id, current_user.company_id
        )
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Determine content type and filename based on file extension
        content_type = "application/octet-stream"
        filename_lower = document.filename.lower()

        # Handle text files - convert to markdown
        if filename_lower.endswith((".txt", ".text")):
            # Change extension to .md for text files
            base_name = document.filename.rsplit(".", 1)[0]
            filename = f"highlighted_{base_name}.md"
            content_type = "text/markdown"
        else:
            # Keep original extension for all other file types
            filename = f"highlighted_{document.filename}"

            # Set appropriate content type
            if filename_lower.endswith(".pdf"):
                content_type = "application/pdf"
            elif filename_lower.endswith(".docx"):
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif filename_lower.endswith(".doc"):
                content_type = "application/msword"
            elif filename_lower.endswith(".pptx"):
                content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            elif filename_lower.endswith(".ppt"):
                content_type = "application/vnd.ms-powerpoint"
            elif filename_lower.endswith((".md", ".markdown")):
                content_type = "text/markdown"

        return Response(
            content=highlighted_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating highlighted document: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate highlighted document"
        )
