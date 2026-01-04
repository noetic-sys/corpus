from typing import Type, List
from pydantic import Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import override

from common.core.otel_axiom_exporter import get_logger
from packages.agents.tools.base import (
    ToolDefinition,
    ToolResult,
    ToolPermission,
    ToolContext,
    ToolParameters,
    ToolSuccessResult,
    ToolErrorResult,
    Tool,
)
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.documents.models.domain.document import DocumentModel
from packages.documents.models.schemas.document import BulkUrlUploadRequest
from packages.documents.routes.documents import upload_documents_from_urls

logger = get_logger(__name__)


class AddUrlsAsDocumentsErrorResult(ToolErrorResult):
    error: str


class AddUrlsAsDocumentsSuccessResult(ToolSuccessResult):
    documents: List[DocumentModel]
    errors: List[str]


class AddUrlsAsDocumentsParameters(ToolParameters):
    matrix_id: int = Field(description="ID of the matrix to add the documents to")
    entity_set_id: int = Field(
        description="ID of the document entity set to add the documents to"
    )
    urls: List[HttpUrl] = Field(
        description="List of URLs to fetch and add as documents"
    )


class AddUrlsAsDocumentsTool(Tool[AddUrlsAsDocumentsParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.WRITE

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="add_urls_as_documents",
            description="Fetch content from multiple URLs in parallel and add them as documents to a matrix",
            parameters=AddUrlsAsDocumentsParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[AddUrlsAsDocumentsParameters]:
        return AddUrlsAsDocumentsParameters

    @override
    async def execute(
        self,
        parameters: AddUrlsAsDocumentsParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            logger.info(f"Adding {len(parameters.urls)} URLs as documents")

            # Call the route directly
            request = BulkUrlUploadRequest(urls=parameters.urls)
            response = await upload_documents_from_urls(
                matrix_id=parameters.matrix_id,
                entity_set_id=parameters.entity_set_id,
                request=request,
                current_user=as_user,
            )

            return ToolResult.ok(
                AddUrlsAsDocumentsSuccessResult(
                    documents=[doc for doc in response.documents],
                    errors=response.errors,
                )
            )

        except Exception as e:
            logger.error(f"Error adding URLs as documents: {e}")
            return ToolResult.err(AddUrlsAsDocumentsErrorResult(error=str(e)))
