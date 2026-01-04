from typing import Type, Optional, List

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
from packages.questions.models.domain.question import QuestionModel
from packages.questions.models.schemas.question import QuestionCreate
from packages.questions.models.schemas.question_with_options import (
    QuestionWithOptionsCreate,
)
from packages.questions.models.schemas.question_option import QuestionOptionCreate
from packages.questions.routes.questions import (
    create_question,
    create_question_with_options,
)


class CreateQuestionErrorResult(ToolErrorResult):
    error: str


class CreateQuestionSuccessResult(ToolSuccessResult):
    question: QuestionModel


class CreateQuestionParameters(ToolParameters):
    matrix_id: int = Field(description="ID of the matrix to create the question in")
    entity_set_id: int = Field(
        description="ID of the question entity set to add the question to"
    )
    question_text: str = Field(description="The question text")
    question_type_id: int = Field(description="ID of the question type")
    label: Optional[str] = Field(
        default=None, description="Optional label for the question"
    )
    min_answers: int = Field(
        default=1, description="Minimum number of answers required"
    )
    max_answers: Optional[int] = Field(
        default=1, description="Maximum number of answers allowed (null for unlimited)"
    )
    options: Optional[List[str]] = Field(
        default=None, description="List of options for select-type questions"
    )
    ai_model_id: Optional[int] = Field(
        default=None, description="Optional AI model ID to use for this question"
    )


class CreateQuestionTool(Tool[CreateQuestionParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.WRITE

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="create_question",
            description="Create a new question in a matrix, optionally with multiple choice options",
            parameters=CreateQuestionParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[CreateQuestionParameters]:
        return CreateQuestionParameters

    @override
    async def execute(
        self,
        parameters: CreateQuestionParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Call the appropriate route function directly
            if parameters.options:
                # Convert string options to QuestionOptionCreate objects
                option_objects = [
                    QuestionOptionCreate(value=option) for option in parameters.options
                ]

                question_data = QuestionWithOptionsCreate(
                    question_text=parameters.question_text,
                    question_type_id=parameters.question_type_id,
                    label=parameters.label,
                    min_answers=parameters.min_answers,
                    max_answers=parameters.max_answers,
                    options=option_objects,
                    ai_model_id=parameters.ai_model_id,
                )

                # Call the create_question_with_options route function
                question = await create_question_with_options(
                    matrix_id=parameters.matrix_id,
                    entity_set_id=parameters.entity_set_id,
                    question_data=question_data,
                    current_user=as_user,
                )
            else:
                question_data = QuestionCreate(
                    question_text=parameters.question_text,
                    question_type_id=parameters.question_type_id,
                    label=parameters.label,
                    min_answers=parameters.min_answers,
                    max_answers=parameters.max_answers,
                    ai_model_id=parameters.ai_model_id,
                )

                # Call the create_question route function
                question = await create_question(
                    matrix_id=parameters.matrix_id,
                    entity_set_id=parameters.entity_set_id,
                    question=question_data,
                    current_user=as_user,
                )

            return ToolResult.ok(CreateQuestionSuccessResult(question=question))

        except Exception as e:
            return ToolResult.err(CreateQuestionErrorResult(error=str(e)))
