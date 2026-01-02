from typing import List, Type

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
from packages.documents.models.schemas.document import MatrixDocumentResponse
from packages.documents.routes.documents import get_documents_by_matrix


class GetMatrixDocumentsErrorResult(ToolErrorResult):
    error: str


class GetMatrixDocumentsSuccessResult(ToolSuccessResult):
    documents: List[MatrixDocumentResponse]


class GetMatrixDocumentsParameters(ToolParameters):
    matrix_id: int = Field(description="the matrix id to get documents for")


class GetMatrixDocumentsTool(Tool[GetMatrixDocumentsParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="get_matrix_documents",
            description="Get all documents associated with a specific matrix",
            parameters=GetMatrixDocumentsParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[GetMatrixDocumentsParameters]:
        return GetMatrixDocumentsParameters

    @override
    async def execute(
        self,
        parameters: GetMatrixDocumentsParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Call the get_documents_by_matrix route function directly
            documents = await get_documents_by_matrix(
                matrix_id=parameters.matrix_id,
                current_user=as_user,
                db=session,
            )

            return ToolResult.ok(GetMatrixDocumentsSuccessResult(documents=documents))

        except Exception as e:
            return ToolResult.err(GetMatrixDocumentsErrorResult(error=str(e)))
