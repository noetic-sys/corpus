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
from packages.questions.models.schemas.question import QuestionUpdate
from packages.questions.models.schemas.question_with_options import (
    QuestionWithOptionsUpdate,
)
from packages.questions.models.schemas.question_option import QuestionOptionCreate
from packages.questions.routes.questions import (
    update_question,
    update_question_with_options,
)


class UpdateQuestionErrorResult(ToolErrorResult):
    error: str


class UpdateQuestionSuccessResult(ToolSuccessResult):
    question: QuestionModel


class UpdateQuestionParameters(ToolParameters):
    matrix_id: int = Field(description="ID of the matrix containing the question")
    question_id: int = Field(description="ID of the question to update")
    question_text: Optional[str] = Field(default=None, description="New question text")
    question_type_id: Optional[int] = Field(
        default=None, description="New question type ID"
    )
    label: Optional[str] = Field(default=None, description="New label for the question")
    min_answers: Optional[int] = Field(
        default=None, description="New minimum number of answers required"
    )
    max_answers: Optional[int] = Field(
        default=None,
        description="New maximum number of answers allowed (null for unlimited)",
    )
    options: Optional[List[str]] = Field(
        default=None,
        description="New list of options for select-type questions (replaces existing options)",
    )
    ai_model_id: Optional[int] = Field(
        default=None, description="New AI model ID to use for this question"
    )


class UpdateQuestionTool(Tool[UpdateQuestionParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.WRITE

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="update_question",
            description="Update an existing question in a matrix. Can update text, type, options, or other properties. Only provided fields will be updated.",
            parameters=UpdateQuestionParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[UpdateQuestionParameters]:
        return UpdateQuestionParameters

    @override
    async def execute(
        self,
        parameters: UpdateQuestionParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Build update data only with provided fields
            update_fields = {}
            if parameters.question_text is not None:
                update_fields["question_text"] = parameters.question_text
            if parameters.question_type_id is not None:
                update_fields["question_type_id"] = parameters.question_type_id
            if parameters.label is not None:
                update_fields["label"] = parameters.label
            if parameters.min_answers is not None:
                update_fields["min_answers"] = parameters.min_answers
            if parameters.max_answers is not None:
                update_fields["max_answers"] = parameters.max_answers
            if parameters.ai_model_id is not None:
                update_fields["ai_model_id"] = parameters.ai_model_id

            if not update_fields and parameters.options is None:
                return ToolResult.err(
                    UpdateQuestionErrorResult(error="No update fields provided")
                )

            # Call the appropriate route function directly
            if parameters.options is not None:
                # Convert string options to QuestionOptionCreate objects
                option_objects = [
                    QuestionOptionCreate(value=option) for option in parameters.options
                ]

                question_update_data = QuestionWithOptionsUpdate(
                    **update_fields, options=option_objects
                )

                # Call the update_question_with_options route function
                question = await update_question_with_options(
                    matrix_id=parameters.matrix_id,
                    question_id=parameters.question_id,
                    question_update=question_update_data,
                    current_user=as_user,
                    db=session,
                )
            else:
                question_update_data = QuestionUpdate(**update_fields)

                # Call the update_question route function
                question = await update_question(
                    question_id=parameters.question_id,
                    question_update=question_update_data,
                    current_user=as_user,
                    db=session,
                )

            return ToolResult.ok(UpdateQuestionSuccessResult(question=question))

        except Exception as e:
            return ToolResult.err(UpdateQuestionErrorResult(error=str(e)))
