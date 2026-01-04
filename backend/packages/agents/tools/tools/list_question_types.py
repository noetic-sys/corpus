from typing import Type, List

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
from packages.questions.models.schemas.question_type import QuestionTypeResponse
from packages.questions.routes.question_types import get_question_types


class ListQuestionTypesErrorResult(ToolErrorResult):
    error: str


class ListQuestionTypesSuccessResult(ToolSuccessResult):
    question_types: List[QuestionTypeResponse]


class ListQuestionTypesParameters(ToolParameters):
    # No parameters needed - this lists all available question types
    pass


class ListQuestionTypesTool(Tool[ListQuestionTypesParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="list_question_types",
            description="List all available question types with their IDs, names, and descriptions. Use this to understand what question types are available when creating questions.",
            parameters=ListQuestionTypesParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[ListQuestionTypesParameters]:
        return ListQuestionTypesParameters

    @override
    async def execute(
        self,
        parameters: ListQuestionTypesParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Call the get_question_types route function directly
            question_types = await get_question_types()

            return ToolResult.ok(
                ListQuestionTypesSuccessResult(question_types=question_types)
            )

        except Exception as e:
            return ToolResult.err(ListQuestionTypesErrorResult(error=str(e)))
