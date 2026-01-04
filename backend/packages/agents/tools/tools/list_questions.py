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
from packages.questions.models.schemas.question import QuestionResponse
from packages.questions.routes.questions import get_questions_by_matrix


class ListQuestionsErrorResult(ToolErrorResult):
    error: str


class ListQuestionsSuccessResult(ToolSuccessResult):
    questions: List[QuestionResponse]


class ListQuestionsParameters(ToolParameters):
    matrix_id: int = Field(description="the matrix id to list questions for")


class ListQuestionsTool(Tool[ListQuestionsParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="list_questions",
            description="List questions for a given matrix",
            parameters=ListQuestionsParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[ListQuestionsParameters]:
        return ListQuestionsParameters

    @override
    async def execute(
        self,
        parameters: ListQuestionsParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Call the get_questions_by_matrix route function directly
            question_responses = await get_questions_by_matrix(
                matrix_id=parameters.matrix_id,
                current_user=as_user,
            )

            return ToolResult.ok(
                ListQuestionsSuccessResult(questions=question_responses)
            )

        except Exception as e:
            return ToolResult.err(ListQuestionsErrorResult(error=str(e)))
