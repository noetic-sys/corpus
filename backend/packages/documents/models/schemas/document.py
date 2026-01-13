from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, HttpUrl
from pydantic.alias_generators import to_camel


class DocumentBase(BaseModel):
    filename: str
    storage_key: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class DocumentLabelUpdate(BaseModel):
    label: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class DocumentUploadOptions(BaseModel):
    """Options for document upload behavior."""

    use_agentic_chunking: bool = False

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class DocumentResponse(DocumentBase):
    id: int
    company_id: int
    checksum: str
    extracted_content_path: Optional[str] = None
    extraction_status: str
    extraction_started_at: Optional[datetime] = None
    extraction_completed_at: Optional[datetime] = None
    use_agentic_chunking: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


class BulkUrlUploadRequest(BaseModel):
    urls: List[HttpUrl]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class BulkUrlUploadResponse(BaseModel):
    documents: List[DocumentResponse]
    errors: List[str]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class MatrixDocumentResponse(BaseModel):
    """Response schema for document with matrix association context."""

    id: int
    matrix_id: int
    document_id: int
    company_id: int
    label: Optional[str] = None
    document: DocumentResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


class DocumentSearchRequest(BaseModel):
    """Request schema for document search."""

    q: Optional[str] = None
    content_type: Optional[str] = None
    extraction_status: Optional[str] = None
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    skip: int = 0
    limit: int = 100

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class DocumentListResponse(BaseModel):
    """Response schema for document list with pagination metadata."""

    documents: List[DocumentResponse]
    total_count: int
    skip: int
    limit: int
    has_more: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class DocumentMatchSnippetResponse(BaseModel):
    """A matching snippet from document content."""

    chunk_id: str
    content: str
    score: float
    metadata: dict

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class DocumentSearchHitResponse(BaseModel):
    """Document search result with match context."""

    document: DocumentResponse
    match_score: float
    match_type: str  # MatchType enum value
    snippets: List[DocumentMatchSnippetResponse]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class HybridDocumentSearchResponse(BaseModel):
    """Response for hybrid document search with match snippets."""

    results: List[DocumentSearchHitResponse]
    total_count: int
    skip: int
    limit: int
    has_more: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class SupportedExtensionsResponse(BaseModel):
    """Response schema for supported file extensions."""

    extensions: List[str]
    max_file_size_mb: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )
