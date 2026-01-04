from typing import Optional, Type

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import override

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
from packages.documents.models.schemas.document import DocumentListResponse
from packages.documents.routes.documents import list_documents, search_documents


class ListDocumentsErrorResult(ToolErrorResult):
    error: str


class ListDocumentsSuccessResult(ToolSuccessResult):
    documents_response: DocumentListResponse


class ListDocumentsParameters(ToolParameters):
    query: Optional[str] = Field(
        description="optional search query to filter documents", default=None
    )
    content_type: Optional[str] = Field(
        description="optional content type filter", default=None
    )
    limit: int = Field(description="maximum number of documents to return", default=50)
    skip: int = Field(
        description="number of documents to skip for pagination", default=0
    )


class ListDocumentsTool(Tool[ListDocumentsParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="list_documents",
            description="List or search documents in the system",
            parameters=ListDocumentsParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[ListDocumentsParameters]:
        return ListDocumentsParameters

    @override
    async def execute(
        self,
        parameters: ListDocumentsParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            if parameters.query:
                # Call search_documents route function
                documents_response = await search_documents(
                    q=parameters.query,
                    content_type=parameters.content_type,
                    skip=parameters.skip,
                    limit=parameters.limit,
                    current_user=as_user,
                )
            else:
                # Call list_documents route function
                documents_response = await list_documents(
                    content_type=parameters.content_type,
                    skip=parameters.skip,
                    limit=parameters.limit,
                    current_user=as_user,
                )

            return ToolResult.ok(
                ListDocumentsSuccessResult(documents_response=documents_response)
            )

        except Exception as e:
            return ToolResult.err(ListDocumentsErrorResult(error=str(e)))
